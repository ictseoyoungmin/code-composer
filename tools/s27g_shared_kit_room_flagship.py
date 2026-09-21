from __future__ import annotations

import csv
import json
import math
import wave
from pathlib import Path

import numpy as np

from code_composer.analysis.drummer_performance_analysis import analyze_drummer_performance
from code_composer.audio.drum_kit import integrate_drum_kit
from code_composer.audio.percussion import render_drum_event
from code_composer.presets import materialize_preset

SR = 24_000
BPM = 118.0
BEAT_S = 60.0 / BPM
BARS = 16
TAIL_S = 2.6
SEED = 27092026

DRY_PRESET = "drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated"
S26_PRESET = "drums.s19_core_powerful_room"
S27G_PRESET = DRY_PRESET


def ev(drum, beat, vel, section, dur=.08, pan=0.0):
    return {
        "event_type": "drum",
        "drum": drum,
        "start_beat": float(beat),
        "duration_beats": float(dur),
        "velocity": float(vel),
        "pan": float(pan),
        "section_id": section,
    }


def flagship_events():
    """Return the 269-event S27-G closure performance.

    Contract preserved from the engineering candidate:
      189 hand events / 65 right-foot events / 15 left-foot events.
    The timing offsets are explicit authored groove, not random humanization.
    """
    e = []
    groove_offsets = [0.000, -0.004, 0.004, -0.003, 0.003, -0.004, 0.004, -0.003]

    for bar in range(BARS):
        base = bar * 4.0
        if bar < 4:
            section = "pocket"
        elif bar < 8:
            section = "cross_stick_verse"
        elif bar < 12:
            section = "ride_lift"
        else:
            section = "power_chorus"

        # One stick-driven timekeeper per 8th-note slot. Crash replaces the
        # downbeat timekeeper at section entries; it never stacks with ride/hat.
        for step in range(8):
            off = step * 0.5 + groove_offsets[step]
            if step == 0 and bar in {4, 8, 12, 15}:
                drum = "crash"
                vel = 0.96 if bar != 15 else 1.00
                dur = .30
            elif bar < 2:
                drum = "hat_tight_closed"
                vel = 0.68 if step % 2 else 0.76
                dur = .07
            elif bar < 4:
                drum = "hat_closed"
                vel = 0.66 if step % 2 else 0.75
                dur = .08
            elif bar < 6:
                drum = "hat_half_open"
                vel = 0.64 if step % 2 else 0.74
                dur = .10
            elif bar < 8:
                drum = "hat_open" if step in {3, 7} else "hat_half_open"
                vel = 0.70 if drum == "hat_open" else (0.64 if step % 2 else 0.73)
                dur = .16 if drum == "hat_open" else .10
            elif bar < 12:
                drum = "ride"
                vel = 0.68 if step % 2 else 0.77
                dur = .14
            elif bar < 14:
                drum = "hat_closed"
                vel = 0.68 if step % 2 else 0.78
                dur = .08
            elif bar < 15:
                drum = "hat_open" if step in {3, 7} else "hat_closed"
                vel = 0.70 if drum == "hat_open" else (0.68 if step % 2 else 0.78)
                dur = .16 if drum == "hat_open" else .08
            else:
                drum = "hat_closed"
                vel = 0.70 if step % 2 else 0.80
                dur = .08
            e.append(ev(drum, base + off, vel, section, dur))

        # Backbeat semantics change by section. A 5-7 ms authored layback keeps
        # the groove human without changing the score or invoking random jitter.
        if bar < 4:
            snare, sv = "snare_center", .90
        elif bar < 8:
            snare, sv = "snare_cross_stick", .68
        elif bar < 12:
            snare, sv = "snare_center", .91
        else:
            snare, sv = "snare_rimshot", .97
        e.append(ev(snare, base + 1.010, sv, section, .12))
        e.append(ev(snare, base + 3.013, min(1.0, sv + .01), section, .12))

        # Four right-foot events per bar; section energy comes from velocity
        # shape, not automatic density mutation.
        kick_pattern = [(0.000, .90), (1.496, .77), (2.004, .86), (3.497, .74)]
        if bar >= 12:
            kick_pattern = [(0.000, .94), (1.496, .80), (2.004, .90), (3.497, .80)]
        for off, vel in kick_pattern:
            e.append(ev("kick", base + off, vel, section, .13))

    # Extra authored hand detail: 29 events. These are quiet enough to remain
    # articulation/detail, not a hidden loudness increase.
    for bar in range(4):
        base = bar * 4.0
        e.append(ev("snare_ghost", base + .744, .34, "pocket", .07))
        e.append(ev("snare_ghost", base + 2.742, .31, "pocket", .07))

    for bar in range(4, 8):
        base = bar * 4.0
        e.append(ev("snare_ghost", base + 2.742, .28, "cross_stick_verse", .07))

    for bar in range(8, 12):
        base = bar * 4.0
        e.append(ev("snare_ghost", base + .744, .33, "ride_lift", .07))
        e.append(ev("snare_ghost", base + 2.742, .30, "ride_lift", .07))

    for bar, offs in ((12, (.744, 2.742)), (13, (.744, 2.742)), (14, (2.742,))):
        base = bar * 4.0
        for off in offs:
            e.append(ev("snare_ghost", base + off, .30, "power_chorus", .07))

    # Final high -> mid -> floor fill and crash/kick punctuation. Floor tom is
    # at 3.5 so the deterministic hand assignment remains zero-strain.
    base = 15 * 4.0
    for off, drum, vel in (
        (2.246, "tom_high", .83),
        (2.744, "tom_mid", .87),
        (3.497, "tom_floor", .94),
        (3.752, "crash", 1.00),
    ):
        e.append(ev(drum, base + off, vel, "power_chorus", .18 if drum.startswith("tom_") else .30))
    e.append(ev("kick", base + 3.752, .98, "power_chorus", .13))

    # Ride section left-foot chicks: 15 total. They coexist with the stick ride
    # and make the performance explicitly four-limb rather than a hand-only demo.
    for bar, offs in (
        (8, (.5, 1.5, 2.5, 3.5)),
        (9, (.5, 1.5, 2.5, 3.5)),
        (10, (.5, 1.5, 2.5, 3.5)),
        (11, (.5, 1.5, 2.5)),
    ):
        base = bar * 4.0
        for off in offs:
            e.append(ev("hat_pedal", base + off + .006, .52, "ride_lift", .08))

    return sorted(e, key=lambda x: (x["start_beat"], x["drum"]))


