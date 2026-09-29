#!/usr/bin/env python3
"""AG09 Dogfood 1 — production fingerstyle solo.

One acoustic-guitar track, explicitly authored string/fret/right-hand/arpeggio
mechanics, rendered through the accepted AG08 S5 performance preset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import numpy as np

from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files
from code_composer.execution.performance_score import performance_score_fingerprint


SR = 24000
BPM = 78
PRESET = "acoustic_guitar.steel_stateful_performance"
OPEN = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}
OFFSETS = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5)
DURS = (1.8, 1.1, 0.9, 1.0, 1.4, 0.9, 1.3, 0.9)

# (midi, string, fret, player, voice, base_velocity)
BARS = [
    [(40,6,0,"thumb","bass",.66),(47,5,2,"thumb","bass",.54),(66,1,2,"ring","treble",.68),(55,3,0,"index","inner",.47),
     (52,4,2,"thumb","bass",.57),(59,2,0,"middle","treble",.51),(67,1,3,"ring","treble",.72),(55,3,0,"index","inner",.45)],
    [(48,5,3,"thumb","bass",.63),(52,4,2,"thumb","bass",.53),(67,1,3,"ring","treble",.67),(55,3,0,"index","inner",.46),
     (43,6,3,"thumb","bass",.57),(60,2,1,"middle","treble",.50),(64,1,0,"ring","treble",.65),(55,3,0,"index","inner",.44)],
    [(43,6,3,"thumb","bass",.64),(50,4,0,"thumb","bass",.53),(59,2,0,"middle","treble",.63),(55,3,0,"index","inner",.46),
     (47,5,2,"thumb","bass",.56),(62,2,3,"middle","treble",.56),(67,1,3,"ring","treble",.70),(55,3,0,"index","inner",.45)],
    [(42,6,2,"thumb","bass",.66),(50,4,0,"thumb","bass",.54),(57,3,2,"index","inner",.49),(62,2,3,"middle","treble",.65),
     (45,5,0,"thumb","bass",.58),(57,3,2,"index","inner",.48),(66,1,2,"ring","treble",.72),(62,2,3,"middle","treble",.55)],
    [(40,6,0,"thumb","bass",.68),(47,5,2,"thumb","bass",.56),(59,2,0,"middle","treble",.66),(55,3,0,"index","inner",.48),
     (52,4,2,"thumb","bass",.59),(62,2,3,"middle","treble",.57),(67,1,3,"ring","treble",.73),(55,3,0,"index","inner",.47)],
    [(48,5,3,"thumb","bass",.64),(52,4,2,"thumb","bass",.54),(64,1,0,"ring","treble",.68),(55,3,0,"index","inner",.47),
     (43,6,3,"thumb","bass",.58),(60,2,1,"middle","treble",.54),(64,1,0,"ring","treble",.63),(55,3,0,"index","inner",.46)],
    [(45,5,0,"thumb","bass",.65),(52,4,2,"thumb","bass",.54),(60,2,1,"middle","treble",.65),(55,3,0,"index","inner",.48),
     (40,6,0,"thumb","bass",.57),(52,4,2,"thumb","bass",.52),(64,1,0,"ring","treble",.69),(60,2,1,"middle","treble",.53)],
    [(47,5,2,"thumb","bass",.70),(51,4,1,"thumb","bass",.58),(66,1,2,"ring","treble",.72),(57,3,2,"index","inner",.51),
     (42,6,2,"thumb","bass",.62),(51,4,1,"thumb","bass",.55),(63,2,4,"middle","treble",.69),(57,3,2,"index","inner",.49)],
    [(48,5,3,"thumb","bass",.64),(52,4,2,"thumb","bass",.53),(64,1,0,"ring","treble",.66),(55,3,0,"index","inner",.47),
     (43,6,3,"thumb","bass",.57),(59,2,0,"middle","treble",.52),(67,1,3,"ring","treble",.70),(55,3,0,"index","inner",.45)],
    [(47,5,2,"thumb","bass",.63),(50,4,0,"thumb","bass",.52),(62,2,3,"middle","treble",.64),(55,3,0,"index","inner",.46),
     (43,6,3,"thumb","bass",.55),(59,2,0,"middle","treble",.50),(67,1,3,"ring","treble",.61),(55,3,0,"index","inner",.44)],
    [(42,6,2,"thumb","bass",.65),(50,4,0,"thumb","bass",.53),(64,1,0,"ring","treble",.66),(57,3,2,"index","inner",.48),
     (45,5,0,"thumb","bass",.57),(62,2,3,"middle","treble",.54),(66,1,2,"ring","treble",.70),(57,3,2,"index","inner",.46)],
    [(40,6,0,"thumb","bass",.62),(47,5,2,"thumb","bass",.50),(66,1,2,"ring","treble",.62),(55,3,0,"index","inner",.43),
     (52,4,2,"thumb","bass",.52),(59,2,0,"middle","treble",.46),(64,1,0,"ring","treble",.65),(55,3,0,"index","inner",.40)],
]
BAR_SCALE = (.96,.91,.93,.99,1.02,.97,1.00,1.06,.98,.93,1.00,.88)


def build_song():
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "Ash Between Pines", "global_seed": 1919001, "revision": "AG09-D1-R0"},
        "transport": {"bpm": BPM, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
        "tonal": {"root": "E", "scale": "natural_minor"},
        "sections": [{"id": "solo", "bars": 12, "name": "Fingerstyle Solo"}],
        "instruments": [{
            "id": "guitar",
            "family": "acoustic_guitar",
            "variant": "steel-string",
            "render_lock": {"preset": PRESET, "preset_version": "1.0.0"},
        }],
        "tracks": [{"id": "guitar", "function": "fingerstyle-solo", "instrument": "guitar"}],
        "materials": [{"id": "fingerstyle", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": "solo-part", "section": "solo", "track": "guitar", "material": "fingerstyle"}],
    }


def _event(event_id, start, duration, midi, string, fret, player, voice, velocity, gesture, sequence):
    method = "thumb" if player == "thumb" else "finger"
    return {
        "id": event_id,
        "type": "note",
        "start_beat": float(start),
        "duration_beats": float(duration),
        "midi": int(midi),
        "velocity": float(max(0.05, min(0.95, velocity))),
        "instrument_performance": {
            "string": int(string),
            "fret": int(fret),
            "right_hand": {"method": method},
            "arpeggio": {
                "gesture_id": gesture,
                "player": player,
                "voice": voice,
                "sequence_index": int(sequence),
            },
        },
    }


def build_events():
    events = []
    for bar_index, notes in enumerate(BARS):
        if len(notes) != 8:
            raise ValueError(f"bar {bar_index+1}: expected 8 authored contacts")
        gesture = f"bar-{bar_index+1:02d}"
        base = bar_index * 4.0
        for seq, ((midi,string,fret,player,voice,vel), offset, dur) in enumerate(zip(notes, OFFSETS, DURS)):
            if int(midi) != OPEN[int(string)] + int(fret):
                raise ValueError(
                    f"bar {bar_index+1} event {seq}: midi/string/fret mismatch "
                    f"{midi} != {OPEN[int(string)]}+{fret}"
                )
            if voice == "bass" and string not in (4,5,6):
                raise ValueError("bass voice must stay on strings 4-6")
            if voice == "inner" and string != 3:
                raise ValueError("inner voice must stay on string 3")
            if voice == "treble" and string not in (1,2):
                raise ValueError("treble voice must stay on strings 1-2")
            if bar_index == 11 and seq == 6:
                duration = 0.95
            elif bar_index == 11 and seq == 7:
                duration = 0.45
            else:
                duration = dur
            events.append(_event(
                f"b{bar_index+1:02d}e{seq}",
                base + offset,
                duration,
                midi,
                string,
                fret,
                player,
                voice,
                vel * BAR_SCALE[bar_index],
                gesture,
                seq,
            ))
    return events


def build_score(song):
    events = build_events()
    return {
        "format": "code-composer-performance-score/v1",
        "source_song": {"format": "code-composer-song/v1", "fingerprint": song_fingerprint(song)},
        "meta": {"title": "Ash Between Pines — AG09 D1 R0"},
        "tracks": [{"id": "guitar", "events": deepcopy(events)}],
        "render": {
            "sample_rate": SR,
            "tail_seconds": 2.6,
            "mix": {
                "tracks": [{"track": "guitar", "gain": 0.50, "pan": 0.0, "reverb_send": 0.0}],
                "music_bus_gain": 1.0,
                "room_return_gain": 0.0,
                "master_gain": 0.82,
            },
        },
    }


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _rms(audio):
    x = np.asarray(audio, dtype=np.float64)
    return float(np.sqrt(np.mean(x*x))) if x.size else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    song = build_song()
    score = build_score(song)
    wav_a = out / "01_ash_between_pines_R0.wav"
    wav_b = out / "02_ash_between_pines_R0_repeat.wav"

    result_a = render_song_score_to_files(
        song, score, wav_a,
        plan_path=out/"execution_plan.json",
        render_ir_path=out/"render_ir.json",
        resolved_path=out/"resolved_ir.json",
        analysis_path=out/"audio_analysis.json",
    )
    result_b = render_song_score_to_files(song, score, wav_b)

    audio_a = np.asarray(result_a["audio"], dtype=np.float64)
    audio_b = np.asarray(result_b["audio"], dtype=np.float64)
    deterministic = bool(np.array_equal(audio_a, audio_b))
    finite = bool(np.isfinite(audio_a).all())
    peak = float(np.max(np.abs(audio_a))) if audio_a.size else 0.0
    clipped = float(np.mean(np.abs(audio_a) >= 1.0)) if audio_a.size else 0.0
    authored = build_events()
    realized = result_a["render_ir"]["tracks"][0]["events"]

    if int(result_a["sr"]) != SR:
        raise SystemExit(f"expected {SR} Hz, got {result_a['sr']}")
    if not deterministic:
        raise SystemExit("fingerstyle dogfood is not deterministic")
    if not finite:
        raise SystemExit("fingerstyle dogfood contains non-finite samples")
    if clipped != 0.0 or peak >= 0.98:
        raise SystemExit(f"unsafe output peak={peak} clipped={clipped}")
    if len(realized) != len(authored):
        raise SystemExit(f"event authority changed {len(authored)} -> {len(realized)}")
    if [e["id"] for e in realized] != [e["id"] for e in authored]:
        raise SystemExit("authored event identity/order changed")

    report = result_a["render_ir"].get("guitar_performance_report", {})
    track_report = (report.get("tracks") or {}).get("guitar", {})
    gesture_count = len(track_report.get("arpeggio_gestures") or {})
    if gesture_count != 12:
        raise SystemExit(f"expected 12 fingerstyle gestures, got {gesture_count}")

    song_path = out / "song.json"
    score_path = out / "performance_score.json"
    song_path.write_text(json.dumps(song, indent=2) + "\n", encoding="utf-8")
    score_path.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")

    metrics = {
        "schema": "code-composer-ag09-fingerstyle-dogfood/v1",
        "title": song["meta"]["title"],
        "revision": song["meta"]["revision"],
        "sample_rate": SR,
        "bpm": BPM,
        "bars": 12,
        "duration_seconds": len(audio_a) / SR,
        "authored_event_count": len(authored),
        "render_ir_event_count": len(realized),
        "arpeggio_gesture_count": gesture_count,
        "rms": _rms(audio_a),
        "peak": peak,
        "clipped_sample_ratio": clipped,
        "finite": finite,
        "deterministic": deterministic,
        "sha256": _sha256(wav_a),
        "sha256_repeat": _sha256(wav_b),
        "song_fingerprint": song_fingerprint(song),
        "performance_score_fingerprint": performance_score_fingerprint(score),
        "preset": PRESET,
        "automatic_aesthetic_score": False,
        "human_listening_required": True,
    }
    (out/"metrics.json").write_text(json.dumps(metrics, indent=2)+"\n", encoding="utf-8")
    (out/"README.md").write_text(
        "# AG09 Dogfood 1 — Ash Between Pines\n\n"
        "12-bar / 78 BPM / 24 kHz solo steel-string fingerstyle candidate. "
        "One persistent acoustic-guitar track carries authored bass, inner, and melody voices "
        "through the accepted AG08 stateful performance preset.\n\n"
        "Listen to 01_ash_between_pines_R0.wav. The repeat file exists only for deterministic QA. "
        "Closure requires human listening; no automatic aesthetic score is used.\n",
        encoding="utf-8",
    )

    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    (out/"SHA256SUMS.txt").write_text(
        "".join(f"{_sha256(p)}  {p.relative_to(out).as_posix()}\n" for p in files),
        encoding="utf-8",
    )
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
