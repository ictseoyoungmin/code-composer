#!/usr/bin/env python3
"""AG09 D3 public-domain reference reproduction: Oh! Susanna.

Purpose:
Evaluate the acoustic-guitar system against a widely recognizable pre-1900 song
rather than only project-authored dogfood. The melody/basic harmony are
public-domain material; this guitar arrangement is independently authored for
Code Composer and does not reproduce a modern recording or arrangement.
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
BPM = 112
PRESET = "acoustic_guitar.steel_stateful_performance"
OPEN = {1:64,2:59,3:55,4:50,5:45,6:40}

# Independent acoustic-guitar voicings in C major.
VOICINGS = {
    "C":  [(48,5,3),(52,4,2),(55,3,0),(60,2,1),(64,1,0)],
    "F":  [(41,6,1),(48,5,3),(53,4,3),(57,3,2),(60,2,1),(65,1,1)],
    "G7": [(43,6,3),(47,5,2),(50,4,0),(55,3,0),(59,2,0),(65,1,1)],
}

# 16 bars in 2/4. Bars 7 and 15 change C -> G7 halfway through.
BAR_HARMONY = [
    (("C",0.0,2.0),),
    (("C",0.0,2.0),),
    (("C",0.0,2.0),),
    (("G7",0.0,2.0),),
    (("C",0.0,2.0),),
    (("C",0.0,2.0),),
    (("C",0.0,1.0),("G7",1.0,2.0)),
    (("C",0.0,2.0),),
    (("F",0.0,2.0),),
    (("F",0.0,2.0),),
    (("C",0.0,2.0),),
    (("G7",0.0,2.0),),
    (("C",0.0,2.0),),
    (("C",0.0,2.0),),
    (("C",0.0,1.0),("G7",1.0,2.0)),
    (("C",0.0,2.0),),
]

# Public-domain melody contour/rhythm in C, one bar = two quarter-note beats.
# (MIDI, start_in_bar_beats, duration_beats)
MELODY = [
    [(64,0.0,.5),(67,.5,.5),(67,1.0,.75),(69,1.75,.25)],
    [(67,0.0,.5),(64,.5,.5),(60,1.0,.75),(62,1.75,.25)],
    [(64,0.0,.5),(64,.5,.5),(62,1.0,.5),(60,1.5,.5)],
    [(62,0.0,1.5),(60,1.5,.25),(62,1.75,.25)],
    [(64,0.0,.5),(67,.5,.5),(67,1.0,.75),(69,1.75,.25)],
    [(67,0.0,.5),(64,.5,.5),(60,1.0,.75),(62,1.75,.25)],
    [(64,0.0,.5),(64,.5,.5),(62,1.0,.5),(62,1.5,.5)],
    [(60,0.0,1.5)],
    [(65,0.0,1.0),(65,1.0,1.0)],
    [(69,0.0,.5),(69,.5,1.0),(69,1.5,.5)],
    [(67,0.0,.5),(67,.5,.5),(64,1.0,.5),(60,1.5,.5)],
    [(62,0.0,1.5),(60,1.5,.25),(62,1.75,.25)],
    [(64,0.0,.5),(67,.5,.5),(67,1.0,.75),(69,1.75,.25)],
    [(67,0.0,.5),(64,.5,.5),(60,1.0,.75),(62,1.75,.25)],
    [(64,0.0,.5),(64,.5,.5),(62,1.0,.5),(62,1.5,.5)],
    [(60,0.0,1.5)],
]

# Play melody one octave below many vocal sheets so it sits naturally on guitar.
# MIDI 60..69 can be covered compactly on strings 1-2.
MELODY_POS = {
    60:(2,1),   # C4
    62:(2,3),   # D4
    64:(1,0),   # E4
    65:(1,1),   # F4
    67:(1,3),   # G4
    69:(1,5),   # A4
}

PUBLIC_DOMAIN_PROVENANCE = {
    "work": "Oh! Susanna",
    "composer": "Stephen Collins Foster",
    "year": 1848,
    "source_note": "public-domain melody/basic harmony; independent Code Composer acoustic-guitar arrangement",
    "loc_reference": "https://www.loc.gov/item/2023800745/",
    "public_domain_scan": "https://commons.wikimedia.org/wiki/File:Oh_Susanna_Original_1848_Sheet_Music_(IA_OhSusannaOriginal1848SheetMusic).pdf",
}


def build_song():
    return {
        "format":"code-composer-song/v1",
        "meta":{
            "title":"Oh! Susanna — public-domain acoustic reference",
            "global_seed":1919004,
            "revision":"AG09-D3-PD-R0",
        },
        "transport":{"bpm":BPM,"meter":{"beats_per_bar":2,"beat_unit":4}},
        "tonal":{"root":"C","scale":"major"},
        "sections":[{"id":"song","bars":16,"name":"Oh! Susanna"}],
        "instruments":[
            {"id":"rhythm_guitar","family":"acoustic_guitar","variant":"steel-string",
             "render_lock":{"preset":PRESET,"preset_version":"1.0.0"}},
            {"id":"melody_guitar","family":"acoustic_guitar","variant":"steel-string",
             "render_lock":{"preset":PRESET,"preset_version":"1.0.0"}},
        ],
        "tracks":[
            {"id":"rhythm","function":"rhythmic-strumming","instrument":"rhythm_guitar"},
            {"id":"melody","function":"picked-melody","instrument":"melody_guitar"},
        ],
        "materials":[{"id":"pd-song","kind":"motif","intervals":[0],"rhythm":[1]}],
        "parts":[
            {"id":"rhythm-part","section":"song","track":"rhythm","material":"pd-song"},
            {"id":"melody-part","section":"song","track":"melody","material":"pd-song"},
        ],
    }


def chord_at(bar_index, offset):
    for chord,start,end in BAR_HARMONY[bar_index]:
        if start <= offset < end:
            return chord
    raise ValueError(f"no harmony for bar {bar_index+1} beat {offset}")


def strum_config(stroke_id, direction, strong, expressive):
    down=direction=="down"
    return {
        "stroke_id":stroke_id,
        "direction":direction,
        "traversal_ms":30.0 if down else 23.0,
        "entry_strength":0.66 if strong else 0.50,
        "acceleration":0.10 if down else -0.06,
        "pick_depth":0.58 if down else 0.46,
        "attack_angle_deg":40.0 if down else 34.0,
        "follow_through":0.74 if down else 0.60,
        "accent_position":0.58 if down else 0.42,
        "accent_amount":(0.30 if strong else 0.08) if expressive else (0.12 if strong else 0.03),
        "from_string":6 if down else 1,
        "to_string":1 if down else 6,
    }


def build_rhythm_events(*, expressive):
    events=[]
    for bar in range(16):
        base=bar*2.0
        for stroke_idx,offset in enumerate((0.0,.5,1.0,1.5)):
            direction="down" if stroke_idx%2==0 else "up"
            strong=stroke_idx in {0,2}
            chord=chord_at(bar,offset)
            # Expressive comparison keeps only phrase-ending offbeat chokes.
            muted=bool(expressive and stroke_idx==3 and bar in {3,7,11,15})
            stroke_id=f"{'x' if expressive else 'c'}-b{bar+1:02d}s{stroke_idx}"
            cfg=strum_config(stroke_id,direction,strong,expressive)
            for ni,(midi,string,fret) in enumerate(VOICINGS[chord]):
                perf={
                    "string":string,"fret":fret,
                    "right_hand":{
                        "method":"pick",
                        "pluck_position":0.12 if direction=="down" else 0.135,
                        "attack_angle_deg":cfg["attack_angle_deg"],
                        "strength":cfg["entry_strength"],
                    },
                    "strum":{**cfg,"state":"muted" if muted else "sounding"},
                }
                if muted:
                    perf["left_hand"]={"technique":"dead_note"}
                events.append({
                    "id":f"{stroke_id}n{ni}",
                    "type":"note",
                    "start_beat":base+offset,
                    "duration_beats":0.18 if muted else 0.42,
                    "midi":midi,
                    "velocity":0.69 if strong else 0.50,
                    "instrument_performance":perf,
                })
    return events


def build_melody_events():
    events=[]
    counter=0
    for bar,notes in enumerate(MELODY):
        base=bar*2.0
        for midi,offset,dur in notes:
            string,fret=MELODY_POS[midi]
            events.append({
                "id":f"mel-{counter:03d}",
                "type":"note",
                "start_beat":base+offset,
                "duration_beats":dur*0.92,
                "midi":midi,
                "velocity":0.68 if offset in {0.0,1.0} else 0.61,
                "instrument_performance":{
                    "string":string,
                    "fret":fret,
                    "right_hand":{
                        "method":"pick",
                        "pluck_position":0.16,
                        "attack_angle_deg":36.0,
                        "strength":0.58,
                    },
                },
            })
            counter+=1
    return events


def build_score(song, *, expressive):
    return {
        "format":"code-composer-performance-score/v1",
        "source_song":{"format":"code-composer-song/v1","fingerprint":song_fingerprint(song)},
        "meta":{"title":f"Oh! Susanna — {'D3 expressive' if expressive else 'clean reference'}"},
        "tracks":[
            {"id":"rhythm","events":deepcopy(build_rhythm_events(expressive=expressive))},
            {"id":"melody","events":deepcopy(build_melody_events())},
        ],
        "render":{
            "sample_rate":SR,
            "tail_seconds":2.4,
            "mix":{
                "tracks":[
                    {"track":"rhythm","gain":0.30,"pan":-0.12,"reverb_send":0.0},
                    {"track":"melody","gain":0.34,"pan":0.10,"reverb_send":0.0},
                ],
                "music_bus_gain":1.0,"room_return_gain":0.0,"master_gain":0.78,
            },
        },
    }


def harmonic_certificate():
    bars=[]
    chord_pcs={"C":{0,4,7},"F":{0,5,9},"G7":{2,5,7,11}}
    for bar,harmonies in enumerate(BAR_HARMONY):
        for chord,start,end in harmonies:
            pcs={midi%12 for midi,_,_ in VOICINGS[chord]}
            if pcs != chord_pcs[chord]:
                raise ValueError(f"{chord} voicing pitch classes {pcs} != {chord_pcs[chord]}")
        for midi,offset,_dur in MELODY[bar]:
            chord=chord_at(bar,offset)
            # Public-domain melody contains simple non-chord passing/neighbor tones.
            # They are allowed here but explicitly recorded rather than treated as
            # chord-membership failures.
            if midi%12 not in chord_pcs[chord]:
                bars.append({
                    "bar":bar+1,"beat":offset,"midi":midi,"chord":chord,
                    "kind":"public_domain_melody_non_chord_tone",
                })
    return {
        "valid":True,
        "voicing_chord_tones_valid":True,
        "declared_melody_non_chord_tones":bars,
        "undeclared_non_chord_tone_count":0,
    }


def _sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def _rms(x):
    x=np.asarray(x,dtype=np.float64)
    return float(np.sqrt(np.mean(x*x))) if x.size else 0.0


def render_variant(song,out,name,expressive,*,repeat=False):
    score=build_score(song,expressive=expressive)
    wav=out/f"{name}.wav"
    result=render_song_score_to_files(
        song,score,wav,
        plan_path=out/f"{name}_execution_plan.json",
        render_ir_path=out/f"{name}_render_ir.json",
    )
    audio=np.asarray(result["audio"],dtype=np.float64)
    if not np.isfinite(audio).all():
        raise SystemExit(f"{name}: non-finite output")
    peak=float(np.max(np.abs(audio))) if audio.size else 0.0
    clipped=float(np.mean(np.abs(audio)>=1.0)) if audio.size else 0.0
    if clipped!=0.0 or peak>=0.98:
        raise SystemExit(f"{name}: unsafe peak/clipping {peak} {clipped}")

    deterministic=True
    repeat_sha=None
    if repeat:
        repeat_path=out/f"{name}_repeat.wav"
        again=render_song_score_to_files(song,score,repeat_path)
        b=np.asarray(again["audio"],dtype=np.float64)
        deterministic=bool(np.array_equal(audio,b))
        if not deterministic:
            raise SystemExit(f"{name}: nondeterministic repeat")
        repeat_sha=_sha256(repeat_path)

    authored_count=sum(len(t["events"]) for t in score["tracks"])
    realized_count=sum(len(t["events"]) for t in result["render_ir"]["tracks"])
    if realized_count!=authored_count:
        raise SystemExit(f"{name}: event authority {authored_count}->{realized_count}")

    return {
        "name":name,
        "score_fingerprint":performance_score_fingerprint(score),
        "duration_seconds":len(audio)/SR,
        "authored_event_count":authored_count,
        "render_ir_event_count":realized_count,
        "peak":peak,
        "rms":_rms(audio),
        "clipped_sample_ratio":clipped,
        "deterministic":deterministic,
        "sha256":_sha256(wav),
        "sha256_repeat":repeat_sha,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=True)

    song=build_song()
    harmony=harmonic_certificate()
    clean=render_variant(song,out,"01_oh_susanna_clean_reference",False,repeat=False)
    expressive=render_variant(song,out,"02_oh_susanna_d3_expressive",True,repeat=True)

    metrics={
        "schema":"code-composer-ag09-d3-public-domain-reference/v1",
        "title":"Oh! Susanna",
        "revision":"AG09-D3-PD-R0",
        "public_domain_provenance":PUBLIC_DOMAIN_PROVENANCE,
        "sample_rate":SR,"bpm":BPM,"meter":"2/4","bars":16,
        "melody_event_count":len(build_melody_events()),
        "clean_rhythm_event_count":len(build_rhythm_events(expressive=False)),
        "expressive_rhythm_event_count":len(build_rhythm_events(expressive=True)),
        "harmonic_certificate":harmony,
        "clean_reference":clean,
        "d3_expressive":expressive,
        "automatic_aesthetic_score":False,
        "human_listening_required":True,
    }
    (out/"song.json").write_text(json.dumps(song,indent=2)+"\n",encoding="utf-8")
    (out/"metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
    (out/"README.md").write_text(
        "# AG09 D3 public-domain reference — Oh! Susanna\n\n"
        "This is an independently authored Code Composer acoustic-guitar arrangement "
        "of the public-domain 1848 song by Stephen Collins Foster. It uses the "
        "public-domain melody/basic harmony only; no modern recording or arrangement "
        "is copied.\n\n"
        "01 = clean strumming + melody reference.\n"
        "02 = same melody/harmony with D3 stronger local accents and phrase-ending "
        "dead-note chokes. Compare musical identity and guitar realism, not loudness.\n",
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
