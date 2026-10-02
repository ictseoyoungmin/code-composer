#!/usr/bin/env python3
"""AG09 Dogfood 5 — integrated acoustic-guitar performance.

One persistent steel-string guitar transitions in-performance through fingerstyle,
picked arpeggio, rhythmic strumming/mute, and percussive fingerstyle. Transition
bars deliberately switch technique inside the same bar; this is not an audio
splice of earlier dogfoods.
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
BPM = 96
PRESET = "acoustic_guitar.steel_stateful_performance"
OPEN = {1:64, 2:59, 3:55, 4:50, 5:45, 6:40}
VOICINGS = {
    "Em":    [(40,6,0),(47,5,2),(52,4,2),(55,3,0),(59,2,0),(64,1,0)],
    "Cmaj7": [(48,5,3),(52,4,2),(55,3,0),(59,2,0),(64,1,0)],
    "G6":    [(43,6,3),(47,5,2),(50,4,0),(55,3,0),(59,2,0),(64,1,0)],
    "D/F#":  [(42,6,2),(45,5,0),(50,4,0),(57,3,2),(62,2,3),(66,1,2)],
    "Am7":   [(45,5,0),(52,4,2),(55,3,0),(60,2,1),(64,1,0)],
    "B7":    [(47,5,2),(54,4,4),(57,3,2),(63,2,4),(66,1,2)],
    "Em/G":  [(43,6,3),(47,5,2),(52,4,2),(55,3,0),(59,2,0),(64,1,0)],
}
CHORD_PCS = {
    "Em": {4,7,11}, "Cmaj7": {0,4,7,11}, "G6": {2,4,7,11},
    "D/F#": {2,6,9}, "Am7": {0,4,7,9}, "B7": {3,6,9,11}, "Em/G": {4,7,11},
}
BAR_CHORDS = [
    "Em","Cmaj7","G6","D/F#",
    "Em","Cmaj7","Am7","B7",
    "Em","G6","Cmaj7","B7",
    "Em/G","Cmaj7","B7","Em",
]
HALF = (0.0,0.5,1.0,1.5)
FULL = (0.0,0.5,1.0,1.5,2.0,2.5,3.0,3.5)


def build_song():
    return {
        "format":"code-composer-song/v1",
        "meta":{"title":"One Wood, Four Hands","global_seed":1919006,"revision":"AG09-D5-R0"},
        "transport":{"bpm":BPM,"meter":{"beats_per_bar":4,"beat_unit":4}},
        "tonal":{"root":"E","scale":"natural_minor"},
        "sections":[{"id":"integration","bars":16,"name":"Integrated Acoustic Guitar"}],
        "instruments":[{
            "id":"guitar","family":"acoustic_guitar","variant":"steel-string",
            "render_lock":{"preset":PRESET,"preset_version":"1.0.0"},
        }],
        "tracks":[{"id":"guitar","function":"integrated-acoustic-performance","instrument":"guitar"}],
        "materials":[{"id":"integrated-flow","kind":"motif","intervals":[0],"rhythm":[1]}],
        "parts":[{"id":"integration-part","section":"integration","track":"guitar","material":"integrated-flow"}],
    }


def _voice(string):
    if string >= 5:
        return "bass"
    if string >= 3:
        return "inner"
    return "treble"


def _player(string):
    if string >= 5:
        return "thumb"
    if string in (3,4):
        return "index"
    if string == 2:
        return "middle"
    return "ring"


def _single_note(eid, start, duration, pitch, *, method, gesture, seq, velocity):
    midi,string,fret = pitch
    if midi != OPEN[string] + fret:
        raise ValueError(f"{eid}: midi/string/fret mismatch")
    voice = _voice(string)
    player = "pick" if method == "pick" else _player(string)
    rh = {"method": method}
    if method == "pick":
        rh.update({
            "pluck_position": 0.12 + 0.006*(seq%4),
            "attack_angle_deg": 36.0 + 3.0*(seq%3),
            "strength": 0.58 + 0.04*(seq%2),
        })
    return {
        "id":eid,"type":"note","start_beat":float(start),"duration_beats":float(duration),
        "midi":int(midi),"velocity":float(velocity),
        "instrument_performance":{
            "string":int(string),"fret":int(fret),"right_hand":rh,
            "arpeggio":{
                "gesture_id":gesture,"player":player,"voice":voice,"sequence_index":int(seq),
            },
        },
    }


def _finger_pattern(voicing):
    return (voicing[0],voicing[-1],voicing[2],voicing[-2],voicing[1],voicing[-1],voicing[2],voicing[-2])


def _arpeggio_events(bar_index, chord, *, method, offsets=FULL, start_seq=0, id_tag="arp"):
    base = bar_index * 4.0
    voicing = VOICINGS[chord]
    pattern = _finger_pattern(voicing)
    if len(offsets) == 4:
        pattern = pattern[:4] if offsets[0] < 2.0 else pattern[4:]
    out=[]
    for local,(offset,pitch) in enumerate(zip(offsets,pattern)):
        seq=start_seq+local
        vel=(0.67,0.56,0.49,0.54,0.61,0.58,0.48,0.53)[seq%8]
        dur=(1.28,0.78,0.72,0.66,1.05,0.72,0.68,0.40)[seq%8]
        out.append(_single_note(
            f"b{bar_index+1:02d}-{id_tag}-{seq}",base+offset,dur,pitch,
            method=method,gesture=f"b{bar_index+1:02d}-{id_tag}",seq=seq,velocity=vel,
        ))
    return out


def _stroke_cfg(stroke_id,direction,index):
    down=direction=="down"
    strong=index in {0,4}
    secondary=index in {2,6}
    return {
        "stroke_id":stroke_id,"direction":direction,
        "traversal_ms":31.0 if down else 24.0,
        "entry_strength":0.68 if strong else (0.58 if secondary else 0.50),
        "acceleration":0.12 if down else -0.08,
        "pick_depth":0.60 if down else 0.48,
        "attack_angle_deg":40.0 if down else 34.0,
        "follow_through":0.76 if down else 0.61,
        "accent_position":0.58 if down else 0.42,
        "accent_amount":0.34 if strong else (0.16 if secondary else 0.06),
        "from_string":6 if down else 1,"to_string":1 if down else 6,
    }


def _strum_events(bar_index,chord,indices):
    base=bar_index*4.0
    voicing=VOICINGS[chord]
    out=[]
    for idx in indices:
        direction="down" if idx%2==0 else "up"
        offset=0.5*idx
        muted=idx in {3,7}
        sid=f"b{bar_index+1:02d}-strum-{idx}"
        cfg=_stroke_cfg(sid,direction,idx)
        for n,(midi,string,fret) in enumerate(voicing):
            perf={
                "string":string,"fret":fret,
                "right_hand":{
                    "method":"pick","pluck_position":0.115 if direction=="down" else 0.135,
                    "attack_angle_deg":cfg["attack_angle_deg"],"strength":cfg["entry_strength"],
                },
                "strum":{**cfg,"state":"muted" if muted else "sounding"},
            }
            if muted:
                perf["left_hand"]={"technique":"dead_note"}
            out.append({
                "id":f"{sid}n{n}","type":"note","start_beat":base+offset,
                "duration_beats":0.18 if muted else 0.42,
                "midi":midi,"velocity":0.72 if idx in {0,4} else 0.52,
                "instrument_performance":perf,
            })
    return out


def _action(eid,action,start,strength,location=None):
    p={"strength":float(strength)}
    if location is not None:
        p["location"]=location
    return {"id":eid,"type":"instrument_action","start_beat":float(start),"duration_beats":0.08,"action":action,"parameters":p}


def _percussive_events(bar_index,chord,offsets=FULL):
    # Pitched contacts remain ordinary fingerstyle; actions share selected note onsets.
    notes=_arpeggio_events(bar_index,chord,method="finger",offsets=offsets,id_tag="perc")
    base=bar_index*4.0
    out=list(notes)
    action_offsets=[]
    if 1.5 in offsets:
        action_offsets.append((1.5,"top_slap"))
    if 3.0 in offsets:
        action_offsets.append((3.0,"body_tap"))
    if 3.5 in offsets:
        action_offsets.append((3.5,"string_slap"))
    if 2.5 in offsets and len(offsets)==4:
        action_offsets.append((2.5,"top_slap"))
    for i,(off,action) in enumerate(action_offsets):
        loc="soundboard" if action=="top_slap" else ("lower_bout" if action=="body_tap" else None)
        out.append(_action(f"b{bar_index+1:02d}-action-{i}-{action}",action,base+off,0.46+0.03*i,loc))
    return out


def build_events():
    events=[]
    technique_bars={}
    for b,chord in enumerate(BAR_CHORDS):
        bar=b+1
        if bar <= 3:
            technique_bars[bar]="fingerstyle"
            events += _arpeggio_events(b,chord,method="finger",id_tag="finger")
        elif bar == 4:
            technique_bars[bar]="fingerstyle->picked"
            events += _arpeggio_events(b,chord,method="finger",offsets=HALF,start_seq=0,id_tag="finger")
            events += _arpeggio_events(b,chord,method="pick",offsets=(2.0,2.5,3.0,3.5),start_seq=4,id_tag="pick")
        elif bar <= 7:
            technique_bars[bar]="picked-arpeggio"
            events += _arpeggio_events(b,chord,method="pick",id_tag="pick")
        elif bar == 8:
            technique_bars[bar]="picked->strum"
            events += _arpeggio_events(b,chord,method="pick",offsets=HALF,start_seq=0,id_tag="pick")
            events += _strum_events(b,chord,indices=(4,5,6,7))
        elif bar <= 11:
            technique_bars[bar]="strumming"
            events += _strum_events(b,chord,indices=tuple(range(8)))
        elif bar == 12:
            technique_bars[bar]="strum->percussive"
            events += _strum_events(b,chord,indices=(0,1,2,3))
            events += _percussive_events(b,chord,offsets=(2.0,2.5,3.0,3.5))
        else:
            technique_bars[bar]="percussive-fingerstyle"
            events += _percussive_events(b,chord)
    return sorted(events,key=lambda e:(float(e["start_beat"]),0 if e["type"]=="note" else 1,e["id"])), technique_bars


def harmonic_certificate(events):
    notes=[e for e in events if e["type"]=="note"]
    rows=[]
    for b,chord in enumerate(BAR_CHORDS):
        bar=[e for e in notes if b*4.0 <= float(e["start_beat"]) < (b+1)*4.0]
        pcs={int(e["midi"])%12 for e in bar}
        if not pcs.issubset(CHORD_PCS[chord]):
            raise ValueError(f"bar {b+1} {chord}: non-chord pitch classes {sorted(pcs-CHORD_PCS[chord])}")
        rows.append({"bar":b+1,"chord":chord,"pitch_classes":sorted(pcs)})
    return {"valid":True,"bars":rows,"undeclared_non_chord_tone_count":0}


def build_score(song):
    events,_=build_events()
    return {
        "format":"code-composer-performance-score/v1",
        "source_song":{"format":"code-composer-song/v1","fingerprint":song_fingerprint(song)},
        "meta":{"title":"One Wood, Four Hands — AG09 D5 R0"},
        "tracks":[{"id":"guitar","events":deepcopy(events)}],
        "render":{
            "sample_rate":SR,"tail_seconds":2.6,
            "mix":{"tracks":[{"track":"guitar","gain":0.42,"pan":0.0,"reverb_send":0.0}],
                   "music_bus_gain":1.0,"room_return_gain":0.0,"master_gain":0.80},
        },
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


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    song=build_song(); score=build_score(song); authored,technique_bars=build_events()
    harmony=harmonic_certificate(authored)
    wav_a=out/"01_one_wood_four_hands_R0.wav"
    wav_b=out/"02_one_wood_four_hands_R0_repeat.wav"
    result_a=render_song_score_to_files(song,score,wav_a,plan_path=out/"execution_plan.json",render_ir_path=out/"render_ir.json",resolved_path=out/"resolved_ir.json",analysis_path=out/"audio_analysis.json")
    result_b=render_song_score_to_files(song,score,wav_b)
    a=np.asarray(result_a["audio"],dtype=np.float64); b=np.asarray(result_b["audio"],dtype=np.float64)
    realized=result_a["render_ir"]["tracks"][0]["events"]
    if int(result_a["sr"])!=SR: raise SystemExit("sample-rate mismatch")
    if not np.array_equal(a,b): raise SystemExit("D5 render is not deterministic")
    if not np.isfinite(a).all(): raise SystemExit("D5 contains non-finite samples")
    peak=float(np.max(np.abs(a))) if a.size else 0.0
    clipped=float(np.mean(np.abs(a)>=1.0)) if a.size else 0.0
    if peak>=0.98 or clipped!=0.0: raise SystemExit(f"unsafe D5 output peak={peak} clipped={clipped}")
    if len(realized)!=len(authored): raise SystemExit(f"event authority changed {len(authored)}->{len(realized)}")

    authored_notes=[e for e in authored if e["type"]=="note"]
    realized_notes=[e for e in realized if "midi" in e]
    authored_actions=[e for e in authored if e["type"]=="instrument_action"]
    realized_actions=[e for e in realized if e.get("event_type")=="instrument_action"]
    if len(authored_notes)!=len(realized_notes) or len(authored_actions)!=len(realized_actions):
        raise SystemExit("note/action authority split changed")
    acore=[(int(e["midi"]),float(e["start_beat"]),float(e["duration_beats"])) for e in authored_notes]
    rcore=[(int(e["midi"]),float(e["start_beat"]),float(e["duration_beats"])) for e in realized_notes]
    if acore!=rcore: raise SystemExit("pitched note authority changed")

    report=result_a["render_ir"].get("guitar_performance_report",{})
    track=(report.get("tracks") or {}).get("guitar",{})
    strum_strokes=track.get("strum_strokes") or {}
    arpeggio_gestures=track.get("arpeggio_gestures") or {}
    action_counts={"top_slap":0,"body_tap":0,"string_slap":0}
    for e in realized_actions:
        if e["action"] in action_counts: action_counts[e["action"]]+=1
    transition_bars={4:"fingerstyle->picked",8:"picked->strum",12:"strum->percussive"}
    for k,v in transition_bars.items():
        if technique_bars.get(k)!=v: raise SystemExit(f"transition bar {k} contract lost")
    note_onsets={round(float(e["start_beat"]),9) for e in authored_notes}
    simultaneous=sum(round(float(e["start_beat"]),9) in note_onsets for e in authored_actions)

    metrics={
        "schema":"code-composer-ag09-integration-dogfood/v1",
        "title":song["meta"]["title"],"revision":song["meta"]["revision"],
        "sample_rate":SR,"bpm":BPM,"bars":16,"duration_seconds":len(a)/SR,
        "harmonic_path":BAR_CHORDS,"harmonic_certificate":harmony,
        "technique_bars":technique_bars,"transition_bars":transition_bars,
        "authored_event_count":len(authored),"render_ir_event_count":len(realized),
        "pitched_note_count":len(authored_notes),"instrument_action_count":len(authored_actions),
        "action_counts":action_counts,"simultaneous_note_action_onsets":simultaneous,
        "arpeggio_gesture_count":len(arpeggio_gestures),"strum_stroke_count":len(strum_strokes),
        "single_persistent_track":True,"preset":PRESET,"no_audio_splice":True,"no_drum_track_substitution":True,
        "deterministic":True,"finite":True,"peak":peak,"rms":_rms(a),"clipped_sample_ratio":clipped,
        "sha256":_sha256(wav_a),"sha256_repeat":_sha256(wav_b),
        "song_fingerprint":song_fingerprint(song),"performance_score_fingerprint":performance_score_fingerprint(score),
        "automatic_aesthetic_score":False,"human_listening_required":True,
    }
    (out/"song.json").write_text(json.dumps(song,indent=2)+"\n",encoding="utf-8")
    (out/"performance_score.json").write_text(json.dumps(score,indent=2)+"\n",encoding="utf-8")
    (out/"metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
    (out/"README.md").write_text(
        "# AG09 Dogfood 5 — One Wood, Four Hands\n\n"
        "16-bar / 96 BPM / 24 kHz single-track integration candidate. The same persistent modeled steel-string guitar moves through fingerstyle, picked arpeggio, strumming/mute and percussive fingerstyle. Bars 4, 8 and 12 switch technique inside the bar; this is not an audio splice.\n",
        encoding="utf-8",
    )
    files=sorted(p for p in out.rglob("*") if p.is_file() and p.name!="SHA256SUMS.txt")
    (out/"SHA256SUMS.txt").write_text("".join(f"{_sha256(p)}  {p.relative_to(out).as_posix()}\n" for p in files),encoding="utf-8")
    print(json.dumps(metrics,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
