#!/usr/bin/env python3
"""Render AG05 C/F picked-vs-fingerstyle arpeggio evidence."""
from __future__ import annotations

import json
import os
from pathlib import Path
import wave

import numpy as np

from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files


OUT = Path(os.environ.get("AG05_EVIDENCE_DIR", "artifacts/ag05-arpeggio"))
SR = 24000


def song():
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG05 Multi-string Evidence", "global_seed": 67},
        "transport": {"bpm": 92, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
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
        "tracks": [{"id": "g", "function": "arpeggio", "instrument": "guitar"}],
        "materials": [{"id": "m", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": "part", "section": "a", "track": "g", "material": "m"}],
    }


def note(eid, start, dur, midi, string, fret, player, voice, seq, gesture, mode):
    method = "pick" if mode == "pick" else ("thumb" if player == "thumb" else "finger")
    return {
        "id": eid,
        "type": "note",
        "start_beat": float(start),
        "duration_beats": float(dur),
        "midi": int(midi),
        "velocity": 0.65,
        "instrument_performance": {
            "string": int(string),
            "fret": int(fret),
            "right_hand": {"method": method},
            "arpeggio": {
                "gesture_id": gesture,
                "player": "pick" if mode == "pick" else player,
                "voice": voice,
                "sequence_index": int(seq),
            },
        },
    }


def pattern(chord, mode):
    if chord == "C":
        data = [
            (48,5,3,"thumb","bass",1.50),
            (52,4,2,"thumb","bass",1.25),
            (55,3,0,"index","inner",1.00),
            (60,2,1,"middle","treble",0.50),
            (64,1,0,"ring","treble",0.80),
            (60,2,1,"middle","treble",0.70),
            (55,3,0,"index","inner",0.80),
            (52,4,2,"thumb","bass",0.80),
        ]
    elif chord == "F":
        data = [
            (41,6,1,"thumb","bass",1.50),
            (48,5,3,"thumb","bass",1.25),
            (53,4,3,"thumb","bass",1.00),
            (57,3,2,"index","inner",0.50),
            (60,2,1,"middle","treble",0.50),
            (65,1,1,"ring","treble",0.70),
            (60,2,1,"middle","treble",0.80),
            (57,3,2,"index","inner",0.80),
        ]
    else:
        raise ValueError(chord)

    gesture = f"{chord.lower()}-{mode}"
    events = []
    for i, (midi, string, fret, player, voice, dur) in enumerate(data):
        events.append(note(
            f"{chord.lower()}{i}",
            i * 0.25,
            dur,
            midi,
            string,
            fret,
            player,
            voice,
            i,
            gesture,
            mode,
        ))
    return events


def score(events):
    s = song()
    return s, {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(s),
        },
        "meta": {"title": "AG05 Multi-string Evidence"},
        "tracks": [{"id": "g", "events": events}],
        "render": {
            "sample_rate": SR,
            "tail_seconds": 0.1,
            "mix": {
                "tracks": [{"track": "g", "gain": 0.42, "pan": 0.0, "reverb_send": 0.0}],
                "music_bus_gain": 1.0,
                "room_return_gain": 0.0,
                "master_gain": 0.82,
            },
        },
    }


def event_identity(events):
    return [
        (
            int(e["midi"]),
            float(e["start_beat"]),
            float(e["duration_beats"]),
            float(e["velocity"]),
            int(e["instrument_performance"]["string"]),
            int(e["instrument_performance"]["fret"]),
        )
        for e in events
    ]


def _peak_abs(path):
    with wave.open(str(path), "rb") as wf:
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2")
    if data.size == 0:
        return 0.0
    return float(np.max(np.abs(data.astype(np.float64) / 32767.0)))


def render_case(chord, mode):
    events = pattern(chord, mode)
    s, sc = score(events)
    wav_path = OUT / f"{chord}_{mode}_arpeggio.wav"
    result = render_song_score_to_files(
        s,
        sc,
        wav_path,
        render_ir_path=OUT / f"{chord}_{mode}_render_ir.json",
    )
    peak = _peak_abs(wav_path)
    if peak >= 0.98:
        raise AssertionError(f"{chord}/{mode}: evidence peak {peak:.6f} >= 0.98")
    report = result["guitar_performance_report"]["tracks"]["g"]
    gesture_id = next(iter(report["arpeggio_gestures"]))
    gesture = report["arpeggio_gestures"][gesture_id]
    if gesture["max_distinct_string_overlap"] < 3:
        raise AssertionError(f"{chord}/{mode}: insufficient independent string overlap")
    if gesture["bass_upper_overlap_count"] < 1:
        raise AssertionError(f"{chord}/{mode}: bass does not sustain under upper voice")
    gesture = dict(gesture)
    gesture["audio_peak_abs"] = peak
    return events, gesture


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = [
        "AG05 Arpeggio / Fingerstyle — actual-pipeline evidence",
        f"git_sha: {os.environ.get('GITHUB_SHA', 'local')}",
        f"sample_rate: {SR}",
        "C and F use explicit authored guitar voicings.",
        "Picked and fingerstyle versions have identical MIDI/onset/duration/velocity/string/fret content.",
        "",
    ]
    summary = {}

    for chord in ("C", "F"):
        finger_events, finger_report = render_case(chord, "fingerstyle")
        pick_events, pick_report = render_case(chord, "pick")
        if event_identity(finger_events) != event_identity(pick_events):
            raise AssertionError(f"{chord}: picked/fingerstyle authored note identity drift")

        summary[chord] = {
            "fingerstyle": finger_report,
            "pick": pick_report,
            "authored_note_identity_equal": True,
        }
        manifest += [
            f"{chord}: authored_note_identity_equal=true",
            f"  fingerstyle overlap={finger_report['max_distinct_string_overlap']} "
            f"bass_upper={finger_report['bass_upper_overlap_count']} "
            f"peak={finger_report['audio_peak_abs']:.6f} "
            f"players={finger_report['players']}",
            f"  pick overlap={pick_report['max_distinct_string_overlap']} "
            f"bass_upper={pick_report['bass_upper_overlap_count']} "
            f"peak={pick_report['audio_peak_abs']:.6f}",
        ]

    (OUT / "REPORT.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    manifest += [
        "",
        "Human gate:",
        "1. Both C and F must sound like multiple independent guitar strings ringing together over time.",
        "2. Bass sustain should remain underneath later inner/treble notes.",
        "3. Fingerstyle should read as thumb + fingers; picked arpeggio as one pick moving note-by-note.",
        "4. The difference must come from explicit AG03 right-hand methods, not invented timing or notes.",
        "5. Neither render should sound like a block chord merely unfolded by MIDI.",
        "AG05 remains OPEN until explicit human listening PASS.",
    ]
    (OUT / "MANIFEST.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print("\n".join(manifest))


if __name__ == "__main__":
    main()
