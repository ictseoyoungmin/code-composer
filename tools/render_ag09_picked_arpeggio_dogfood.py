#!/usr/bin/env python3
"""AG09 Dogfood 2 — production picked arpeggio.

A single persistent acoustic-guitar track with explicit string/fret authority and
per-note pick mechanics. The musical candidate deliberately revisits several
pitches on alternate physical strings so the listening gate can judge whether
position-dependent color remains distinct without sounding like separate
instruments.
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
BPM = 92
PRESET = "acoustic_guitar.steel_stateful_performance"
OPEN = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}
OFFSETS = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5)
DURS = (1.55, 1.05, 0.92, 0.82, 1.18, 0.78, 0.88, 0.42)
ANGLE = (34.0, 48.0, 36.0, 50.0, 32.0, 47.0, 37.0, 46.0)
PLUCK = (0.125, 0.145, 0.155, 0.135, 0.115, 0.140, 0.150, 0.145)
STRENGTH = (0.68, 0.52, 0.50, 0.56, 0.72, 0.54, 0.49, 0.46)


# Pitch classes use C=0 ... B=11. Every authored pitch must either belong to
# the active harmony or be declared as a non-chord tone with explicit
# provenance/resolution. R2 intentionally uses no undeclared non-chord tones.
HARMONIC_PLAN = [
    {"label": "Em(add9)", "allowed": {4, 6, 7, 11}, "required": {4, 6, 7, 11}, "bass_pc": 4},
    {"label": "Cmaj7",   "allowed": {0, 4, 7, 11}, "required": {0, 4, 7, 11}, "bass_pc": 0},
    {"label": "G6",      "allowed": {2, 4, 7, 11}, "required": {2, 4, 7, 11}, "bass_pc": 7},
    {"label": "D/F#",    "allowed": {2, 6, 9},     "required": {2, 6, 9},     "bass_pc": 6},
    {"label": "Em7",     "allowed": {2, 4, 7, 11}, "required": {2, 4, 7, 11}, "bass_pc": 4},
    {"label": "Cmaj9",   "allowed": {0, 2, 4, 7, 11}, "required": {0, 2, 4, 7, 11}, "bass_pc": 0},
    {"label": "Am7",     "allowed": {0, 4, 7, 9},  "required": {0, 4, 7, 9},  "bass_pc": 9},
    {"label": "B7",      "allowed": {3, 6, 9, 11}, "required": {3, 6, 9, 11}, "bass_pc": 11},
    {"label": "Em/G",    "allowed": {4, 7, 11},    "required": {4, 7, 11},    "bass_pc": 7},
    {"label": "Cmaj7",   "allowed": {0, 4, 7, 11}, "required": {0, 4, 7, 11}, "bass_pc": 0},
    {"label": "B7sus4->B7", "allowed": {3, 4, 6, 9, 11}, "required": {3, 4, 6, 9, 11}, "bass_pc": 11},
    {"label": "Em(add9)", "allowed": {4, 6, 7, 11}, "required": {4, 6, 7, 11}, "bass_pc": 4},
]
NON_CHORD_TONES = []

# (midi, string, fret, voice, base_velocity)
# Harmonic path:
# Em(add9) -> Cmaj7 -> G6 -> D/F# -> Em7 -> Cmaj9 ->
# Am7 -> B7 -> Em/G -> Cmaj7 -> B7sus4->B7 -> Em(add9)
BARS = [
    [(40,6,0,"bass",.68),(52,4,2,"inner",.54),(55,3,0,"inner",.50),(59,2,0,"treble",.56),
     (66,1,2,"treble",.72),(55,3,0,"inner",.50),(52,4,2,"inner",.47),(59,2,0,"treble",.45)],
    [(48,5,3,"bass",.66),(52,4,2,"inner",.53),(55,3,0,"inner",.50),(59,2,0,"treble",.58),
     (64,1,0,"treble",.72),(55,3,0,"inner",.49),(52,4,2,"inner",.46),(59,2,0,"treble",.44)],
    [(43,6,3,"bass",.69),(50,4,0,"inner",.52),(55,3,0,"inner",.50),(59,2,0,"treble",.58),
     (64,1,0,"treble",.74),(55,3,0,"inner",.50),(50,4,0,"inner",.46),(59,2,0,"treble",.45)],
    [(42,6,2,"bass",.68),(50,4,0,"inner",.53),(57,3,2,"inner",.51),(62,2,3,"treble",.59),
     (66,1,2,"treble",.75),(57,3,2,"inner",.50),(50,4,0,"inner",.46),(62,2,3,"treble",.45)],
    [(40,6,0,"bass",.70),(52,4,2,"inner",.55),(55,3,0,"inner",.52),(62,2,3,"treble",.60),
     (67,1,3,"treble",.76),(55,3,0,"inner",.51),(52,4,2,"inner",.47),(59,2,0,"treble",.46)],
    [(48,5,3,"bass",.67),(55,4,5,"inner",.55),(59,3,4,"inner",.52),(62,2,3,"treble",.60),
     (64,1,0,"treble",.74),(55,3,0,"inner",.50),(52,4,2,"inner",.47),(64,2,5,"treble",.48)],
    [(45,5,0,"bass",.68),(52,4,2,"inner",.54),(55,3,0,"inner",.51),(60,2,1,"treble",.59),
     (64,1,0,"treble",.73),(57,3,2,"inner",.50),(52,4,2,"inner",.46),(60,2,1,"treble",.45)],
    [(47,5,2,"bass",.72),(54,4,4,"inner",.56),(57,3,2,"inner",.53),(63,2,4,"treble",.61),
     (66,1,2,"treble",.77),(57,3,2,"inner",.51),(54,4,4,"inner",.47),(63,2,4,"treble",.46)],
    [(43,6,3,"bass",.69),(52,4,2,"inner",.55),(55,3,0,"inner",.52),(59,2,0,"treble",.59),
     (64,1,0,"treble",.75),(55,3,0,"inner",.50),(52,4,2,"inner",.47),(59,2,0,"treble",.45)],
    [(48,5,3,"bass",.67),(52,4,2,"inner",.53),(55,3,0,"inner",.50),(59,2,0,"treble",.57),
     (64,1,0,"treble",.72),(55,3,0,"inner",.48),(52,4,2,"inner",.45),(59,2,0,"treble",.43)],
    [(47,5,2,"bass",.70),(54,4,4,"inner",.55),(57,3,2,"inner",.52),(64,2,5,"treble",.60),
     (66,1,2,"treble",.76),(57,3,2,"inner",.50),(54,4,4,"inner",.46),(63,2,4,"treble",.47)],
    [(40,6,0,"bass",.66),(52,4,2,"inner",.51),(55,3,0,"inner",.48),(59,2,0,"treble",.54),
     (66,1,2,"treble",.70),(55,3,0,"inner",.46),(52,4,2,"inner",.43),(64,2,5,"treble",.48)],
]
BAR_SCALE = (.93,.96,.99,.94,1.03,.98,.96,1.04,1.00,.95,.98,.86)


def build_song():
    return {
        "format": "code-composer-song/v1",
        "meta": {
            "title": "Wirelight Current",
            "global_seed": 1919002,
            "revision": "AG09-D2-R2",
        },
        "transport": {"bpm": BPM, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
        "tonal": {"root": "E", "scale": "natural_minor"},
        "sections": [{"id": "picked", "bars": 12, "name": "Picked Arpeggio"}],
        "instruments": [{
            "id": "guitar",
            "family": "acoustic_guitar",
            "variant": "steel-string",
            "render_lock": {"preset": PRESET, "preset_version": "1.0.0"},
        }],
        "tracks": [{"id": "guitar", "function": "picked-arpeggio", "instrument": "guitar"}],
        "materials": [{"id": "picked-flow", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": "picked-part", "section": "picked", "track": "guitar", "material": "picked-flow"}],
    }


def _event(event_id, start, duration, midi, string, fret, voice, velocity, gesture, sequence):
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
            "right_hand": {
                "method": "pick",
                "pluck_position": float(PLUCK[sequence]),
                "attack_angle_deg": float(ANGLE[sequence]),
                "strength": float(STRENGTH[sequence]),
            },
            "arpeggio": {
                "gesture_id": gesture,
                "player": "pick",
                "voice": voice,
                "sequence_index": int(sequence),
            },
        },
    }


def build_events():
    events = []
    for bar_index, notes in enumerate(BARS):
        if len(notes) != 8:
            raise ValueError(f"bar {bar_index+1}: expected 8 authored pick contacts")
        gesture = f"picked-bar-{bar_index+1:02d}"
        base = bar_index * 4.0
        for seq, ((midi,string,fret,voice,vel), offset, dur) in enumerate(zip(notes, OFFSETS, DURS)):
            if int(midi) != OPEN[int(string)] + int(fret):
                raise ValueError(
                    f"bar {bar_index+1} event {seq}: midi/string/fret mismatch "
                    f"{midi} != {OPEN[int(string)]}+{fret}"
                )
            if voice == "bass" and string not in (5,6):
                raise ValueError("picked bass voice must stay on strings 5-6")
            if voice == "inner" and string not in (3,4):
                raise ValueError("picked inner voice must stay on strings 3-4")
            if voice == "treble" and string not in (1,2):
                raise ValueError("picked treble voice must stay on strings 1-2")
            duration = dur
            if bar_index == 11 and seq == 4:
                duration = 1.45
            elif bar_index == 11 and seq >= 5:
                duration = (0.76, 0.82, 0.38)[seq-5]
            events.append(_event(
                f"b{bar_index+1:02d}e{seq}",
                base + offset,
                duration,
                midi,
                string,
                fret,
                voice,
                vel * BAR_SCALE[bar_index],
                gesture,
                seq,
            ))
    return events


def build_score(song):
    return {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(song),
        },
        "meta": {"title": "Wirelight Current — AG09 D2 R2"},
        "tracks": [{"id": "guitar", "events": deepcopy(build_events())}],
        "render": {
            "sample_rate": SR,
            "tail_seconds": 2.6,
            "mix": {
                "tracks": [{"track": "guitar", "gain": 0.48, "pan": 0.0, "reverb_send": 0.0}],
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


def _position_pairs(events):
    by_pitch = {}
    for e in events:
        perf = e["instrument_performance"]
        by_pitch.setdefault(int(e["midi"]), set()).add((int(perf["string"]), int(perf["fret"])))
    return {
        str(midi): sorted([list(x) for x in positions])
        for midi, positions in by_pitch.items()
        if len(positions) >= 2
    }


def harmonic_plan_certificate(events):
    if len(HARMONIC_PLAN) != 12:
        raise ValueError("harmonic plan must contain 12 bars")

    declared_nct = {
        (int(item["bar"]), int(item["event_index"])): item
        for item in NON_CHORD_TONES
    }
    bars = []
    for bar_index, harmony in enumerate(HARMONIC_PLAN):
        bar_events = [
            e for e in events
            if bar_index * 4.0 <= float(e["start_beat"]) < (bar_index + 1) * 4.0
        ]
        if not bar_events:
            raise ValueError(f"bar {bar_index+1}: no authored notes")

        pcs = {int(e["midi"]) % 12 for e in bar_events}
        chord_events = []
        undeclared = []
        declared = []
        for event_index, event in enumerate(bar_events):
            pc = int(event["midi"]) % 12
            if pc in harmony["allowed"]:
                chord_events.append(event)
                continue
            key = (bar_index + 1, event_index)
            info = declared_nct.get(key)
            if info is None:
                undeclared.append({
                    "event_id": event["id"],
                    "midi": int(event["midi"]),
                    "pitch_class": pc,
                })
            else:
                declared.append({
                    "event_id": event["id"],
                    "midi": int(event["midi"]),
                    "kind": str(info["kind"]),
                    "resolves_to_midi": int(info["resolves_to_midi"]),
                })

        missing = sorted(int(pc) for pc in harmony["required"] - pcs)
        bass_pc = int(bar_events[0]["midi"]) % 12
        if bass_pc != int(harmony["bass_pc"]):
            raise ValueError(
                f"bar {bar_index+1} {harmony['label']}: bass pitch class "
                f"{bass_pc} != planned {harmony['bass_pc']}"
            )
        if undeclared:
            raise ValueError(
                f"bar {bar_index+1} {harmony['label']}: undeclared non-chord tones {undeclared}"
            )
        if missing:
            raise ValueError(
                f"bar {bar_index+1} {harmony['label']}: missing required pitch classes {missing}"
            )

        bars.append({
            "bar": bar_index + 1,
            "label": harmony["label"],
            "pitch_classes": sorted(pcs),
            "bass_pitch_class": bass_pc,
            "undeclared_non_chord_tones": undeclared,
            "declared_non_chord_tones": declared,
            "required_pitch_classes_present": True,
        })

    # The harmonic-minor leading tone D# in B7 must resolve upward to E at
    # the following tonic arrival. Use authored onset order, not audio analysis.
    bar11 = [
        e for e in events
        if 40.0 <= float(e["start_beat"]) < 44.0 and int(e["midi"]) % 12 == 3
    ]
    bar12_e = [
        e for e in events
        if 44.0 <= float(e["start_beat"]) < 48.0 and int(e["midi"]) % 12 == 4
    ]
    if not bar11 or not bar12_e:
        raise ValueError("B7 leading-tone resolution evidence is incomplete")
    source = max(bar11, key=lambda e: float(e["start_beat"]))
    target = min(
        (e for e in bar12_e if float(e["start_beat"]) > float(source["start_beat"])),
        key=lambda e: float(e["start_beat"]),
        default=None,
    )
    if target is None or int(target["midi"]) - int(source["midi"]) != 1:
        raise ValueError("B7 D# leading tone does not resolve by semitone to E")
    resolution_beats = float(target["start_beat"]) - float(source["start_beat"])
    if resolution_beats > 0.5 + 1e-12:
        raise ValueError(f"B7 D# -> E resolution too late: {resolution_beats} beats")

    return {
        "valid": True,
        "bars": bars,
        "non_chord_tone_count": len(NON_CHORD_TONES),
        "undeclared_non_chord_tone_count": 0,
        "leading_tone_resolution": {
            "source_event_id": source["id"],
            "source_midi": int(source["midi"]),
            "target_event_id": target["id"],
            "target_midi": int(target["midi"]),
            "resolution_beats": resolution_beats,
            "direction_semitones": int(target["midi"]) - int(source["midi"]),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    song = build_song()
    score = build_score(song)
    authored = build_events()
    harmonic_certificate = harmonic_plan_certificate(authored)
    wav_a = out / "01_wirelight_current_R2.wav"
    wav_b = out / "02_wirelight_current_R2_repeat.wav"

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
    realized = result_a["render_ir"]["tracks"][0]["events"]
    deterministic = bool(np.array_equal(audio_a, audio_b))
    finite = bool(np.isfinite(audio_a).all())
    peak = float(np.max(np.abs(audio_a))) if audio_a.size else 0.0
    clipped = float(np.mean(np.abs(audio_a) >= 1.0)) if audio_a.size else 0.0

    if int(result_a["sr"]) != SR:
        raise SystemExit(f"expected {SR} Hz, got {result_a['sr']}")
    if not deterministic:
        raise SystemExit("picked arpeggio dogfood is not deterministic")
    if not finite:
        raise SystemExit("picked arpeggio dogfood contains non-finite samples")
    if clipped != 0.0 or peak >= 0.98:
        raise SystemExit(f"unsafe output peak={peak} clipped={clipped}")
    if len(realized) != len(authored):
        raise SystemExit(f"event authority changed {len(authored)} -> {len(realized)}")

    authored_core = [
        (int(e["midi"]), float(e["start_beat"]), float(e["duration_beats"]))
        for e in authored
    ]
    realized_core = [
        (int(e["midi"]), float(e["start_beat"]), float(e["duration_beats"]))
        for e in realized
    ]
    if realized_core != authored_core:
        raise SystemExit("authored pitch/start/duration authority changed")

    report = result_a["render_ir"].get("guitar_performance_report", {})
    track_report = (report.get("tracks") or {}).get("guitar", {})
    gestures = track_report.get("arpeggio_gestures") or {}
    if len(gestures) != 12:
        raise SystemExit(f"expected 12 picked arpeggio gestures, got {len(gestures)}")
    if int(track_report.get("right_hand_event_count", -1)) != len(authored):
        raise SystemExit("not every D2 note retained explicit AG03 pick mechanics")
    for gesture in gestures.values():
        if any(player != "pick" for player in gesture.get("players", [])):
            raise SystemExit("non-pick player leaked into D2 arpeggio gesture")

    pairs = _position_pairs(authored)
    required = {
        "55": {(3,0),(4,5)},
        "59": {(2,0),(3,4)},
        "64": {(1,0),(2,5)},
    }
    for midi, expected in required.items():
        observed = {tuple(x) for x in pairs.get(midi, [])}
        if not expected.issubset(observed):
            raise SystemExit(f"missing alternate physical positions for MIDI {midi}: {observed}")

    (out/"song.json").write_text(json.dumps(song, indent=2)+"\n", encoding="utf-8")
    (out/"performance_score.json").write_text(json.dumps(score, indent=2)+"\n", encoding="utf-8")

    metrics = {
        "schema": "code-composer-ag09-picked-arpeggio-dogfood/v1",
        "title": song["meta"]["title"],
        "revision": song["meta"]["revision"],
        "harmonic_path": [item["label"] for item in HARMONIC_PLAN],
        "harmonic_plan_certificate": harmonic_certificate,
        "sample_rate": SR,
        "bpm": BPM,
        "bars": 12,
        "duration_seconds": len(audio_a) / SR,
        "authored_event_count": len(authored),
        "render_ir_event_count": len(realized),
        "arpeggio_gesture_count": len(gestures),
        "right_hand_pick_event_count": int(track_report.get("right_hand_event_count", 0)),
        "alternate_position_pitches": pairs,
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
        "# AG09 Dogfood 2 — Wirelight Current\n\n"
        "12-bar / 92 BPM / 24 kHz steel-string picked-arpeggio candidate with an explicit harmonic path. "
        "Every authored note carries explicit string/fret and AG03 pick mechanics. "
        "MIDI 55, 59, and 64 intentionally recur on alternate physical strings so "
        "the human gate can judge string/fret color separation inside a musical phrase.\n\n"
        "Harmonic path: Em(add9) -> Cmaj7 -> G6 -> D/F# -> Em7 -> Cmaj9 -> Am7 -> B7 -> Em/G -> Cmaj7 -> B7sus4->B7 -> Em(add9).\\n\\n"
        "R2 hard-validates chord-tone membership, required chord tones, bass authority, and B7 D# -> E resolution.\\n\\n"
        "Listen to 01_wirelight_current_R2.wav. The repeat file exists only for deterministic QA. "
        "No automatic aesthetic score is used.\n",
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
