from __future__ import annotations

from copy import deepcopy

from ..agent.performance_ir import PerformanceIR, performance_ir_from_dict
from ..core.theory import (
    NOTE_TO_PC,
    SCALES,
    scale_degree_to_midi,
    scale_pitch_classes,
    nearest_inversion,
)


class MusicalTransitionError(ValueError):
    pass


def _role_for_track(track: dict) -> str | None:
    return track.get("arrangement_role") or track.get("id")


def _section_spans(ir: dict) -> dict[str, tuple[float, float]]:
    bpb=float(ir.get("transport",{}).get("beats_per_bar",4.0))
    out={}
    cursor=0.0
    for sec in ir.get("form",[]):
        sid=sec["id"]
        start=float(sec.get("start_bar",cursor/bpb))*bpb
        end=start+float(sec["bars"])*bpb
        out[sid]=(start,end)
        cursor=end
    return out


def _track_map(ir: dict) -> dict[str, dict]:
    out={}
    for track in ir.get("tracks",[]):
        role=_role_for_track(track)
        if role:
            out[role]=track
    return out


def _event_interval(event: dict):
    start=float(event.get("start_beat",0.0))
    return start,start+max(0.0,float(event.get("duration_beats",0.0)))


def _cut_window(events: list[dict], start: float, end: float, reason: str):
    """Remove onsets inside [start,end) and truncate sustains at the window start."""
    out=[]; removed=0; truncated=0
    for event in events:
        e=dict(event)
        a,b=_event_interval(e)
        if start-1e-9 <= a < end-1e-9:
            removed+=1
            continue
        if a < start < b:
            e["duration_beats"]=max(1e-6,start-a)
            e["musical_transition"]={
                **(e.get("musical_transition",{}) if isinstance(e.get("musical_transition"),dict) else {}),
                "truncated_for":reason,
                "truncated_at":start,
            }
            truncated+=1
        out.append(e)
    return out,removed,truncated


def _append_event(track: dict, event: dict):
    track.setdefault("events",[]).append(event)


def _sort_tracks(ir: dict):
    for track in ir.get("tracks",[]):
        track["events"]=sorted(
            track.get("events",[]),
            key=lambda e:(float(e.get("start_beat",0.0)), int(e.get("midi",-1)), str(e.get("drum","")))
        )


def _scale_approach(target: int, root: str, scale: str, direction: str, steps: int) -> list[int]:
    pcs=scale_pitch_classes(root,scale)
    if direction=="below":
        found=[]; n=target-1
        while len(found)<steps and n>=0:
            if n%12 in pcs: found.append(n)
            n-=1
        return list(reversed(found))
    found=[]; n=target+1
    while len(found)<steps and n<=127:
        if n%12 in pcs: found.append(n)
        n+=1
    return list(reversed(found))  # farthest -> nearest while descending to target


def _chromatic_approach(target: int, direction: str, steps: int) -> list[int]:
    if direction=="below":
        return list(range(target-steps,target))
    return list(range(target+steps,target,-1))


def validate_musical_transition_contract(ir: dict, performance_ir: PerformanceIR | dict) -> None:
    perf=performance_ir if isinstance(performance_ir,PerformanceIR) else performance_ir_from_dict(performance_ir)
    spans=_section_spans(ir)
    tracks=set(_track_map(ir))
    tonal=ir.get("tonal",{})
    if tonal.get("root") not in NOTE_TO_PC or tonal.get("scale") not in SCALES:
        if perf.transitions:
            raise MusicalTransitionError("musical transitions require a supported tonal root/scale")
    for i,t in enumerate(perf.transitions):
        name=f"transition[{i}] {t.get('from_section')}->{t.get('to_section')}"
        if t.get("from_section") not in spans or t.get("to_section") not in spans:
            raise MusicalTransitionError(f"{name}: unknown section")
        ant=t.get("harmonic_anticipation",{})
        if ant.get("enabled"):
            role=ant["role"]
            if role not in perf.register_plans:
                raise MusicalTransitionError(f"{name}: harmonic anticipation role {role} needs a register plan")
        bass=t.get("bass_approach",{"type":"none"})
        if bass.get("type")!="none" and "bass" not in set(perf.register_plans) | tracks:
            raise MusicalTransitionError(f"{name}: bass approach requires a bass role")
        fill=t.get("rhythm_fill",{})
        if fill and tracks and fill["role"] not in tracks:
            # Direct resolved IR can fail early; arrangement IR may not yet have every resolved track.
            arrangement_roles=set(ir.get("arrangement",{}).get("roles",{}))
            if fill["role"] not in arrangement_roles:
                raise MusicalTransitionError(f"{name}: rhythm fill role {fill['role']} has no track/arrangement role")


def _apply_texture_subtraction(track_map, transition, boundary, report):
    cfg=transition.get("texture_subtraction",{})
    if not cfg:
        return
    start=boundary-float(cfg["beats"])
    for role in cfg["roles"]:
        track=track_map.get(role)
        if not track: continue
        new,removed,truncated=_cut_window(track.get("events",[]),start,boundary,"texture_subtraction")
        track["events"]=new
        report["texture_subtraction_removed"]+=removed
        report["texture_subtraction_truncated"]+=truncated


