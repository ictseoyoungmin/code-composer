#!/usr/bin/env python3
"""Cedar Rain, Afterlight R3 — guitar-native fingerstyle texture revision."""
from __future__ import annotations

from copy import deepcopy
import math
import compose_cedar_rain_afterlight as base

BPM=base.BPM
PRESET=base.PRESET
OPEN=base.OPEN
INSPIRATION=base.INSPIRATION
VOICINGS=base.VOICINGS
LOW=base.LOW
SECTIONS=base.SECTIONS
START=base.START
TOTAL_BARS=base.TOTAL_BARS
HARMONY=base.HARMONY
ENERGY=base.ENERGY


def _role_for_string(s:int):
    if s>=4:
        return ("thumb","bass" if s>=5 else "inner","thumb")
    if s==3:
        return ("index","inner","finger")
    if s==2:
        return ("middle","treble","finger")
    return ("ring","treble","finger")


def _arp_note(eid,start,dur,pos,vel,gid,seq,*,use_nail=False):
    _m,s,_f=pos
    player,voice,method=_role_for_string(int(s))
    if use_nail and s<=2:
        method="nail"
    ev=base.note(
        eid,start,dur,pos,vel,method,
        pluck=.145 if method=="nail" else (.18 if s>=4 else .165),
        angle=31. if method=="thumb" else (43. if method=="nail" else 37.),
    )
    ev["instrument_performance"]["arpeggio"]={
        "gesture_id":gid,
        "player":player,
        "voice":voice,
        "sequence_index":int(seq),
    }
    return ev


def _by_string(chord):
    return {int(p[1]):p for p in VOICINGS[chord]}


def _supports(chord,melody_string,j,local):
    bys=_by_string(chord)
    bass=[bys[s] for s in (6,5,4) if s in bys and s!=melody_string]
    inn=[bys[s] for s in (4,3,2,1) if s in bys and s!=melody_string]
    if not bass:
        bass=inn[:1]
    if melody_string==1:
        pref=[bys[s] for s in (3,2,4) if s in bys and s!=1]
    else:
        pref=[bys[s] for s in (4,3,1) if s in bys and s!=2]
    if len(pref)<2:
        pref=inn
    b=bass[(local+j)%len(bass)]
    a=pref[(local+j)%len(pref)]
    c=pref[(local+j+1)%len(pref)]
    if c[1]==a[1]:
        c=next(p for p in inn if p[1]!=a[1])
    return b,a,c


def finger_bar(bar0:int,local:int,section:str,percussive:bool=False):
    """Embed every top-line note inside a real 3/4-contact guitar arpeggio.

    R2 exposed four treble notes as an independent layer. R3 removes that layer.
    Every melodic arrival is now preceded by two or three contacts on different
    physical strings, with explicit thumb/index/middle/ring player authority.
    """
    chord=HARMONY[bar0]
    energy=ENERGY[section]+.022*math.sin((local+1)*.67)
    out=[]
    for j,(off,midi,mel_dur) in enumerate(base.melody(bar0,local,section)):
        mel=base.top_pos(midi,alt=((local+j)%5==0 and section in {"development","recap","percussive"}))
        bass,a,c=_supports(chord,int(mel[1]),j,local)
        gid=f"r3-b{bar0+1:02d}-g{j}"
        if j%2==0:
            contacts=[(-.24,bass,.82,-.055),(-.145,a,.66,-.025),(-.070,c,.58,-.010),(0.,mel,mel_dur,.060)]
        else:
            contacts=[(-.155,a,.62,-.030),(-.072,c,.55,-.010),(0.,mel,mel_dur,.055)]

        # Repair any physical-string collision before authoring the gesture.
        used=set(); repaired=[]
        alternatives=list(VOICINGS[chord])
        for k,(delta,pos,dur,dv) in enumerate(contacts):
            if k==len(contacts)-1:
                pos=mel
            elif pos[1] in used or pos[1]==mel[1]:
                pos=next(p for p in alternatives if p[1] not in used and p[1]!=mel[1])
            used.add(pos[1])
            repaired.append((delta,pos,dur,dv))
        repaired[-1]=(repaired[-1][0],mel,repaired[-1][2],repaired[-1][3])

        peak=bar0*4.0+off
        starts=[max(bar0*4.0+.006*i,peak+delta) for i,(delta,_p,_d,_v) in enumerate(repaired)]
        starts[-1]=peak
        for i in range(1,len(starts)):
            if starts[i]<=starts[i-1]+1e-6:
                starts[i]=starts[i-1]+.018
        if starts[-1]>peak+1e-9:
            shift=starts[-1]-peak
            starts=[x-shift for x in starts]

        for seq,((_delta,pos,dur,dv),start) in enumerate(zip(repaired,starts)):
            out.append(_arp_note(
                f"r3-b{bar0+1:02d}-g{j}-n{seq}",start,dur,pos,energy+dv,gid,seq,
                use_nail=(seq==len(repaired)-1 and (bar0+j)%17==0),
            ))

    if percussive:
        if local%2==0:
            out += [base.action(f"b{bar0+1:02d}-tap","body_tap",bar0*4+1.50,.44,"lower_bout"),
                    base.action(f"b{bar0+1:02d}-slap","top_slap",bar0*4+3.00,.47,"soundboard")]
        else:
            out += [base.action(f"b{bar0+1:02d}-slap","top_slap",bar0*4+1.50,.43,"soundboard"),
                    base.action(f"b{bar0+1:02d}-ss","string_slap",bar0*4+3.25,.46)]
    return out


