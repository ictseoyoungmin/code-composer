#!/usr/bin/env python3
"""AG08-S2 same-string continuity evidence through the actual pipeline."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files


OUT = Path(os.environ.get("AG08_S2_EVIDENCE_DIR", "artifacts/ag08-s2"))
BASE = "acoustic_guitar.steel_single_string"
S2 = "acoustic_guitar.steel_stateful_continuity"
SR = 24000
BPM = 96
BEAT_S = 60.0 / BPM


def song(preset):
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG08 S2 Evidence", "global_seed": 103},
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
        "meta": {"title": "AG08 S2 Evidence"},
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


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render_case(case, preset, events):
    s, sc = score(preset, events)
    tag = "A_AG07" if preset == BASE else "B_AG08_S2"
    path = OUT / f"{case}_{tag}.wav"
    result = render_song_score_to_files(
        s,
        sc,
        path,
        render_ir_path=OUT / f"{case}_{tag}_render_ir.json",
    )
    return path, result["audio"], result["render_ir"]


def rms(x):
    x = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(x * x))) if x.size else 0.0


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    same_string = [
        note("e4_1", 0.0, 0.45, 64, 1, 0, "finger"),
        note("e4_2", 0.5, 0.45, 64, 1, 0, "finger"),
        note("fs4", 1.0, 0.45, 66, 1, 2, "finger"),
        note("g4", 1.5, 0.45, 67, 1, 3, "finger"),
    ]
    different_string = [
        note("e4_s1", 0.0, 0.50, 64, 1, 0, "finger"),
        note("e4_s2", 0.5, 0.50, 64, 2, 5, "finger"),
    ]
    isolated = [note("e4", 0.0, 0.75, 64, 1, 0, "finger")]

    report = {
        "git_sha": os.environ.get("GITHUB_SHA", "local"),
        "sample_rate": SR,
        "baseline": BASE,
        "candidate": S2,
        "cases": {},
    }
    manifest = [
        "AG08-S2 — same-string residual continuity",
        f"git_sha: {report['git_sha']}",
        "S2 must alter repeated use of one physical string while preserving isolated and different-string controls.",
        "",
    ]

    # Isolated note: no prior state exists, so S2 must remain exact.
    p_a, a, ir_a = render_case("isolated_E4", BASE, isolated)
    p_b, b, ir_b = render_case("isolated_E4", S2, isolated)
    isolated_exact = bool(np.array_equal(a, b))
    isolated_event_exact = ir_a["tracks"][0]["events"] == ir_b["tracks"][0]["events"]
    if not isolated_exact or not isolated_event_exact:
        raise AssertionError("isolated note changed under AG08-S2")
    report["cases"]["isolated_E4"] = {
        "sample_exact": isolated_exact,
        "event_exact": isolated_event_exact,
        "sha256_a": sha256(p_a),
        "sha256_b": sha256(p_b),
    }
    manifest.append(f"isolated_E4: sample_exact={isolated_exact} event_exact={isolated_event_exact}")

    # Different physical string: S2 must not invent coupling.
    p_a, a, ir_a = render_case("different_string_E4", BASE, different_string)
    p_b, b, ir_b = render_case("different_string_E4", S2, different_string)
    different_exact = bool(np.array_equal(a, b))
    different_event_exact = ir_a["tracks"][0]["events"] == ir_b["tracks"][0]["events"]
    if not different_exact or not different_event_exact:
        raise AssertionError("different-string control changed before AG08-S4")
    report["cases"]["different_string_E4"] = {
        "sample_exact": different_exact,
        "event_exact": different_event_exact,
        "sha256_a": sha256(p_a),
        "sha256_b": sha256(p_b),
    }
    manifest.append(
        f"different_string_E4: sample_exact={different_exact} event_exact={different_event_exact}"
    )

    # Repeated same string: prefix before second attack is exact; later state differs.
    p_a, a, ir_a = render_case("same_string_phrase", BASE, same_string)
    p_b, b, ir_b = render_case("same_string_phrase", S2, same_string)
    p_b2, b2, _ = render_case("same_string_phrase_repeat", S2, same_string)
    second = int(0.5 * BEAT_S * SR)
    prefix_exact = bool(np.array_equal(a[:second], b[:second]))
    deterministic = bool(np.array_equal(b, b2))
    event_exact = ir_a["tracks"][0]["events"] == ir_b["tracks"][0]["events"]
    delta_ratio = rms(b[second:] - a[second:]) / (rms(a[second:]) + 1e-12)
    peak = float(np.max(np.abs(b))) if b.size else 0.0
    if not prefix_exact:
        raise AssertionError("S2 changed audio before any same-string re-attack")
    if not deterministic:
        raise AssertionError("S2 repeated render is not deterministic")
    if not event_exact:
        raise AssertionError("S2 changed authored/resolved event authority")
    if not 0.01 < delta_ratio < 0.75:
        raise AssertionError(f"S2 same-string delta ratio out of bound: {delta_ratio}")
    if peak >= 0.98:
        raise AssertionError(f"S2 peak too high: {peak}")

    report["cases"]["same_string_phrase"] = {
        "prefix_exact_before_second_attack": prefix_exact,
        "deterministic": deterministic,
        "event_exact": event_exact,
        "delta_rms_ratio": delta_ratio,
        "peak": peak,
        "sha256_a": sha256(p_a),
        "sha256_b": sha256(p_b),
        "sha256_repeat": sha256(p_b2),
    }
    manifest.append(
        "same_string_phrase: "
        f"prefix_exact={prefix_exact} deterministic={deterministic} "
        f"event_exact={event_exact} delta_rms_ratio={delta_ratio:.6f} peak={peak:.6f}"
    )

    (OUT / "REPORT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    manifest += [
        "",
        "Listening focus: A may stack independent same-string tails; B should read as one re-attacked string with bounded residual carry.",
        "S2 is not AG08 listening closure; shared body/action/cross-string state remains deferred.",
    ]
    (OUT / "MANIFEST.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print("\n".join(manifest))


if __name__ == "__main__":
    main()
