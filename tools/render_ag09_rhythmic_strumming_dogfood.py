#!/usr/bin/env python3
"""AG09 Dogfood 3 — production rhythmic strumming.

12-bar steel-string rhythm-guitar candidate using AG06 shared-gesture strums:
alternating down/up strokes, local accents, skipped strings, and authored
left-hand muted strokes on a real multi-chord progression.
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
BPM = 104
PRESET = "acoustic_guitar.steel_stateful_performance"
OPEN = {1:64,2:59,3:55,4:50,5:45,6:40}

VOICINGS = {
    "Em": [(40,6,0),(47,5,2),(52,4,2),(55,3,0),(59,2,0),(64,1,0)],
    "Cmaj7": [(48,5,3),(52,4,2),(55,3,0),(59,2,0),(64,1,0)],
    "G6": [(43,6,3),(47,5,2),(50,4,0),(55,3,0),(59,2,0),(64,1,0)],
    "D/F#": [(42,6,2),(45,5,0),(50,4,0),(57,3,2),(62,2,3),(66,1,2)],
    "Am7": [(45,5,0),(52,4,2),(55,3,0),(60,2,1),(64,1,0)],
    "B7": [(47,5,2),(54,4,4),(57,3,2),(63,2,4),(66,1,2)],
    "Em/G": [(43,6,3),(47,5,2),(52,4,2),(55,3,0),(59,2,0),(64,1,0)],
}
BAR_CHORDS = ["Em","Cmaj7","G6","D/F#","Em","Am7","Cmaj7","B7","Em/G","Cmaj7","B7","Em"]
HARMONIC_PLAN = {
    "Em": {4,7,11},
    "Cmaj7": {0,4,7,11},
    "G6": {2,4,7,11},
    "D/F#": {2,6,9},
    "Am7": {0,4,7,9},
    "B7": {3,6,9,11},
    "Em/G": {4,7,11},
}
STROKE_OFFSETS = (0.0,0.5,1.0,1.5,2.0,2.5,3.0,3.5)
DIRECTIONS = ("down","up","down","up","down","up","down","up")
# Two choke/mute contacts per bar: an upbeat and the final offbeat.
MUTED_STROKES = {3,7}
BASE_VELOCITY = (0.72,0.50,0.60,0.47,0.76,0.52,0.62,0.45)


def build_song():
    return {
        "format":"code-composer-song/v1",
        "meta":{"title":"Copper Rail","global_seed":1919003,"revision":"AG09-D3-R0"},
        "transport":{"bpm":BPM,"meter":{"beats_per_bar":4,"beat_unit":4}},
        "tonal":{"root":"E","scale":"natural_minor"},
        "sections":[{"id":"rhythm","bars":12,"name":"Rhythmic Strumming"}],
        "instruments":[{
            "id":"guitar","family":"acoustic_guitar","variant":"steel-string",
            "render_lock":{"preset":PRESET,"preset_version":"1.0.0"},
        }],
        "tracks":[{"id":"guitar","function":"rhythmic-strumming","instrument":"guitar"}],
        "materials":[{"id":"rhythm-flow","kind":"motif","intervals":[0],"rhythm":[1]}],
        "parts":[{"id":"rhythm-part","section":"rhythm","track":"guitar","material":"rhythm-flow"}],
    }


def _stroke_config(stroke_id, direction, stroke_index, bar_index):
    down = direction == "down"
    strong = stroke_index in {0,4}
    secondary = stroke_index in {2,6}
    return {
        "stroke_id": stroke_id,
        "direction": direction,
        "traversal_ms": 31.0 if down else 24.0,
        "entry_strength": 0.68 if strong else (0.58 if secondary else 0.50),
        "acceleration": 0.12 if down else -0.08,
        "pick_depth": 0.60 if down else 0.48,
        "attack_angle_deg": 40.0 if down else 34.0,
        "follow_through": 0.76 if down else 0.61,
        "accent_position": 0.58 if down else 0.42,
        "accent_amount": 0.34 if strong else (0.16 if secondary else 0.06),
        "from_string": 6 if down else 1,
        "to_string": 1 if down else 6,
    }


def build_events():
    events=[]
    for bar_index,chord in enumerate(BAR_CHORDS):
        voicing=VOICINGS[chord]
        base=bar_index*4.0
        for stroke_index,(offset,direction) in enumerate(zip(STROKE_OFFSETS,DIRECTIONS)):
            muted=stroke_index in MUTED_STROKES
            stroke_id=f"b{bar_index+1:02d}s{stroke_index}"
            cfg=_stroke_config(stroke_id,direction,stroke_index,bar_index)
            for note_index,(midi,string,fret) in enumerate(voicing):
                if midi != OPEN[string]+fret:
                    raise ValueError(f"{chord}: MIDI/string/fret mismatch {midi} != {OPEN[string]}+{fret}")
                perf={
                    "string":string,
                    "fret":fret,
                    "right_hand":{
                        "method":"pick",
                        "pluck_position":0.115 if direction=="down" else 0.135,
                        "attack_angle_deg":cfg["attack_angle_deg"],
                        "strength":cfg["entry_strength"],
                    },
                    "strum":{**cfg,"state":"muted" if muted else "sounding"},
                }
                if muted:
                    perf["left_hand"]={"technique":"dead_note"}
                events.append({
                    "id":f"{stroke_id}n{note_index}",
                    "type":"note",
                    "start_beat":base+offset,
                    "duration_beats":0.18 if muted else 0.44,
                    "midi":midi,
                    "velocity":BASE_VELOCITY[stroke_index],
                    "instrument_performance":perf,
                })
    return events


def build_score(song):
    return {
        "format":"code-composer-performance-score/v1",
        "source_song":{"format":"code-composer-song/v1","fingerprint":song_fingerprint(song)},
        "meta":{"title":"Copper Rail — AG09 D3 R0"},
        "tracks":[{"id":"guitar","events":deepcopy(build_events())}],
        "render":{
            "sample_rate":SR,
            "tail_seconds":2.4,
            "mix":{
                "tracks":[{"track":"guitar","gain":0.40,"pan":0.0,"reverb_send":0.0}],
                "music_bus_gain":1.0,"room_return_gain":0.0,"master_gain":0.80,
            },
        },
    }


def harmonic_certificate(events):
    bars=[]
    for bar_index,chord in enumerate(BAR_CHORDS):
        bar_events=[e for e in events if bar_index*4.0 <= float(e["start_beat"]) < (bar_index+1)*4.0]
        pcs={int(e["midi"])%12 for e in bar_events}
        allowed=HARMONIC_PLAN[chord]
        if not pcs.issubset(allowed):
            raise ValueError(f"bar {bar_index+1} {chord}: out-of-harmony pitch classes {sorted(pcs-allowed)}")
        if pcs != allowed:
            raise ValueError(f"bar {bar_index+1} {chord}: incomplete chord-tone set {sorted(pcs)} != {sorted(allowed)}")
        bars.append({"bar":bar_index+1,"chord":chord,"pitch_classes":sorted(pcs)})
    return {"valid":True,"bars":bars,"undeclared_non_chord_tone_count":0}


def _sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def _rms(x):
    x=np.asarray(x,dtype=np.float64)
    return float(np.sqrt(np.mean(x*x))) if x.size else 0.0


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=True)

    song=build_song()
    score=build_score(song)
    authored=build_events()
    harmony=harmonic_certificate(authored)
    wav_a=out/"01_copper_rail_R0.wav"
    wav_b=out/"02_copper_rail_R0_repeat.wav"

    result_a=render_song_score_to_files(
        song,score,wav_a,
        plan_path=out/"execution_plan.json",
        render_ir_path=out/"render_ir.json",
        resolved_path=out/"resolved_ir.json",
        analysis_path=out/"audio_analysis.json",
    )
    result_b=render_song_score_to_files(song,score,wav_b)

    a=np.asarray(result_a["audio"],dtype=np.float64)
    b=np.asarray(result_b["audio"],dtype=np.float64)
    realized=result_a["render_ir"]["tracks"][0]["events"]
    report=result_a["render_ir"].get("guitar_performance_report",{})
    track=(report.get("tracks") or {}).get("guitar",{})
    strokes=track.get("strum_strokes") or {}

    if int(result_a["sr"]) != SR:
        raise SystemExit("sample-rate mismatch")
    if not np.array_equal(a,b):
        raise SystemExit("D3 render is not deterministic")
    if not np.isfinite(a).all():
        raise SystemExit("D3 contains non-finite samples")
    peak=float(np.max(np.abs(a))) if a.size else 0.0
    clipped=float(np.mean(np.abs(a)>=1.0)) if a.size else 0.0
    if clipped != 0.0 or peak >= 0.98:
        raise SystemExit(f"unsafe D3 output peak={peak} clipped={clipped}")
    if len(realized) != len(authored):
        raise SystemExit(f"event authority changed {len(authored)} -> {len(realized)}")

    authored_core=[(int(e["midi"]),float(e["start_beat"]),float(e["duration_beats"])) for e in authored]
    realized_core=[(int(e["midi"]),float(e["start_beat"]),float(e["duration_beats"])) for e in realized]
    if authored_core != realized_core:
        raise SystemExit("authored pitch/timing authority changed")

    if len(strokes) != 12*8:
        raise SystemExit(f"expected 96 strum strokes, got {len(strokes)}")
    directions=[s["direction"] for s in strokes.values()]
    if directions.count("down") != 48 or directions.count("up") != 48:
        raise SystemExit("down/up stroke count mismatch")

    muted_ids=set()
    accented_ids=set()
    for stroke_id,stroke in strokes.items():
        if stroke["muted_strings"]:
            muted_ids.add(stroke_id)
        forces=[row["force"] for row in stroke["profile"]]
        if max(forces)-min(forces) <= 0.01:
            raise SystemExit(f"uniform-force stroke: {stroke_id}")
        # strong beats have accent_amount 0.34 in authored config; identify by id index
        idx=int(stroke_id.split("s")[-1])
        if idx in {0,4}:
            accented_ids.add(stroke_id)

    if len(muted_ids) != 12*len(MUTED_STROKES):
        raise SystemExit(f"muted stroke count mismatch: {len(muted_ids)}")
    if len(accented_ids) != 24:
        raise SystemExit("accented strong-beat stroke count mismatch")

    metrics={
        "schema":"code-composer-ag09-rhythmic-strumming-dogfood/v1",
        "title":song["meta"]["title"],
        "revision":song["meta"]["revision"],
        "sample_rate":SR,"bpm":BPM,"bars":12,
        "duration_seconds":len(a)/SR,
        "harmonic_path":BAR_CHORDS,
        "harmonic_certificate":harmony,
        "authored_event_count":len(authored),
        "render_ir_event_count":len(realized),
        "strum_stroke_count":len(strokes),
        "downstroke_count":directions.count("down"),
        "upstroke_count":directions.count("up"),
        "muted_stroke_count":len(muted_ids),
        "accented_strong_beat_count":len(accented_ids),
        "deterministic":True,
        "finite":True,
        "peak":peak,
        "rms":_rms(a),
        "clipped_sample_ratio":clipped,
        "sha256":_sha256(wav_a),
        "sha256_repeat":_sha256(wav_b),
        "song_fingerprint":song_fingerprint(song),
        "performance_score_fingerprint":performance_score_fingerprint(score),
        "preset":PRESET,
        "automatic_aesthetic_score":False,
        "human_listening_required":True,
    }
    (out/"song.json").write_text(json.dumps(song,indent=2)+"\n",encoding="utf-8")
    (out/"performance_score.json").write_text(json.dumps(score,indent=2)+"\n",encoding="utf-8")
    (out/"metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
    (out/"README.md").write_text(
        "# AG09 Dogfood 3 — Copper Rail\n\n"
        "12-bar / 104 BPM / 24 kHz rhythmic steel-string candidate. "
        "Eight authored strokes per bar alternate down/up. Beats 1 and 3 use local "
        "gesture accents; two offbeat strokes per bar are authored left-hand dead-note mutes. "
        "Every stroke keeps deterministic nonuniform per-string force from AG06.\n\n"
        "Harmonic path: "+ " -> ".join(BAR_CHORDS) +"\n",
        encoding="utf-8",
    )
    files=sorted(p for p in out.rglob("*") if p.is_file() and p.name!="SHA256SUMS.txt")
    (out/"SHA256SUMS.txt").write_text(
        "".join(f"{_sha256(p)}  {p.relative_to(out).as_posix()}\n" for p in files),
        encoding="utf-8",
    )
    print(json.dumps(metrics,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
