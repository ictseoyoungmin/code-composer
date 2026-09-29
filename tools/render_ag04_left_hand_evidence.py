#!/usr/bin/env python3
"""Render AG04 left-hand evidence through the actual Composer-first pipeline."""
from __future__ import annotations

import os
from pathlib import Path

from code_composer.execution import render_song_score_to_files
from code_composer.core.song import song_fingerprint


OUT = Path(os.environ.get("AG04_EVIDENCE_DIR", "artifacts/ag04-left-hand"))
SR = 24000


def song():
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG04 Evidence", "global_seed": 53},
        "transport": {"bpm": 96, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
        "tonal": {"root": "E", "scale": "major"},
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
        "tracks": [{"id": "g", "function": "single-note", "instrument": "guitar"}],
        "materials": [{"id": "m", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": "part", "section": "a", "track": "g", "material": "m"}],
    }


def note(event_id, start, duration, midi, string, fret, *, right=None, left=None):
    perf = {"string": string, "fret": fret}
    if right is not None:
        perf["right_hand"] = dict(right)
    if left is not None:
        perf["left_hand"] = dict(left)
    return {
        "id": event_id,
        "type": "note",
        "start_beat": float(start),
        "duration_beats": float(duration),
        "midi": int(midi),
        "velocity": 0.65,
        "instrument_performance": perf,
    }


def score(events):
    s = song()
    return s, {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(s),
        },
        "meta": {"title": "AG04 Evidence"},
        "tracks": [{"id": "g", "events": events}],
        "render": {
            "sample_rate": SR,
            "tail_seconds": 0.1,
            "mix": {
                "tracks": [{"track": "g", "gain": 0.72, "pan": 0.0, "reverb_send": 0.0}],
                "music_bus_gain": 1.0,
                "room_return_gain": 0.0,
                "master_gain": 0.82,
            },
        },
    }


def render(name, events):
    s, sc = score(events)
    path = OUT / f"{name}.wav"
    result = render_song_score_to_files(s, sc, path)
    return result["render_ir"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    right = {"method": "finger"}

    single = {
        "E4_A_AG03_reference": None,
        "E4_B_palm_mute": {"technique": "palm_mute", "amount": 0.72},
        "E4_C_fretting_mute": {"technique": "fretting_mute", "amount": 0.72},
        "E4_D_dead_note": {"technique": "dead_note"},
        "E4_E_natural_harmonic_2": {"technique": "natural_harmonic", "harmonic_order": 2},
    }
    lines = [
        "AG04 Left-Hand Articulation / Damping — actual pipeline evidence",
        f"git_sha: {os.environ.get('GITHUB_SHA', 'local')}",
        "sample_rate: 24000",
        "",
        "Single-note set: identical E4/string1/fret0/velocity/finger right-hand.",
    ]

    for name, left in single.items():
        render(
            name,
            [note("n", 0.0, 0.65, 64, 1, 0, right=right, left=left)],
        )
        lines.append(name)

    phrases = {
        "PHRASE_A_plain_E4_to_A4": [
            note("a", 0.0, 0.55, 64, 1, 0, right=right),
            note("b", 0.5, 0.70, 69, 1, 5, right=right),
        ],
        "PHRASE_B_slide_E4_to_A4": [
            note("a", 0.0, 0.55, 64, 1, 0, right=right),
            note("b", 0.5, 0.70, 69, 1, 5, left={"technique": "slide", "transition_ms": 90}),
        ],
        "PHRASE_C_plain_E4_to_G4": [
            note("a", 0.0, 0.55, 64, 1, 0, right=right),
            note("b", 0.5, 0.70, 67, 1, 3, right=right),
        ],
        "PHRASE_D_hammer_E4_to_G4": [
            note("a", 0.0, 0.55, 64, 1, 0, right=right),
            note("b", 0.5, 0.70, 67, 1, 3, left={"technique": "hammer_on"}),
        ],
        "PHRASE_E_plain_G4_to_E4": [
            note("a", 0.0, 0.55, 67, 1, 3, right=right),
            note("b", 0.5, 0.70, 64, 1, 0, right=right),
        ],
        "PHRASE_F_pull_G4_to_E4": [
            note("a", 0.0, 0.55, 67, 1, 3, right=right),
            note("b", 0.5, 0.70, 64, 1, 0, left={"technique": "pull_off"}),
        ],
    }
    lines += ["", "Transition phrases: plain picked transition followed by AG04 left-hand-only version."]
    for name, events in phrases.items():
        ir = render(name, events)
        second = ir["tracks"][0]["events"][1]["performance"]
        if "_plain_" not in name:
            lh = second.get("left_hand_realization")
            if not isinstance(lh, dict) or not lh.get("transition"):
                raise AssertionError(f"{name}: missing AG04 transition realization")
            if "right_hand_realization" in second:
                raise AssertionError(f"{name}: transition destination acquired a right-hand strike")
        lines.append(name)

    lines += [
        "",
        "Human gate:",
        "1. A reference must retain the accepted AG03 guitar identity.",
        "2. palm/fretting/dead note must sound like damping/contact changes, not EQ presets.",
        "3. natural harmonic should remain a guitar note but with a clearer harmonic-mode character.",
        "4. slide must audibly connect source and destination pitch.",
        "5. hammer-on/pull-off destination must not sound like a fresh picked note.",
        "AG04 remains OPEN until explicit human listening PASS.",
    ]
    (OUT / "MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
