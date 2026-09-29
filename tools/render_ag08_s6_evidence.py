#!/usr/bin/env python3
"""AG08-S6 passive-energy / long-horizon stability evidence."""
from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path

import numpy as np

from code_composer.audio.acoustic_guitar.body import radiate_acoustic_guitar_body
from code_composer.audio.acoustic_guitar.stability import passive_transition_certificate
from code_composer.audio.acoustic_guitar.stateful import render_stateful_acoustic_guitar_track
from code_composer.audio.acoustic_guitar.string import render_steel_string_bridge_drive
from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files
from code_composer.presets import materialize_preset


OUT = Path(os.environ.get("AG08_S6_EVIDENCE_DIR", "artifacts/ag08-s6"))
PRESET = "acoustic_guitar.steel_stateful_performance"
SR = 24000
BPM = 96
BEAT_S = 60.0 / BPM


def note(eid, start, dur, midi, string, fret, *, method="finger", arpeggio=None, strum=None):
    perf = {"string": int(string), "fret": int(fret), "right_hand": {"method": method}}
    if arpeggio is not None:
        perf["arpeggio"] = deepcopy(arpeggio)
    if strum is not None:
        perf["strum"] = deepcopy(strum)
    return {
        "id": eid, "type": "note", "start_beat": float(start),
        "duration_beats": float(dur), "midi": int(midi), "velocity": 0.65,
        "instrument_performance": perf,
    }


def action(eid, start, kind, **parameters):
    return {
        "id": eid, "type": "instrument_action",
        "start_beat": float(start), "duration_beats": 0.08,
        "action": kind, "parameters": parameters,
    }


def strum_cfg(stroke_id):
    return {
        "stroke_id": stroke_id, "direction": "down", "traversal_ms": 34.0,
        "entry_strength": 0.62, "acceleration": 0.10, "pick_depth": 0.58,
        "attack_angle_deg": 42.0, "follow_through": 0.72,
        "accent_position": 0.50, "accent_amount": 0.08,
        "from_string": 6, "to_string": 1, "state": "sounding",
    }


def cycle_events(cycle, offset):
    pre = f"pre-{cycle}"
    post = f"post-{cycle}"
    stroke = f"stroke-{cycle}"
    ev = [
        note(
            f"{cycle}-arp-bass", offset + 0.00, 0.20, 48, 5, 3, method="thumb",
            arpeggio={"gesture_id": pre, "player": "thumb", "voice": "bass", "sequence_index": 0},
        ),
        note(
            f"{cycle}-arp-inner", offset + 0.25, 0.20, 55, 3, 0, method="finger",
            arpeggio={"gesture_id": pre, "player": "index", "voice": "inner", "sequence_index": 1},
        ),
    ]
    cfg = strum_cfg(stroke)
    for i, (midi, string, fret) in enumerate(
        [(43, 6, 3), (47, 5, 2), (50, 4, 0), (55, 3, 0), (59, 2, 0), (67, 1, 3)]
    ):
        ev.append(note(
            f"{cycle}-strum-{i}", offset + 0.65, 0.28,
            midi, string, fret, method="pick", strum=cfg,
        ))
    ev += [
        action(
            f"{cycle}-mute", offset + 1.15, "muted_strum",
            strength=0.72, direction="down", traversal_ms=38.0,
            string_count=6, location="strings",
        ),
        action(
            f"{cycle}-slap", offset + 1.45, "top_slap",
            strength=0.58, location="soundboard",
        ),
        note(
            f"{cycle}-post-bass", offset + 1.75, 0.22, 40, 6, 0, method="thumb",
            arpeggio={"gesture_id": post, "player": "thumb", "voice": "bass", "sequence_index": 0},
        ),
        note(
            f"{cycle}-post-treble", offset + 2.00, 0.22, 59, 2, 0, method="finger",
            arpeggio={"gesture_id": post, "player": "middle", "voice": "treble", "sequence_index": 1},
        ),
    ]
    return ev


def stress_events():
    out = []
    for cycle, offset in enumerate((0.0, 3.0, 6.0, 9.0)):
        out.extend(cycle_events(cycle, offset))
    return out


