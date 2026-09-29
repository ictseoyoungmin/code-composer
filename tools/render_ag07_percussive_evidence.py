#!/usr/bin/env python3
"""Render AG07 same-guitar percussive action evidence."""
from __future__ import annotations

import json
import os
from pathlib import Path
import wave

import numpy as np

from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files


OUT = Path(os.environ.get("AG07_EVIDENCE_DIR", "artifacts/ag07-percussive-guitar"))
SR = 24000
BPM = 96


def song():
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG07 Percussive Guitar Evidence", "global_seed": 83},
        "transport": {"bpm": BPM, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
        "tonal": {"root": "E", "scale": "minor"},
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
        "tracks": [{"id": "g", "function": "percussive-fingerstyle", "instrument": "guitar"}],
        "materials": [{"id": "m", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": "part", "section": "a", "track": "g", "material": "m"}],
    }


def note(eid, start, midi=52, string=4, fret=2, method="thumb", dur=0.8, velocity=0.62):
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


def action(eid, start, kind, **parameters):
    return {
        "id": eid,
        "type": "instrument_action",
        "start_beat": float(start),
        "duration_beats": 0.08,
        "action": kind,
        "parameters": parameters,
    }


def score(events):
    s = song()
    return s, {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(s),
        },
        "meta": {"title": "AG07 Percussive Guitar Evidence"},
        "tracks": [{"id": "g", "events": events}],
        "render": {
            "sample_rate": SR,
            "tail_seconds": 0.1,
            "mix": {
                "tracks": [{"track": "g", "gain": 0.34, "pan": 0.0, "reverb_send": 0.0}],
                "music_bus_gain": 1.0,
                "room_return_gain": 0.0,
                "master_gain": 0.80,
            },
        },
    }


def read_wav(path):
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2").astype(np.float64) / 32767.0
    return data.reshape(-1, channels)


def metrics(path):
    x = read_wav(path)
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    rms = float(np.sqrt(np.mean(x * x)) + 1e-12)
    if peak >= 0.98:
        raise AssertionError(f"{path.name}: peak {peak:.6f} >= 0.98")
    return {"peak_abs": peak, "rms": rms}


def render_case(name, events):
    s, sc = score(events)
    path = OUT / f"{name}.wav"
    result = render_song_score_to_files(
        s,
        sc,
        path,
        render_ir_path=OUT / f"{name}_render_ir.json",
    )
    m = metrics(path)
    actions = [
        e for e in result["render_ir"]["tracks"][0]["events"]
        if e.get("event_type") == "instrument_action"
    ]
    notes = [e for e in result["render_ir"]["tracks"][0]["events"] if "midi" in e]
    return {
        **m,
        "action_count": len(actions),
        "note_count": len(notes),
        "actions": [
            {
                "action": e["action"],
                "start_beat": e["start_beat"],
                "duration_beats": e["duration_beats"],
                "parameters": e["parameters"],
            }
            for e in actions
        ],
        "notes": [
            {
                "midi": e["midi"],
                "start_beat": e["start_beat"],
                "duration_beats": e["duration_beats"],
            }
            for e in notes
        ],
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    cases = {
        "A_body_tap_lower_bout": [
            action("a", 0.0, "body_tap", strength=0.68, location="lower_bout")
        ],
        "B_body_tap_upper_bout": [
            action("b", 0.0, "body_tap", strength=0.68, location="upper_bout")
        ],
        "C_top_slap_soundboard": [
            action("c", 0.0, "top_slap", strength=0.66, location="soundboard")
        ],
        "D_bridge_hit": [
            action("d", 0.0, "bridge_hit", strength=0.62, location="bridge")
        ],
        "E_string_slap": [
            action("e", 0.0, "string_slap", strength=0.66, location="strings")
        ],
        "F_muted_strum_down": [
            action(
                "f", 0.0, "muted_strum",
                strength=0.70, direction="down", traversal_ms=42.0,
                string_count=6, location="strings",
            )
        ],
        "G_muted_strum_up": [
            action(
                "g", 0.0, "muted_strum",
                strength=0.70, direction="up", traversal_ms=42.0,
                string_count=6, location="strings",
            )
        ],
        "H_dead_strum_down": [
            action(
                "h", 0.0, "dead_strum",
                strength=0.72, direction="down", traversal_ms=38.0,
                string_count=6, location="strings",
            )
        ],
        "I_nail_click": [
            action("i", 0.0, "nail_click", strength=0.55, location="rim")
        ],
        "J_thumb_bass_only": [
            note("j-note", 0.0, midi=52, string=4, fret=2, method="thumb")
        ],
        "K_thumb_bass_plus_top_slap": [
            note("k-note", 0.0, midi=52, string=4, fret=2, method="thumb"),
            action("k-slap", 0.0, "top_slap", strength=0.58, location="soundboard"),
        ],
        "L_percussive_fingerstyle_phrase": [
            note("l0", 0.0, midi=52, string=4, fret=2, method="thumb", dur=0.9),
            action("l1", 0.5, "top_slap", strength=0.56, location="soundboard"),
            note("l2", 1.0, midi=59, string=2, fret=0, method="finger", dur=0.65),
            action("l3", 1.5, "string_slap", strength=0.58, location="strings"),
            note("l4", 2.0, midi=55, string=3, fret=0, method="finger", dur=0.75),
            action(
                "l5", 2.5, "dead_strum",
                strength=0.62, direction="down", traversal_ms=36.0,
                string_count=6, location="strings",
            ),
            note("l6", 3.0, midi=52, string=4, fret=2, method="thumb", dur=0.75),
            action("l7", 3.0, "body_tap", strength=0.48, location="lower_bout"),
        ],
    }

    reports = {}
    for name, events in cases.items():
        reports[name] = render_case(name, events)

    # Same-onset combo must preserve exact note authority.
    combo = reports["K_thumb_bass_plus_top_slap"]
    if combo["note_count"] != 1 or combo["action_count"] != 1:
        raise AssertionError("thumb+slap combo dropped note or action")
    if combo["notes"][0] != {"midi": 52, "start_beat": 0.0, "duration_beats": 0.8}:
        raise AssertionError("thumb+slap combo rewrote authored note state")

    # Location and traversal diagnostics must not collapse to identical audio metrics.
    lower = reports["A_body_tap_lower_bout"]
    upper = reports["B_body_tap_upper_bout"]
    if abs(lower["rms"] - upper["rms"]) < 1e-6:
        raise AssertionError("body tap locations collapsed to identical RMS")

    if abs(
        reports["F_muted_strum_down"]["rms"]
        - reports["G_muted_strum_up"]["rms"]
    ) < 1e-7:
        raise AssertionError("muted-strum direction diagnostic collapsed")

    (OUT / "REPORT.json").write_text(
        json.dumps(reports, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "AG07 Percussive Guitar — actual-pipeline evidence",
        f"git_sha: {os.environ.get('GITHUB_SHA','local')}",
        f"sample_rate: {SR}",
        "All actions are instrument_action events on the acoustic-guitar track.",
        "No percussion engine, drum event, sample, or IR is used.",
        "",
    ]
    for name, report in reports.items():
        lines.append(
            f"{name}: peak={report['peak_abs']:.6f} rms={report['rms']:.6f} "
            f"notes={report['note_count']} actions={report['action_count']}"
        )
    lines += [
        "",
        "Human gate:",
        "1. body_tap/top_slap/bridge_hit should share one guitar-body identity while differing by contact location/character.",
        "2. string_slap/muted_strum/dead_strum must read as guitar string/body contact, not a generic drum kit.",
        "3. muted-strum down/up should retain a physical traversal difference.",
        "4. thumb_bass_plus_top_slap must sound like one player performing both on one guitar.",
        "5. percussive_fingerstyle_phrase should integrate pitched notes and percussion without either feeling pasted on.",
        "AG07 remains OPEN until explicit human listening PASS.",
    ]
    (OUT / "MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
