#!/usr/bin/env python3
"""AG09 Dogfood 4 — percussive fingerstyle production candidate.

One modeled steel-string guitar performs bass, inner/treble fingerstyle notes,
body/top contact and string slap in one continuous track. Percussive actions are
AG07 instrument_action events; no drum/percussion track is substituted.
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
BPM = 88
PRESET = "acoustic_guitar.steel_stateful_performance"
OPEN = {1:64, 2:59, 3:55, 4:50, 5:45, 6:40}
OFFSETS = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5)
DURS = (1.35, 0.48, 0.72, 0.48, 1.10, 0.48, 0.72, 0.42)

VOICINGS = {
    "Em":    [(40,6,0),(47,5,2),(52,4,2),(55,3,0),(59,2,0),(64,1,0)],
    "Cmaj7": [(48,5,3),(52,4,2),(55,3,0),(59,2,0),(64,1,0)],
    "G6":    [(43,6,3),(47,5,2),(50,4,0),(55,3,0),(59,2,0),(64,1,0)],
    "D/F#":  [(42,6,2),(45,5,0),(50,4,0),(57,3,2),(62,2,3),(66,1,2)],
    "Am7":   [(45,5,0),(52,4,2),(55,3,0),(60,2,1),(64,1,0)],
    "B7":    [(47,5,2),(54,4,4),(57,3,2),(63,2,4),(66,1,2)],
    "Em/G":  [(43,6,3),(47,5,2),(52,4,2),(55,3,0),(59,2,0),(64,1,0)],
}
BAR_CHORDS = ["Em","Cmaj7","G6","D/F#","Em","Am7","Cmaj7","B7","Em/G","Cmaj7","B7","Em"]
CHORD_PCS = {
    "Em": {4,7,11}, "Cmaj7": {0,4,7,11}, "G6": {2,4,7,11},
    "D/F#": {2,6,9}, "Am7": {0,4,7,9}, "B7": {3,6,9,11}, "Em/G": {4,7,11},
}


def build_song():
    return {
        "format":"code-composer-song/v1",
        "meta":{"title":"Knucklewood","global_seed":1919005,"revision":"AG09-D4-R0"},
        "transport":{"bpm":BPM,"meter":{"beats_per_bar":4,"beat_unit":4}},
        "tonal":{"root":"E","scale":"natural_minor"},
        "sections":[{"id":"percussive","bars":12,"name":"Percussive Fingerstyle"}],
        "instruments":[{
            "id":"guitar","family":"acoustic_guitar","variant":"steel-string",
            "render_lock":{"preset":PRESET,"preset_version":"1.0.0"},
        }],
        "tracks":[{"id":"guitar","function":"percussive-fingerstyle","instrument":"guitar"}],
        "materials":[{"id":"percussive-flow","kind":"motif","intervals":[0],"rhythm":[1]}],
        "parts":[{"id":"percussive-part","section":"percussive","track":"guitar","material":"percussive-flow"}],
    }


def _note(eid, start, duration, midi, string, fret, player, velocity, gesture, seq):
    return {
        "id":eid,
        "type":"note",
        "start_beat":float(start),
        "duration_beats":float(duration),
        "midi":int(midi),
        "velocity":float(velocity),
        "instrument_performance":{
            "string":int(string),
            "fret":int(fret),
            "right_hand":{"method":"thumb" if player=="thumb" else "finger"},
            "arpeggio":{
                "gesture_id":gesture,
                "player":player,
                "voice":"bass" if player=="thumb" else "treble",
                "sequence_index":int(seq),
            },
        },
    }


def _action(eid, action, start, *, strength, location=None):
    params={"strength":float(strength)}
    if location is not None:
        params["location"]=location
    return {
        "id":eid,
        "type":"instrument_action",
        "start_beat":float(start),
        "duration_beats":0.08,
        "action":action,
        "parameters":params,
    }


def build_events():
    events=[]
    for bar_index,chord in enumerate(BAR_CHORDS):
        v=VOICINGS[chord]
        # physical fingerstyle pattern: bass, high, inner, upper-middle, second bass, high, inner, upper-middle
        picks=(v[0],v[-1],v[2],v[-2],v[1],v[-1],v[2],v[-2])
        players=("thumb","ring","index","middle","thumb","ring","index","middle")
        velocities=(.66,.60,.48,.56,.60,.62,.47,.54)
        base=bar_index*4.0
        gesture=f"pf-bar-{bar_index+1:02d}"
        for seq,((midi,string,fret),offset,dur,player,vel) in enumerate(zip(picks,OFFSETS,DURS,players,velocities)):
            if midi != OPEN[string]+fret:
                raise ValueError(f"bar {bar_index+1}: string/fret mismatch")
            events.append(_note(
                f"b{bar_index+1:02d}n{seq}", base+offset, dur, midi, string, fret,
                player, vel, gesture, seq,
            ))

        # One top slap every bar, plus one alternating body/string contact. These are
        # deliberately simultaneous with authored notes to exercise note+action coexistence.
        events.append(_action(
            f"b{bar_index+1:02d}-top", "top_slap", base+1.5,
            strength=.48 + .02*(bar_index%3), location="soundboard",
        ))
        if bar_index % 2 == 0:
            events.append(_action(
                f"b{bar_index+1:02d}-body", "body_tap", base+3.0,
                strength=.42 + .02*(bar_index%4), location="lower_bout",
            ))
        else:
            events.append(_action(
                f"b{bar_index+1:02d}-strings", "string_slap", base+3.5,
                strength=.46 + .02*(bar_index%4),
            ))
    return sorted(events, key=lambda e:(float(e["start_beat"]), 0 if e["type"]=="note" else 1, e["id"]))


def build_score(song):
    return {
        "format":"code-composer-performance-score/v1",
        "source_song":{"format":"code-composer-song/v1","fingerprint":song_fingerprint(song)},
        "meta":{"title":"Knucklewood — AG09 D4 R0"},
        "tracks":[{"id":"guitar","events":deepcopy(build_events())}],
        "render":{
            "sample_rate":SR,
            "tail_seconds":2.5,
            "mix":{
                "tracks":[{"track":"guitar","gain":0.46,"pan":0.0,"reverb_send":0.0}],
                "music_bus_gain":1.0,"room_return_gain":0.0,"master_gain":0.80,
            },
        },
    }


def harmonic_certificate(events):
    rows=[]
    notes=[e for e in events if e["type"]=="note"]
    for bar_index,chord in enumerate(BAR_CHORDS):
        bar=[e for e in notes if bar_index*4.0 <= float(e["start_beat"]) < (bar_index+1)*4.0]
        pcs={int(e["midi"])%12 for e in bar}
        if not pcs.issubset(CHORD_PCS[chord]):
            raise ValueError(f"bar {bar_index+1} {chord}: non-chord pitch classes {sorted(pcs-CHORD_PCS[chord])}")
        rows.append({"bar":bar_index+1,"chord":chord,"pitch_classes":sorted(pcs)})
    return {"valid":True,"bars":rows,"undeclared_non_chord_tone_count":0}


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
    wav_a=out/"01_knucklewood_R0.wav"
    wav_b=out/"02_knucklewood_R0_repeat.wav"

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
    if not np.array_equal(a,b):
        raise SystemExit("D4 render is not deterministic")
    if not np.isfinite(a).all():
        raise SystemExit("D4 contains non-finite samples")
    peak=float(np.max(np.abs(a))) if a.size else 0.0
    clipped=float(np.mean(np.abs(a)>=1.0)) if a.size else 0.0
    if peak>=0.98 or clipped!=0.0:
        raise SystemExit(f"unsafe output peak={peak} clipped={clipped}")

    realized=result_a["render_ir"]["tracks"][0]["events"]
    if len(realized)!=len(authored):
        raise SystemExit(f"event authority changed {len(authored)}->{len(realized)}")

    authored_notes=[e for e in authored if e["type"]=="note"]
    realized_notes=[e for e in realized if "midi" in e]
    authored_actions=[e for e in authored if e["type"]=="instrument_action"]
    realized_actions=[e for e in realized if e.get("event_type")=="instrument_action"]
    if len(realized_notes)!=len(authored_notes) or len(realized_actions)!=len(authored_actions):
        raise SystemExit("note/action authority split changed")

    note_core=[(int(e["midi"]),float(e["start_beat"]),float(e["duration_beats"])) for e in authored_notes]
    realized_core=[(int(e["midi"]),float(e["start_beat"]),float(e["duration_beats"])) for e in realized_notes]
    if note_core!=realized_core:
        raise SystemExit("pitched note authority changed")

    action_counts={name:0 for name in ("top_slap","body_tap","string_slap")}
    for e in realized_actions:
        action=e["action"]
        if action in action_counts:
            action_counts[action]+=1
    if action_counts!={"top_slap":12,"body_tap":6,"string_slap":6}:
        raise SystemExit(f"unexpected action counts {action_counts}")

    note_onsets={round(float(e["start_beat"]),9) for e in authored_notes}
    simultaneous=sum(round(float(e["start_beat"]),9) in note_onsets for e in authored_actions)
    if simultaneous!=24:
        raise SystemExit(f"expected 24 simultaneous note/action onsets, got {simultaneous}")

    report=result_a["render_ir"].get("guitar_performance_report",{})
    track=(report.get("tracks") or {}).get("guitar",{})
    gestures=len(track.get("arpeggio_gestures") or {})
    if gestures!=12:
        raise SystemExit(f"expected 12 fingerstyle gestures, got {gestures}")

    metrics={
        "schema":"code-composer-ag09-percussive-fingerstyle-dogfood/v1",
        "title":song["meta"]["title"],
        "revision":song["meta"]["revision"],
        "sample_rate":SR,"bpm":BPM,"bars":12,
        "duration_seconds":len(a)/SR,
        "harmonic_path":BAR_CHORDS,
        "harmonic_certificate":harmony,
        "authored_event_count":len(authored),
        "render_ir_event_count":len(realized),
        "pitched_note_count":len(authored_notes),
        "instrument_action_count":len(authored_actions),
        "action_counts":action_counts,
        "simultaneous_note_action_onsets":simultaneous,
        "arpeggio_gesture_count":gestures,
        "deterministic":True,"finite":True,
        "peak":peak,"rms":_rms(a),"clipped_sample_ratio":clipped,
        "sha256":_sha256(wav_a),"sha256_repeat":_sha256(wav_b),
        "song_fingerprint":song_fingerprint(song),
        "performance_score_fingerprint":performance_score_fingerprint(score),
        "preset":PRESET,
        "no_drum_track_substitution":True,
        "automatic_aesthetic_score":False,
        "human_listening_required":True,
    }
    (out/"song.json").write_text(json.dumps(song,indent=2)+"\n",encoding="utf-8")
    (out/"performance_score.json").write_text(json.dumps(score,indent=2)+"\n",encoding="utf-8")
    (out/"metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
    (out/"README.md").write_text(
        "# AG09 Dogfood 4 — Knucklewood\n\n"
        "12-bar / 88 BPM / 24 kHz percussive fingerstyle candidate. One modeled acoustic-guitar track contains pitched fingerstyle notes plus AG07 top_slap, body_tap and string_slap actions. No drum or independent percussion track is used.\n",
        encoding="utf-8",
    )
    files=sorted(p for p in out.rglob("*") if p.is_file() and p.name!="SHA256SUMS.txt")
    (out/"SHA256SUMS.txt").write_text(
        "".join(f"{_sha256(p)}  {p.relative_to(out).as_posix()}\n" for p in files),encoding="utf-8"
    )
    print(json.dumps(metrics,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