def _performance_ir(events):
    return {
        "transport": {"bpm": BPM, "beats_per_bar": 4},
        "tracks": [{"id": "drums", "instrument": "drums", "events": events}],
    }


def _timeline_frames(events):
    last = max(float(x["start_beat"]) + float(x["duration_beats"]) for x in events)
    return int((last * BEAT_S + TAIL_S) * SR)


def render_authenticated_dry(patch, events):
    out = np.zeros((_timeline_frames(events), 2), dtype=np.float64)
    for i, x in enumerate(events):
        start = int(float(x["start_beat"]) * BEAT_S * SR)
        hit = render_drum_event(
            x["drum"], float(x["duration_beats"]) * BEAT_S, SR,
            float(x["velocity"]), seed=SEED + i * 7919,
            pan=float(x.get("pan", 0.0)), patch=patch,
        )
        end = min(len(out), start + len(hit))
        if end > start:
            out[start:end] += hit[:end-start]
    return out


def rms(x):
    x = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(x*x) + 1e-18)) if len(x) else 0.0


def peak(x):
    return float(np.max(np.abs(np.asarray(x, dtype=np.float64)))) if len(x) else 0.0


def crest(x):
    return peak(x) / max(rms(x), 1e-12)


def band_ratio(x, lo, hi):
    mono = .5 * (x[:, 0] + x[:, 1])
    if not len(mono):
        return 0.0
    w = np.hanning(len(mono))
    sp = np.abs(np.fft.rfft(mono * w)) ** 2
    f = np.fft.rfftfreq(len(mono), 1 / SR)
    return float(sp[(f >= lo) & (f < hi)].sum() / (sp.sum() + 1e-18))


