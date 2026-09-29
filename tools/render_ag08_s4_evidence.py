#!/usr/bin/env python3
"""AG08-S4 bounded sympathetic cross-string coupling evidence."""
from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path

import numpy as np

from code_composer.audio.acoustic_guitar.stateful import (
    _sympathetic_transfer_plan,
    initialize_acoustic_guitar_state,
)
from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files
from code_composer.presets import materialize_preset


OUT = Path(os.environ.get("AG08_S4_EVIDENCE_DIR", "artifacts/ag08-s4"))
S3 = "acoustic_guitar.steel_stateful_body"
S4 = "acoustic_guitar.steel_stateful_sympathetic"
SR = 24000
BPM = 96


def song(preset):
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG08 S4 Evidence", "global_seed": 107},
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


def score(preset, events):
    s = song(preset)
    return s, {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(s),
        },
        "meta": {"title": "AG08 S4 Evidence"},
        "tracks": [{"id": "g", "events": deepcopy(events)}],
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


def render(case, preset, events, suffix=""):
    s, sc = score(preset, events)
    tag = "A_S3" if preset == S3 else "B_S4"
    if suffix:
        tag += "_" + suffix
    path = OUT / f"{case}_{tag}.wav"
    result = render_song_score_to_files(
        s, sc, path, render_ir_path=OUT / f"{case}_{tag}_render_ir.json"
    )
    return path, result["audio"], result["render_ir"]


def rms(x):
    x = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(x * x))) if x.size else 0.0


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def exact_case(case, events):
    pa, a, ira = render(case, S3, events)
    pb, b, irb = render(case, S4, events)
    sample_exact = bool(np.array_equal(a, b))
    event_exact = ira["tracks"][0]["events"] == irb["tracks"][0]["events"]
    if not sample_exact or not event_exact:
        raise AssertionError(f"{case}: S4 preservation control changed")
    return {
        "sample_exact": sample_exact,
        "event_exact": event_exact,
        "sha256_a": sha256(pa),
        "sha256_b": sha256(pb),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    f4 = [note("f4", 0.0, 0.70, 65, 1, 1)]
    chord = [
        note("s1", 0.0, 0.70, 64, 1, 0),
        note("s2", 0.0, 0.70, 59, 2, 0),
        note("s3", 0.0, 0.70, 56, 3, 1),
        note("s4", 0.0, 0.70, 52, 4, 2),
        note("s5", 0.0, 0.70, 47, 5, 2),
        note("s6", 0.0, 0.70, 40, 6, 0),
    ]
    e4 = [note("e4", 0.0, 0.70, 64, 1, 0)]

    report = {
        "sample_rate": SR,
        "incompatible_f4": exact_case("incompatible_f4", f4),
        "fully_authored_chord": exact_case("fully_authored_chord", chord),
    }

    pa, a, ira = render("compatible_e4", S3, e4)
    pb, b, irb = render("compatible_e4", S4, e4)
    pb2, b2, irb2 = render("compatible_e4", S4, e4, "repeat")
    event_exact = (
        ira["tracks"][0]["events"]
        == irb["tracks"][0]["events"]
        == irb2["tracks"][0]["events"]
    )
    deterministic = bool(np.array_equal(b, b2))
    delta_ratio = rms(b - a) / (rms(a) + 1e-12)

    patch = materialize_preset(S4)
    graph = patch["acoustic_guitar_graph"]
    cfg = graph["stateful_coupling"]
    state = initialize_acoustic_guitar_state(SR, graph)
    plan = _sympathetic_transfer_plan(
        64, 0, state, SR, graph,
        cfg["cross_string_coupling"], cfg["sympathetic_gain"],
    )
    eta = float(sum(item["eta"] for item in plan))
    targets = [int(item["target_idx"]) + 1 for item in plan]

    if not deterministic or not event_exact:
        raise AssertionError("compatible E4 lost deterministic/event identity")
    if len(irb["tracks"][0]["events"]) != 1:
        raise AssertionError("S4 created a hidden Render-IR note")
    if not (0.001 < delta_ratio < 0.45):
        raise AssertionError(f"unexpected S4 audible delta ratio {delta_ratio}")
    if not (0.0 < eta <= 0.12):
        raise AssertionError(f"invalid bridge-domain energy transfer {eta}")
    if eta > cfg["cross_string_coupling"] * cfg["sympathetic_gain"] + 1e-12:
        raise AssertionError("S4 transfer exceeds configured passive budget")
    peak = float(np.max(np.abs(b))) if b.size else 0.0
    if peak >= 0.98:
        raise AssertionError(f"S4 peak too high: {peak}")

    report["compatible_e4"] = {
        "sample_exact": bool(np.array_equal(a, b)),
        "deterministic": deterministic,
        "event_exact": event_exact,
        "render_ir_event_count": len(irb["tracks"][0]["events"]),
        "delta_rms_ratio_vs_s3": delta_ratio,
        "bridge_energy_transfer_fraction": eta,
        "target_strings": targets,
        "source_keep_squared_plus_transfer": (1.0 - eta) + eta,
        "peak": peak,
        "sha256_a": sha256(pa),
        "sha256_b": sha256(pb),
        "sha256_b_repeat": sha256(pb2),
    }

    (OUT / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
