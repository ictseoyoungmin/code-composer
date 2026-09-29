#!/usr/bin/env python3
"""Render AG06 C/F/G/Am continuous-strum evidence through the actual pipeline."""
from __future__ import annotations

import json
import os
from pathlib import Path
import wave

import numpy as np

from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files


OUT = Path(os.environ.get("AG06_EVIDENCE_DIR", "artifacts/ag06-strum"))
SR = 24000
BPM = 96

VOICINGS = {
    "C": [(48,5,3),(52,4,2),(55,3,0),(60,2,1),(64,1,0)],
    "F": [(41,6,1),(48,5,3),(53,4,3),(57,3,2),(60,2,1),(65,1,1)],
    "G": [(43,6,3),(47,5,2),(50,4,0),(55,3,0),(59,2,0),(67,1,3)],
    "Am": [(45,5,0),(52,4,2),(57,3,2),(60,2,1),(64,1,0)],
}


def song():
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG06 Strum Evidence", "global_seed": 73},
        "transport": {"bpm": BPM, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
        "tonal": {"root": "C", "scale": "major"},
        "sections": [{"id": "a", "bars": 1}],
        "instruments": [{
            "id": "guitar",
            "family": "acoustic_guitar",
            "variant": "steel-string",
            "render_lock": {
                "preset": "acoustic_guitar.steel_single_string",
                "preset_version": "1.0.0",
            },
        }],
        "tracks": [{"id": "g", "function": "strum", "instrument": "guitar"}],
        "materials": [{"id": "m", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": "part", "section": "a", "track": "g", "material": "m"}],
    }


def gesture(stroke_id, direction, traversal_ms, **overrides):
    cfg = {
        "stroke_id": stroke_id,
        "direction": direction,
        "traversal_ms": traversal_ms,
        "entry_strength": 0.62,
        "acceleration": 0.10,
        "pick_depth": 0.58,
        "attack_angle_deg": 42.0,
        "follow_through": 0.72,
        "accent_position": 0.50,
        "accent_amount": 0.0,
        "from_string": 6 if direction == "down" else 1,
        "to_string": 1 if direction == "down" else 6,
    }
    cfg.update(overrides)
    return cfg


def chord_events(
    name,
    *,
    stroke_id,
    direction,
    traversal_ms,
    method="pick",
    gesture_overrides=None,
    muted_low_e=False,
):
    cfg = gesture(
        stroke_id,
        direction,
        traversal_ms,
        **(gesture_overrides or {}),
    )
    data = list(VOICINGS[name])
    if name == "C" and muted_low_e:
        data = [(40,6,0)] + data

    events = []
    for i, (midi, string, fret) in enumerate(data):
        muted = bool(name == "C" and muted_low_e and string == 6)
        strum = dict(cfg)
        strum["state"] = "muted" if muted else "sounding"
        perf = {
            "string": int(string),
            "fret": int(fret),
            "right_hand": {"method": method},
            "strum": strum,
        }
        if muted:
            perf["left_hand"] = {"technique": "dead_note"}
        events.append({
            "id": f"{stroke_id}_{i}",
            "type": "note",
            "start_beat": 0.0,
            "duration_beats": 1.35,
            "midi": int(midi),
            "velocity": 0.65,
            "instrument_performance": perf,
        })
    return events


def score(events):
    s = song()
    return s, {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(s),
        },
        "meta": {"title": "AG06 Strum Evidence"},
        "tracks": [{"id": "g", "events": events}],
        "render": {
            "sample_rate": SR,
            "tail_seconds": 0.1,
            "mix": {
                "tracks": [{"track": "g", "gain": 0.30, "pan": 0.0, "reverb_send": 0.0}],
                "music_bus_gain": 1.0,
                "room_return_gain": 0.0,
                "master_gain": 0.80,
            },
        },
    }


def peak_abs(path):
    with wave.open(str(path), "rb") as wf:
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2")
    if data.size == 0:
        return 0.0
    return float(np.max(np.abs(data.astype(np.float64) / 32767.0)))


def render_case(name, events):
    s, sc = score(events)
    wav_path = OUT / f"{name}.wav"
    result = render_song_score_to_files(
        s,
        sc,
        wav_path,
        render_ir_path=OUT / f"{name}_render_ir.json",
    )
    peak = peak_abs(wav_path)
    if peak >= 0.98:
        raise AssertionError(f"{name}: evidence peak {peak:.6f} >= 0.98")

    strokes = result["guitar_performance_report"]["tracks"]["g"]["strum_strokes"]
    if len(strokes) != 1:
        raise AssertionError(f"{name}: expected exactly one strum stroke")
    report = dict(next(iter(strokes.values())))
    report["audio_peak_abs"] = peak
    forces = [row["force"] for row in report["profile"]]
    if len(forces) >= 3 and max(forces) - min(forces) <= 0.01:
        raise AssertionError(f"{name}: per-string force profile too uniform")
    return report


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cases = {}

    for chord in ("C", "F", "G", "Am"):
        for direction in ("down", "up"):
            key = f"{chord}_{direction}_fast_pick"
            cases[key] = chord_events(
                chord,
                stroke_id=key,
                direction=direction,
                traversal_ms=28.0,
                method="pick",
            )

    cases["F_down_slow_rake"] = chord_events(
        "F", stroke_id="F_down_slow_rake", direction="down",
        traversal_ms=96.0, method="pick",
    )
    cases["G_down_accent"] = chord_events(
        "G", stroke_id="G_down_accent", direction="down",
        traversal_ms=28.0, method="pick",
        gesture_overrides={"accent_position": 0.62, "accent_amount": 0.38},
    )
    cases["Am_down_fast_finger"] = chord_events(
        "Am", stroke_id="Am_down_fast_finger", direction="down",
        traversal_ms=30.0, method="finger",
    )
    cases["C_down_muted_lowE"] = chord_events(
        "C", stroke_id="C_down_muted_lowE", direction="down",
        traversal_ms=32.0, method="pick", muted_low_e=True,
    )

    reports = {}
    lines = [
        "AG06 Chord / Strum Mechanics — actual-pipeline evidence",
        f"git_sha: {os.environ.get('GITHUB_SHA','local')}",
        f"sample_rate: {SR}",
        "All chord notes retain one nominal authored onset; AG06 adds render-local string contact offsets.",
        "Per-string force comes from one deterministic shared gesture; no random humanize.",
        "",
    ]

    for name, events in cases.items():
        report = render_case(name, events)
        reports[name] = report
        force_text = ", ".join(
            f"s{row['string']}@{row['offset_ms']:.1f}ms:{row['force']:.4f}"
            for row in report["profile"]
        )
        lines += [
            f"{name}: peak={report['audio_peak_abs']:.6f} "
            f"force_span={report['force_span']:.6f} "
            f"skipped={report['skipped_strings']} muted={report['muted_strings']}",
            f"  {force_text}",
        ]

    # Hard cross-case gates.
    fast = reports["F_down_fast_pick"]
    slow = reports["F_down_slow_rake"]
    if abs(fast["traversal_ms"] - slow["traversal_ms"]) < 1.0:
        raise AssertionError("fast/slow traversal did not differ")
    fast_forces = [r["force"] for r in fast["profile"]]
    slow_forces = [r["force"] for r in slow["profile"]]
    if not any(abs(a-b) > 1e-3 for a,b in zip(fast_forces, slow_forces)):
        raise AssertionError("fast/slow force distributions did not differ")

    if reports["C_down_fast_pick"]["skipped_strings"] != [6]:
        raise AssertionError("C downstroke must traverse but skip low-E string")
    if reports["C_down_muted_lowE"]["muted_strings"] != [6]:
        raise AssertionError("muted-low-E diagnostic did not preserve muted contact")

    (OUT / "REPORT.json").write_text(
        json.dumps(reports, indent=2) + "\n", encoding="utf-8"
    )
    lines += [
        "",
        "Human gate:",
        "1. C/F/G/Am down/up must read as opposite physical stroke directions.",
        "2. Strings must not sound perfectly simultaneous or equally struck.",
        "3. F slow rake must be slower and have a different force contour, not only wider timing.",
        "4. G accent must emphasize a local portion of the stroke rather than all strings uniformly.",
        "5. Am finger stroke should differ from pick while preserving the same chord mechanics.",
        "6. C skip/muted-low-E cases must sound mechanically distinct.",
        "AG06 remains OPEN until explicit human listening PASS.",
    ]
    (OUT / "MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