def _apply_cadence_extension(track_map, transition, boundary, report):
    cfg=transition.get("cadence_extension",{})
    if not cfg:
        return
    silence=float(transition.get("silence_beats",0.0))
    latest_end=boundary-silence
    extension=float(cfg["beats"])
    for role in cfg["roles"]:
        track=track_map.get(role)
        if not track: continue
        candidates=[e for e in track.get("events",[]) if float(e.get("start_beat",0.0)) < latest_end-1e-9]
        if not candidates: continue
        last_start=max(float(e["start_beat"]) for e in candidates)
        group=[e for e in candidates if abs(float(e["start_beat"])-last_start)<1e-9]
        ids={id(e) for e in group}
        new=[]
        for e in track.get("events",[]):
            x=dict(e)
            if id(e) in ids:
                a,b=_event_interval(x)
                target=min(latest_end,b+extension)
                if target>b+1e-9:
                    x["duration_beats"]=target-a
                    x["musical_transition"]={
                        **(x.get("musical_transition",{}) if isinstance(x.get("musical_transition"),dict) else {}),
                        "cadence_extension_beats":target-b,
                    }
                    report["cadence_extended_events"]+=1
            new.append(x)
        track["events"]=new


def _apply_silence(track_map, transition, boundary, report):
    beats=float(transition.get("silence_beats",0.0))
    if beats<=0: return
    start=boundary-beats
    for role,track in track_map.items():
        new,removed,truncated=_cut_window(track.get("events",[]),start,boundary,"explicit_silence")
        track["events"]=new
        report["silence_removed"]+=removed
        report["silence_truncated"]+=truncated


def _apply_register_preparation(track_map, transition, boundary, report):
    for role,cfg in transition.get("register_preparation",{}).items():
        track=track_map.get(role)
        if not track: continue
        end=boundary+float(cfg["beats"])
        semitones=int(cfg["semitones"])
        if semitones==0: continue
        new=[]
        for event in track.get("events",[]):
            x=dict(event)
            start=float(x.get("start_beat",0.0))
            if boundary-1e-9 <= start < end-1e-9 and "midi" in x and x.get("event_type")!="drum":
                base=int(x["midi"])
                x["midi"]=base+semitones
                x["musical_transition"]={
                    **(x.get("musical_transition",{}) if isinstance(x.get("musical_transition"),dict) else {}),
                    "register_preparation":semitones,
                    "base_midi":base,
                }
                report["register_prepared_events"]+=1
            new.append(x)
        track["events"]=new


def _add_harmonic_anticipation(ir, perf, track_map, transition, boundary, report):
    cfg=transition.get("harmonic_anticipation",{})
    if not cfg.get("enabled"): return
    role=cfg["role"]
    track=track_map.get(role)
    if not track:
        raise MusicalTransitionError(f"harmonic anticipation role {role} has no resolved track")
    root=ir["tonal"]["root"]; scale=ir["tonal"]["scale"]
    raw=[scale_degree_to_midi(root,scale,int(cfg["target_degree"])+int(off),4) for off in cfg["chord_intervals"]]
    center=int(round(float(perf.register_plans[role]["center"])))
    chord=nearest_inversion(raw,center)
    start=boundary-float(cfg["beats"])
    duration=float(cfg["beats"])*float(cfg["gate"])
    for midi in chord:
        _append_event(track,{
            "start_beat":start,"duration_beats":duration,"midi":int(midi),
            "velocity":float(cfg["velocity"]),"section_id":transition["from_section"],
            "arrangement_role":role,"transition_material":"harmonic_anticipation",
            "musical_transition":{"type":"harmonic_anticipation","to_section":transition["to_section"],"target_degree":int(cfg["target_degree"])}
        })
        report["harmonic_anticipation_events"]+=1


def _add_pickup(ir, track_map, transition, boundary, report):
    cfg=transition.get("pickup",{})
    if not cfg.get("enabled"): return
    role=cfg["role"]
    track=track_map.get(role)
    if not track:
        raise MusicalTransitionError(f"pickup role {role} has no resolved track")
    total=sum(float(x) for x in cfg["rhythm"])
    cursor=boundary-total
    root=ir["tonal"]["root"]; scale=ir["tonal"]["scale"]
    for degree,dur in zip(cfg["degrees"],cfg["rhythm"]):
        _append_event(track,{
            "start_beat":cursor,"duration_beats":float(dur)*0.92,
            "midi":scale_degree_to_midi(root,scale,int(degree),int(cfg["octave"])),
            "velocity":float(cfg["velocity"]),"section_id":transition["from_section"],
            "arrangement_role":role,"transition_material":"pickup",
            "musical_transition":{"type":"pickup","to_section":transition["to_section"]}
        })
        cursor+=float(dur)
        report["pickup_events"]+=1


