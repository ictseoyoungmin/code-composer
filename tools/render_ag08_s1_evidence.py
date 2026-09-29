#!/usr/bin/env python3
"""AG08-S1 zero-coupling preservation evidence through the actual pipeline."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files


OUT = Path(os.environ.get("AG08_S1_EVIDENCE_DIR", "artifacts/ag08-s1"))
BASE = "acoustic_guitar.steel_single_string"
STATEFUL = "acoustic_guitar.steel_stateful"
SR = 24000


def song(preset):
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG08 S1 Evidence", "global_seed": 97},
        "transport": {"bpm": 96, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
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


def note(eid, start, dur, midi, string, fret, method="finger", strum=None):
    perf = {
        "string": string,
        "fret": fret,
        "right_hand": {"method": method},
    }
    if strum is not None:
        perf["strum"] = dict(strum)
    return {
        "id": eid,
        "type": "note",
        "start_beat": float(start),
        "duration_beats": float(dur),
        "midi": int(midi),
        "velocity": 0.65,
        "instrument_performance": perf,
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


def f_strum():
    common = {
        "stroke_id": "f-down",
        "direction": "down",
        "traversal_ms": 30.0,
        "entry_strength": 0.62,
        "acceleration": 0.10,
        "pick_depth": 0.58,
        "attack_angle_deg": 42.0,
        "follow_through": 0.72,
        "accent_position": 0.50,
        "accent_amount": 0.08,
        "from_string": 6,
        "to_string": 1,
        "state": "sounding",
    }
    voicing = [(41,6,1),(48,5,3),(53,4,3),(57,3,2),(60,2,1),(65,1,1)]
    return [
        note(f"f{i}", 0.0, 1.0, midi, string, fret, "pick", common)
        for i, (midi,string,fret) in enumerate(voicing)
    ]


def score(preset, events):
    s = song(preset)
    return s, {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(s),
        },
        "meta": {"title": "AG08 S1 Evidence"},
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
    path = OUT / f"{case}_{'A_AG07' if preset == BASE else 'B_AG08_S1'}.wav"
    result = render_song_score_to_files(
        s,
        sc,
        path,
        render_ir_path=OUT / f"{case}_{'A_AG07' if preset == BASE else 'B_AG08_S1'}_render_ir.json",
    )
    return path, result["audio"], result["render_ir"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    cases = {
        "single_E4": [note("e4", 0.0, 0.75, 64, 1, 0, "finger")],
        "F_down_strum": f_strum(),
        "note_plus_actions": [
            note("bass", 0.0, 0.9, 52, 4, 2, "thumb"),
            action("slap", 0.0, "top_slap", strength=0.58, location="soundboard"),
            action(
                "dead", 1.0, "dead_strum",
                strength=0.60, direction="down",
                traversal_ms=36.0, string_count=6, location="strings",
            ),
        ],
    }

    report = {
        "git_sha": os.environ.get("GITHUB_SHA", "local"),
        "sample_rate": SR,
        "baseline": BASE,
        "candidate": STATEFUL,
        "cases": {},
    }
    manifest = [
        "AG08-S1 — zero-coupling state skeleton preservation",
        f"git_sha: {report['git_sha']}",
        "Requirement: A (AG07 baseline) == B (AG08 stateful candidate) sample-exact.",
        "",
    ]

    for case, events in cases.items():
        path_a, a, ir_a = render_case(case, BASE, events)
        path_b, b, ir_b = render_case(case, STATEFUL, events)

        sample_exact = bool(np.array_equal(a, b))
        wav_byte_exact = path_a.read_bytes() == path_b.read_bytes()
        event_exact = (
            ir_a["tracks"][0]["events"] == ir_b["tracks"][0]["events"]
        )
        if not sample_exact:
            raise AssertionError(f"{case}: AG08-S1 audio is not sample-exact with AG07")
        if not wav_byte_exact:
            raise AssertionError(f"{case}: AG08-S1 WAV is not byte-exact with AG07")
        if not event_exact:
            raise AssertionError(f"{case}: authored/resolved events changed")

        report["cases"][case] = {
            "sample_exact": sample_exact,
            "wav_byte_exact": wav_byte_exact,
            "event_exact": event_exact,
            "sha256_a": sha256(path_a),
            "sha256_b": sha256(path_b),
            "peak": float(np.max(np.abs(a))) if a.size else 0.0,
        }
        manifest.append(
            f"{case}: sample_exact={sample_exact} wav_byte_exact={wav_byte_exact} "
            f"event_exact={event_exact} sha={sha256(path_a)}"
        )

    (OUT / "REPORT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    manifest += [
        "",
        "S1 is an engineering preservation gate, not a listening gate.",
        "Nonzero stateful coupling remains blocked until later AG08 slices.",
    ]
    (OUT / "MANIFEST.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print("\n".join(manifest))


if __name__ == "__main__":
    main()