def write_wav(path, x):
    y = np.asarray(x, dtype=np.float64)
    p = peak(y)
    scale = .98 / max(.98, p) if p > .98 else 1.0
    pcm = (np.clip(y * scale, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())
    return scale


def silence(seconds=.75):
    return np.zeros((int(float(seconds) * SR), 2), dtype=np.float64)


def clip_window(x, start_beat, end_beat, pad_s=.0):
    a = max(0, int((start_beat * BEAT_S - pad_s) * SR))
    b = min(len(x), int((end_beat * BEAT_S + pad_s) * SR))
    return x[a:b]


def window_rms(x, beat, a_s, b_s):
    s = int(float(beat) * BEAT_S * SR)
    a = max(0, s + int(a_s * SR))
    b = min(len(x), s + int(b_s * SR))
    return rms(x[a:b])


def _assignments_csv(path, report):
    fields = ["start_beat", "time_s", "drum", "family", "limb", "velocity", "section_id", "position"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in report["assignments"]:
            w.writerow({k: row.get(k, "") for k in fields})


def main(out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    events = flagship_events()
    report = analyze_drummer_performance(_performance_ir(events))
    assert len(events) == 269
    assert report["limb_event_counts"] == {"hands": 189, "right_foot": 65, "left_foot": 15}
    assert report["playable"] is True
    assert report["strained"] is False
    assert report["issue_counts"] == {"high": 0, "medium": 0, "low": 0}

    dry_patch = materialize_preset(DRY_PRESET, role="drums")
    dry = render_authenticated_dry(dry_patch, events)

    s26_patch = materialize_preset(S26_PRESET, role="drums")
    s27g_patch = materialize_preset(S27G_PRESET, role="drums")
    s26_cfg = s26_patch["drum_graph"]["kit_integration"]
    s27g_cfg = s27g_patch["drum_graph"]["kit_integration"]

    s26, s26_report = integrate_drum_kit(dry, SR, events, BEAT_S, s26_cfg)
    s27g, s27g_report = integrate_drum_kit(dry, SR, events, BEAT_S, s27g_cfg)

    target = rms(dry)
    s26_gain = target / max(rms(s26), 1e-12)
    s27g_gain = target / max(rms(s27g), 1e-12)
    s26m = s26 * s26_gain
    s27gm = s27g * s27g_gain
    gap = silence(.75)

    # Listening order favors complete musical context before short diagnostics.
    outputs = {
        "00_DRY_AUTHENTICATED_16BAR_24k.wav": dry,
        "01_S26_SHARED_ROOM_16BAR_24k.wav": s26,
        "02_S27G_SHARED_ROOM_16BAR_24k.wav": s27g,
        "03_S26_then_S27G_RMS_MATCHED_16BAR_24k.wav": np.concatenate([s26m, gap, s27gm], axis=0),
        "04_DRY_then_S27G_RMS_MATCHED_16BAR_24k.wav": np.concatenate([dry, gap, s27gm], axis=0),
    }

    # Bars 5-8: cross-stick + half/open hat should expose articulation-aware room.
    verse26 = clip_window(s26m, 16.0, 32.0, .15)
    verseg = clip_window(s27gm, 16.0, 32.0, .15)
    outputs["05_CROSS_STICK_OPEN_HAT_S26_then_S27G.wav"] = np.concatenate([verse26, gap, verseg], axis=0)

    # Bars 9-12: ride + left-foot chicks should sound like one physical kit.
    ride26 = clip_window(s26m, 32.0, 48.0, .15)
    rideg = clip_window(s27gm, 32.0, 48.0, .15)
    outputs["06_RIDE_LEFT_FOOT_S26_then_S27G.wav"] = np.concatenate([ride26, gap, rideg], axis=0)

    # Final two bars expose rimshot power, tom-family movement and final crash decay.
    end26 = clip_window(s26m, 56.0, 64.0, .15)
    endg = clip_window(s27gm, 56.0, 64.0, .15)
    outputs["07_POWER_TOM_FILL_S26_then_S27G.wav"] = np.concatenate([end26, gap, endg], axis=0)

    crash_beat = 63.752
    c26 = clip_window(s26m, crash_beat - .20, crash_beat + 2.25/BEAT_S, 0.0)
    cg = clip_window(s27gm, crash_beat - .20, crash_beat + 2.25/BEAT_S, 0.0)
    outputs["08_FINAL_CRASH_TAIL_S26_then_S27G.wav"] = np.concatenate([c26, gap, cg], axis=0)

    export_scales = {name: write_wav(out_dir / name, audio) for name, audio in outputs.items()}

    # Representative musical events for metric windows.
    rimshot_beat = 49.013      # bar 13 beat 2
    open_hat_beat = 29.497     # bar 8 late open hat
    floor_tom_beat = 63.497
    metrics = {
        "sample_rate": SR,
        "bpm": BPM,
        "bars": BARS,
        "event_count": len(events),
        "limb_event_counts": report["limb_event_counts"],
        "drummer_performance": {
            "playable": report["playable"],
            "strained": report["strained"],
            "issue_counts": report["issue_counts"],
        },
        "raw": {
            "dry": {"rms": rms(dry), "peak": peak(dry), "crest": crest(dry)},
            "s26": {"rms": rms(s26), "peak": peak(s26), "crest": crest(s26)},
            "s27g": {"rms": rms(s27g), "peak": peak(s27g), "crest": crest(s27g)},
        },
        "rms_match": {"target": target, "s26_gain": s26_gain, "s27g_gain": s27g_gain},
        "spectral_energy_ratio": {
            "dry_2_6k": band_ratio(dry, 2000, 6000),
            "s26_2_6k": band_ratio(s26m, 2000, 6000),
            "s27g_2_6k": band_ratio(s27gm, 2000, 6000),
            "dry_6_11k": band_ratio(dry, 6000, 11000),
            "s26_6_11k": band_ratio(s26m, 6000, 11000),
            "s27g_6_11k": band_ratio(s27gm, 6000, 11000),
        },
        "rimshot": {
            "s26_0_30ms": window_rms(s26m, rimshot_beat, 0, .030),
            "s27g_0_30ms": window_rms(s27gm, rimshot_beat, 0, .030),
            "s26_80_250ms": window_rms(s26m, rimshot_beat, .080, .250),
            "s27g_80_250ms": window_rms(s27gm, rimshot_beat, .080, .250),
        },
        "open_hat": {
            "s26_0_40ms": window_rms(s26m, open_hat_beat, 0, .040),
            "s27g_0_40ms": window_rms(s27gm, open_hat_beat, 0, .040),
            "s26_200_600ms": window_rms(s26m, open_hat_beat, .200, .600),
            "s27g_200_600ms": window_rms(s27gm, open_hat_beat, .200, .600),
        },
        "floor_tom": {
            "dry_20_180ms": window_rms(dry, floor_tom_beat, .020, .180),
            "s26_20_180ms": window_rms(s26m, floor_tom_beat, .020, .180),
            "s27g_20_180ms": window_rms(s27gm, floor_tom_beat, .020, .180),
        },
        "final_crash": {
            "dry_0_30ms": window_rms(dry, crash_beat, 0, .030),
            "s26_0_30ms": window_rms(s26m, crash_beat, 0, .030),
            "s27g_0_30ms": window_rms(s27gm, crash_beat, 0, .030),
            "dry_300_900ms": window_rms(dry, crash_beat, .300, .900),
            "s26_300_900ms": window_rms(s26m, crash_beat, .300, .900),
            "s27g_300_900ms": window_rms(s27gm, crash_beat, .300, .900),
        },
        "integration_reports": {"s26": s26_report, "s27g": s27g_report},
        "export_scales": export_scales,
    }

    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    (out_dir / "events.json").write_text(json.dumps(events, indent=2) + "\n", encoding="utf-8")
    (out_dir / "drummer_performance.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    _assignments_csv(out_dir / "limb_assignments.csv", report)

    readme = f"""# S27-G perceptual closure audition\n\n24 kHz / 118 BPM / 16 bars / 269 explicit events.\nS27-F: playable=true, strained=false, HIGH/MEDIUM/LOW=0/0/0.\n\nListen in this order:\n\n1. `03_S26_then_S27G_RMS_MATCHED_16BAR_24k.wav` — primary closure A/B.\n2. `04_DRY_then_S27G_RMS_MATCHED_16BAR_24k.wav` — verify authenticated close attack still leads.\n3. `05_CROSS_STICK_OPEN_HAT_S26_then_S27G.wav` — articulation-aware room hierarchy.\n4. `06_RIDE_LEFT_FOOT_S26_then_S27G.wav` — shared four-limb kit image.\n5. `07_POWER_TOM_FILL_S26_then_S27G.wav` — rimshot + high/mid/floor movement.\n6. `08_FINAL_CRASH_TAIL_S26_then_S27G.wav` — attack/body versus late smear.\n\nClosure gate:\n- S27-G must sound like one compact physical kit, not simply a wetter mix.\n- close attack remains in front; no zero-time doubling.\n- open hat/floor tom excite more room than tight/ghost material.\n- rimshot/crash gain power without restoring long tonal wash.\n- tom fill reads as movement across one kit.\n- S26 -> S27-G improvement must survive RMS matching.\n\nRaw whole-render RMS: dry={metrics['raw']['dry']['rms']:.6f}, S26={metrics['raw']['s26']['rms']:.6f}, S27-G={metrics['raw']['s27g']['rms']:.6f}.\n"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/data/s27g_perceptual_closure_audition")