def _add_bass_approach(ir, track_map, transition, boundary, report):
    cfg=transition.get("bass_approach",{"type":"none"})
    kind=cfg.get("type","none")
    if kind=="none": return
    track=track_map.get("bass")
    if not track:
        raise MusicalTransitionError("bass approach requires resolved bass track")
    before=[e for e in track.get("events",[]) if "midi" in e and float(e.get("start_beat",0)) < boundary-1e-9]
    after=[e for e in track.get("events",[]) if "midi" in e and float(e.get("start_beat",0)) >= boundary-1e-9]
    if not after:
        raise MusicalTransitionError("bass approach requires a target bass event in the destination section")
    target=int(min(after,key=lambda e:float(e["start_beat"]))["midi"])
    beats=float(cfg["beats"])
    if kind=="pedal":
        if not before: raise MusicalTransitionError("pedal bass approach requires a preceding bass event")
        notes=[int(max(before,key=lambda e:float(e["start_beat"]))["midi"])]
    elif kind=="chromatic":
        notes=_chromatic_approach(target,cfg["direction"],int(cfg["steps"]))
    else:
        steps=1 if kind=="step" else int(cfg["steps"])
        notes=_scale_approach(target,ir["tonal"]["root"],ir["tonal"]["scale"],cfg["direction"],steps)
    if not notes: return
    slot=beats/len(notes)
    cursor=boundary-beats
    for midi in notes:
        _append_event(track,{
            "start_beat":cursor,"duration_beats":slot*0.90,"midi":int(midi),
            "velocity":float(cfg["velocity"]),"section_id":transition["from_section"],
            "arrangement_role":"bass","transition_material":"bass_approach",
            "musical_transition":{"type":"bass_approach","approach":kind,"to_section":transition["to_section"]}
        })
        cursor+=slot
        report["bass_approach_events"]+=1


def _add_rhythm_fill(track_map, transition, boundary, report):
    cfg=transition.get("rhythm_fill",{})
    if not cfg: return
    role=cfg["role"]
    track=track_map.get(role)
    if not track:
        raise MusicalTransitionError(f"rhythm fill role {role} has no resolved track")
    for item in cfg["events"]:
        event={
            "event_type":"drum","drum":item["drum"],
            "start_beat":boundary+float(item["offset_beats"]),
            "duration_beats":float(item["duration_beats"]),
            "velocity":float(item["velocity"]),
            "section_id":transition["from_section"],"arrangement_role":role,
            "transition_material":"rhythm_fill",
            "musical_transition":{"type":"rhythm_fill","to_section":transition["to_section"]},
        }
        if "pan" in item: event["pan"]=float(item["pan"])
        if "articulation" in item: event["articulation"]=str(item["articulation"])
        if "strike_force" in item: event["strike_force"]=float(item["strike_force"])
        if "strike_position" in item: event["strike_position"]=float(item["strike_position"])
        _append_event(track,event)
        report["rhythm_fill_events"]+=1


def realize_musical_transitions(ir: dict) -> dict:
    if "performance_ir" not in ir:
        return deepcopy(ir)
    if ir.get("musical_transitions_resolved"):
        return deepcopy(ir)

    out=deepcopy(ir)
    perf=performance_ir_from_dict(out["performance_ir"])
    validate_musical_transition_contract(out,perf)
    spans=_section_spans(out)
    track_map=_track_map(out)
    reports=[]

    for index,t in enumerate(perf.transitions):
        boundary=spans[t["to_section"]][0]
        report={
            "index":index,"from_section":t["from_section"],"to_section":t["to_section"],"boundary_beat":boundary,
            "texture_subtraction_removed":0,"texture_subtraction_truncated":0,
            "cadence_extended_events":0,"silence_removed":0,"silence_truncated":0,
            "register_prepared_events":0,"harmonic_anticipation_events":0,"pickup_events":0,
            "bass_approach_events":0,"rhythm_fill_events":0,
        }
        # Structural subtraction and cadence are applied to existing material first.
        _apply_texture_subtraction(track_map,t,boundary,report)
        _apply_cadence_extension(track_map,t,boundary,report)
        _apply_silence(track_map,t,boundary,report)
        _apply_register_preparation(track_map,t,boundary,report)
        # Explicit transition material is authored after silence so it may intentionally occupy the gap.
        _add_harmonic_anticipation(out,perf,track_map,t,boundary,report)
        _add_pickup(out,track_map,t,boundary,report)
        _add_bass_approach(out,track_map,t,boundary,report)
        _add_rhythm_fill(track_map,t,boundary,report)
        reports.append(report)

    _sort_tracks(out)
    out["musical_transitions_resolved"]=True
    out["musical_transition_report"]={
        "transition_count":len(reports),"transitions":reports,
        "semantics":{
            "silence":"removes existing material before explicit transition events are authored",
            "harmonic_anticipation":"explicit scale-degree chord, role and voicing intervals authored by Agent",
            "pickup":"explicit scale degrees/rhythm/octave authored by Agent",
            "bass_approach":"deterministic operation into existing destination bass target",
            "register_preparation":"explicit semitone shift in a bounded destination window before E3 allocation",
            "rhythm_fill":"explicit drum events relative to the section boundary",
        },
    }
    return out


__all__=["MusicalTransitionError","validate_musical_transition_contract","realize_musical_transitions"]