def song():
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG08 S6 Stability Stress", "global_seed": 127},
        "transport": {"bpm": BPM, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
        "tonal": {"root": "E", "scale": "major"},
        "sections": [{"id": "a", "bars": 4}],
        "instruments": [{
            "id": "guitar", "family": "acoustic_guitar", "variant": "steel-string",
            "render_lock": {"preset": PRESET, "preset_version": "1.0.0"},
        }],
        "tracks": [{"id": "g", "function": "percussive-fingerstyle", "instrument": "guitar"}],
        "materials": [{"id": "m", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": "part", "section": "a", "track": "g", "material": "m"}],
    }


def score(events):
    s = song()
    return s, {
        "format": "code-composer-performance-score/v1",
        "source_song": {"format": "code-composer-song/v1", "fingerprint": song_fingerprint(s)},
        "meta": {"title": "AG08 S6 Stability Stress"},
        "tracks": [{"id": "g", "events": deepcopy(events)}],
        "render": {
            "sample_rate": SR,
            "tail_seconds": 8.0,
            "mix": {
                "tracks": [{"track": "g", "gain": 0.32, "pan": 0.0, "reverb_send": 0.0}],
                "music_bus_gain": 1.0, "room_return_gain": 0.0, "master_gain": 0.8,
            },
        },
    }


def rms(x):
    x = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(x * x))) if x.size else 0.0


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    patch = materialize_preset(PRESET)
    graph = patch["acoustic_guitar_graph"]

    cert = passive_transition_certificate(SR, patch)
    if not cert["passive_internal_state_transforms"]:
        raise AssertionError("internal passive-state certificate failed")

    no_input = render_stateful_acoustic_guitar_track(
        [], 12 * SR, SR, patch, BEAT_S
    )
    if no_input is None or not np.array_equal(no_input, np.zeros_like(no_input)):
        raise AssertionError("no-input stateful renderer is not exact silence")

    bridge_impulse = np.zeros(12 * SR, dtype=np.float64)
    bridge_impulse[0] = 1.0
    body = radiate_acoustic_guitar_body(bridge_impulse, SR, graph)
    body_early = rms(body[: int(0.25 * SR)])
    body_late = rms(body[-SR:])
    if not np.all(np.isfinite(body)) or not (body_late < body_early * 1e-4):
        raise AssertionError("body impulse does not decay sufficiently")

    string = render_steel_string_bridge_drive(40, 12 * SR, SR, graph, velocity=0.72)
    string_first = rms(string[: 2 * SR])
    string_mid = rms(string[4 * SR: 6 * SR])
    string_late = rms(string[10 * SR: 12 * SR])
    if not np.all(np.isfinite(string)):
        raise AssertionError("string free-decay produced non-finite values")
    if not (string_first > string_mid > string_late >= 0.0):
        raise AssertionError("string free-decay windows are not descending")
    if not string_late < string_first * 0.08:
        raise AssertionError("string free-decay retains excessive late energy")

    events = stress_events()
    s, sc = score(events)
    p1 = OUT / "stress_A.wav"
    p2 = OUT / "stress_B_repeat.wav"
    r1 = render_song_score_to_files(s, sc, p1, render_ir_path=OUT / "stress_render_ir.json")
    r2 = render_song_score_to_files(s, sc, p2)
    a = r1["audio"]
    b = r2["audio"]

    deterministic = bool(np.array_equal(a, b))
    event_count = len(r1["render_ir"]["tracks"][0]["events"])
    if not deterministic:
        raise AssertionError("long-horizon stress render is not deterministic")
    if event_count != len(events):
        raise AssertionError("long-horizon stress created/dropped Render-IR events")
    if not np.all(np.isfinite(a)):
        raise AssertionError("long-horizon stress produced non-finite samples")

    peak = float(np.max(np.abs(a))) if a.size else 0.0
    if peak >= 0.98:
        raise AssertionError(f"long-horizon stress peak too high: {peak}")

    # Compare the active portion of four identical performance cycles. A passive
    # state may settle to a different steady state, but it must not grow without bound.
    cycle_rms = []
    for offset in (0.0, 3.0, 6.0, 9.0):
        start = int(offset * BEAT_S * SR)
        end = int((offset + 2.4) * BEAT_S * SR)
        cycle_rms.append(rms(a[start:end]))
    cycle_growth = max(cycle_rms) / (min(cycle_rms) + 1e-15)
    if cycle_growth >= 3.0:
        raise AssertionError(f"repeated-cycle energy growth is excessive: {cycle_growth}")

    final_event_end_beat = 11.22
    final_t = final_event_end_beat * BEAT_S
    early0 = int((final_t + 0.25) * SR)
    early1 = int((final_t + 0.75) * SR)
    late0 = int((final_t + 5.0) * SR)
    late1 = int((final_t + 6.0) * SR)
    tail_early = rms(a[early0:early1])
    tail_late = rms(a[late0:late1])
    if not tail_early > 0.0:
        raise AssertionError("stress tail probe missed active decay")
    if not tail_late < tail_early * 0.01:
        raise AssertionError(
            f"long-horizon tail does not decay enough: {tail_late/tail_early}"
        )

    report = {
        "sample_rate": SR,
        "certificate": cert,
        "no_input": {"exact_silence": True, "duration_s": 12.0},
        "body_impulse": {
            "duration_s": 12.0,
            "finite_energy": float(np.sum(body * body)),
            "early_rms": body_early,
            "late_rms": body_late,
            "late_to_early_ratio": body_late / (body_early + 1e-30),
        },
        "string_free_decay": {
            "midi": 40,
            "duration_s": 12.0,
            "finite_energy": float(np.sum(string * string)),
            "rms_0_2s": string_first,
            "rms_4_6s": string_mid,
            "rms_10_12s": string_late,
            "late_to_first_ratio": string_late / (string_first + 1e-30),
        },
        "long_horizon_stress": {
            "cycles": 4,
            "authored_event_count": len(events),
            "render_ir_event_count": event_count,
            "deterministic": deterministic,
            "peak": peak,
            "cycle_rms": cycle_rms,
            "max_to_min_cycle_rms_ratio": cycle_growth,
            "tail_early_rms": tail_early,
            "tail_late_rms": tail_late,
            "tail_late_to_early_ratio": tail_late / (tail_early + 1e-30),
            "sha256": sha256(p1),
            "sha256_repeat": sha256(p2),
        },
    }
    (OUT / "REPORT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