def build_events():
    ev=[]
    for l in range(4):
        ev+=base.harmonic_bar(l,l)
    for l in range(12):
        b=START["theme"]+l; ev+=finger_bar(b,l,"theme")
    for l in range(12):
        b=START["development"]+l; ev+=finger_bar(b,l,"development")
    for l in range(8):
        b=START["bridge"]+l; ev+=base.strum_bar(b,l,final_rake=l in {3,7})
    for l in range(12):
        b=START["percussive"]+l; ev+=finger_bar(b,l,"percussive",True)
    for l in range(8):
        b=START["recap"]+l; ev+=finger_bar(b,l,"recap")
    for l in range(3):
        b=START["coda"]+l; ev+=base.harmonic_bar(b,l,final=l==2)
    b=START["coda"]+3
    ev.append(base.note("final-bass",b*4,1.85,(40,6,0),.46,"thumb"))
    sid="final-rake"; cfg=base.strum_cfg(sid,"down",0,.54,False,True)
    for n,(m,s,f) in enumerate(VOICINGS["Em9"]):
        perf={"string":s,"fret":f,"right_hand":{"method":"pick","pluck_position":.12,"attack_angle_deg":cfg["attack_angle_deg"],"strength":cfg["entry_strength"]},"strum":deepcopy(cfg)}
        ev.append({"id":f"{sid}-{n}","type":"note","start_beat":b*4+2.,"duration_beats":1.35,"midi":m,"velocity":.56,"instrument_performance":perf})
    return sorted(ev,key=lambda x:(float(x["start_beat"]),0 if x["type"]=="note" else 1,x["id"]))


def build_song():
    song=base.build_song(); song["meta"]["revision"]="SOLO-ACOUSTIC-PROD-R3"; return song


def validate_guitar_native_texture(events=None):
    events=build_events() if events is None else events
    arp=[e for e in events if e.get("instrument_performance",{}).get("arpeggio")]
    groups={}
    for e in arp:
        a=e["instrument_performance"]["arpeggio"]
        groups.setdefault(a["gesture_id"],[]).append(e)
    expected=(12+12+12+8)*4
    if len(groups)!=expected:
        raise ValueError(f"expected {expected} gestures, got {len(groups)}")

    peaks=first=isolated=0
    for gid,notes in groups.items():
        notes=sorted(notes,key=lambda e:e["instrument_performance"]["arpeggio"]["sequence_index"])
        strings=[int(e["instrument_performance"]["string"]) for e in notes]
        players=[e["instrument_performance"]["arpeggio"]["player"] for e in notes]
        if len(notes)<3 or len(set(strings))<3 or len(set(strings))!=len(strings):
            raise ValueError(f"{gid}: not a >=3-string gesture: {strings}")
        if players[-1] not in {"middle","ring"}:
            raise ValueError(f"{gid}: melody peak not m/a finger")
        if len(notes)==4 and "thumb" not in players:
            raise ValueError(f"{gid}: four-contact gesture missing thumb")
        peak=notes[-1]; peaks+=1
        if int(peak["instrument_performance"]["string"])==1:
            first+=1
        supports=[e for e in notes[:-1] if 0.0<float(peak["start_beat"])-float(e["start_beat"])<=.28]
        if len(supports)<2:
            isolated+=1
    ratio=first/max(1,peaks)
    if ratio>.72:
        raise ValueError(f"melody too concentrated on string 1: {ratio:.3f}")
    if isolated:
        raise ValueError(f"isolated melody peaks: {isolated}")
    return {
        "arpeggio_gesture_count":len(groups),
        "arpeggio_event_count":len(arp),
        "melody_peak_count":peaks,
        "isolated_melody_peak_count":isolated,
        "first_string_melody_peak_ratio":ratio,
        "minimum_contacts_per_gesture":min(len(v) for v in groups.values()),
        "guitar_native_texture":True,
    }


def bar_sigs(events):
    return base.bar_sigs(events)
