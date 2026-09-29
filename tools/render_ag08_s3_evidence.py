#!/usr/bin/env python3
"""AG08-S3 shared bridge/body memory evidence through the actual pipeline."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files


OUT = Path(os.environ.get("AG08_S3_EVIDENCE_DIR", "artifacts/ag08-s3"))
BASE = "acoustic_guitar.steel_single_string"
S3 = "acoustic_guitar.steel_stateful_body"
SR = 24000
BPM = 96
BEAT_S = 60.0 / BPM


def song(preset):
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG08 S3 Evidence", "global_seed": 107},
        "transport": {"bpm": BPM, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
        "tonal": {"root": "E", "scale": "major"},
        "sections": [{"id": "a", "bars": 1}],
        "instruments": [{
            "id": "guitar",
            "family": "acoustic_guitar",
            "variant": "steel-string",
            "render_lock": {"preset": preset, "preset_version": "1.0.0"},
        }],
        "tracks": [{"id": "g", "function": "guitar", "instrument": "guitar"}],
        "materials": [{"id": "m", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": "part", "section": "a", "track": "g", "material": "m"}],
    }


def note(eid, start, dur, midi, string, fret, method="finger", velocity=0.65):
    return {
        "id": eid,
        "type": "note",
        "start_beat": float(start),
        "duration_beats": float(dur),
        "midi": int(midi),
        "velocity": float(velocity),
        "instrument_performance": {
            "string": int(string),
            "fret": int(fret),
            "right_hand": {"method": method},
        },
    }


def action(eid, start, kind, **params):
    return {
        "id": eid,
        "type": "instrument_action",
        "start_beat": float(start),
        "duration_beats": 0.08,
        "action": kind,
        "parameters": params,
    }


def score(preset, events):
    s = song(preset)
    return s, {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(s),
        },
        "meta": {"title": "AG08 S3 Evidence"},
        "tracks": [{"id": "g", "events": events}],
        "render": {
            "sample_rate": SR,
            "tail_seconds": 0.1,
            "mix": {
                "tracks": [{"track": "g", "gain": 0.32, "pan": 0.0, "reverb_send": 0.0}],
                "music_bus_gain": 1.0,
                "room_return_gain": 0.0,
                "master_gain": 0.8,
            },
        },
    }


def render_case(case, preset, events, suffix=None):
    s, sc = score(preset, events)
    tag = "A_AG07" if preset == BASE else "B_AG08_S3"
    if suffix:
        tag += "_" + suffix
    path = OUT / f"{case}_{tag}.wav"
    result = render_song_score_to_files(
        s, sc, path,
        render_ir_path=OUT / f"{case}_{tag}_render_ir.json",
    )
    return path, result["audio"], result["render_ir"]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rms(x):
    x = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(x * x))) if x.size else 0.0


def compare_exact(case, events):
    pa, a, ira = render_case(case, BASE, events)
    pb, b, irb = render_case(case, S3, events)
    sample_exact = bool(np.array_equal(a, b))
    event_exact = ira["tracks"][0]["events"] == irb["tracks"][0]["events"]
    if not sample_exact or not event_exact:
        raise AssertionError(f"{case}: isolated/simultaneous control changed")
    return {
        "sample_exact": sample_exact,
        "event_exact": event_exact,
        "sha256_a": sha256(pa),
        "sha256_b": sha256(pb),
        "peak": float(np.max(np.abs(b))) if b.size else 0.0,
    }


def compare_transition(case, events, boundary_beat):
    pa, a, ira = render_case(case, BASE, events)
    pb, b, irb = render_case(case, S3, events)
    pb2, b2, _ = render_case(case, S3, events, suffix="repeat")
    boundary = int(float(boundary_beat) * BEAT_S * SR)
    prefix_exact = bool(np.array_equal(a[:boundary], b[:boundary]))
    deterministic = bool(np.array_equal(b, b2))
    event_exact = ira["tracks"][0]["events"] == irb["tracks"][0]["events"]
    delta_ratio = rms(b[boundary:] - a[boundary:]) / (rms(a[boundary:]) + 1e-12)
    peak = float(np.max(np.abs(b))) if b.size else 0.0
    if not prefix_exact:
        raise AssertionError(f"{case}: changed before shared-body re-excitation")
    if not deterministic:
        raise AssertionError(f"{case}: S3 render is not deterministic")
    if not event_exact:
        raise AssertionError(f"{case}: event authority changed")
    if not 0.001 < delta_ratio < 0.40:
        raise AssertionError(f"{case}: body-memory delta ratio out of bound: {delta_ratio}")
    if peak >= 0.98:
        raise AssertionError(f"{case}: peak too high: {peak}")
    return {
        "prefix_exact": prefix_exact,
        "deterministic": deterministic,
        "event_exact": event_exact,
        "delta_rms_ratio": delta_ratio,
        "peak": peak,
        "sha256_a": sha256(pa),
        "sha256_b": sha256(pb),
        "sha256_repeat": sha256(pb2),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    isolated_note = [note("e4", 0.0, 0.75, 64, 1, 0)]
    isolated_action = [
        action("tap", 0.0, "body_tap", strength=0.55, location="lower_bout")
    ]
    simultaneous = [
        note("bass", 0.0, 0.80, 52, 4, 2, "thumb"),
        action("slap", 0.0, "top_slap", strength=0.58, location="soundboard"),
    ]
    note_then_slap = [
        note("e4", 0.0, 0.70, 64, 1, 0, "finger"),
        action("slap", 0.55, "top_slap", strength=0.54, location="soundboard"),
    ]
    slap_then_note = [
        action("tap", 0.0, "body_tap", strength=0.48, location="lower_bout"),
        note("e4", 0.50, 0.70, 64, 1, 0, "finger"),
    ]
    different_string = [
        note("e4_s1", 0.0, 0.55, 64, 1, 0),
        note("e4_s2", 0.50, 0.55, 64, 2, 5),
    ]

    report = {
        "git_sha": os.environ.get("GITHUB_SHA", "local"),
        "sample_rate": SR,
        "baseline": BASE,
        "candidate": S3,
        "cases": {},
    }
    report["cases"]["isolated_note"] = compare_exact("isolated_note", isolated_note)
    report["cases"]["isolated_action"] = compare_exact("isolated_action", isolated_action)
    report["cases"]["simultaneous_note_action"] = compare_exact(
        "simultaneous_note_action", simultaneous
    )
    report["cases"]["note_then_slap"] = compare_transition(
        "note_then_slap", note_then_slap, 0.55
    )
    report["cases"]["slap_then_note"] = compare_transition(
        "slap_then_note", slap_then_note, 0.50
    )
    report["cases"]["different_string_body"] = compare_transition(
        "different_string_body", different_string, 0.50
    )

    lines = [
        "AG08-S3 — shared bridge/body memory",
        f"git_sha: {report['git_sha']}",
        "Controls must remain exact; sequential re-excitation may alter only already-existing shared body residual.",
        "",
    ]
    for name, item in report["cases"].items():
        metrics = " ".join(
            f"{key}={value:.6f}" if isinstance(value, float) else f"{key}={value}"
            for key, value in item.items()
            if key not in {"sha256_a", "sha256_b", "sha256_repeat"}
        )
        lines.append(f"{name}: {metrics}")

    lines += [
        "",
        "S3 adds no new modal frequency, oscillator, hidden note, sample or IR.",
        "S4 sympathetic cross-string transfer remains disabled.",
    ]

    (OUT / "REPORT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
