from __future__ import annotations

from copy import deepcopy

from ..agent.performance_ir import PerformanceIR, performance_ir_from_dict


class OrchestrationBudgetError(ValueError):
    pass


def _role_for_track(track: dict) -> str | None:
    return track.get("arrangement_role") or track.get("id")


def _event_interval(event: dict) -> tuple[float,float]:
    start=float(event.get("start_beat",0.0))
    duration=max(0.0,float(event.get("duration_beats",0.0)))
    return start,start+duration


def _overlap(a0: float,a1: float,b0: float,b1: float) -> float:
    return max(0.0,min(a1,b1)-max(a0,b0))


def _section_spans(ir: dict) -> dict[str,tuple[float,float]]:
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


def _section_for_event(event: dict, spans: dict[str,tuple[float,float]]) -> str | None:
    sid=event.get("section_id")
    if sid in spans:
        return sid
    start=float(event.get("start_beat",0.0))
    for section,(a,b) in spans.items():
        if a-1e-9 <= start < b-1e-9:
            return section
    return None


def _priority_map(cfg: dict) -> dict[str,int]:
    # Larger values are preserved first when simultaneous-role budget arbitration occurs.
    out={}
    for role in cfg.get("decorative_roles",[]):
        out[role]=100
    for role in cfg.get("secondary_roles",[]):
        out[role]=200
    for role in cfg.get("primary_roles",[]):
        out[role]=300
    return out


def _protected_roles(cfg: dict) -> set[str]:
    """Roles in an authored overlap pair involving a primary get a small tie-break preference.

    `allowed_overlaps` is not a blanket ban on every unlisted pair. It tells budget arbitration
    which intended overlaps should be preserved before otherwise-equal alternatives.
    """
    primary=set(cfg.get("primary_roles",[]))
    protected=set()
    for pair in cfg.get("allowed_overlaps",[]):
        if len(pair)!=2:
            continue
        a,b=pair
        if a in primary or b in primary:
            protected.update((a,b))
    return protected


def validate_orchestration_budget_contract(ir: dict, performance_ir: PerformanceIR | dict) -> None:
    perf=(performance_ir if isinstance(performance_ir,PerformanceIR)
          else performance_ir_from_dict(performance_ir))
    spans=_section_spans(ir)
    sections=set(spans)
    cfg_sections=set(perf.orchestration_sections)
    if cfg_sections != sections:
        missing=sections-cfg_sections
        extra=cfg_sections-sections
        bits=[]
        if missing: bits.append(f"missing sections {sorted(missing)}")
        if extra: bits.append(f"unknown sections {sorted(extra)}")
        raise OrchestrationBudgetError("orchestration section mismatch: "+", ".join(bits))

    for sid,cfg in perf.orchestration_sections.items():
        primary=set(cfg.get("primary_roles",[]))
        secondary=set(cfg.get("secondary_roles",[]))
        decorative=set(cfg.get("decorative_roles",[]))
        silence=set(cfg.get("silence_roles",[]))
        active=primary|secondary|decorative
        budget=int(cfg.get("max_simultaneous_roles",1))
        if budget < len(primary):
            raise OrchestrationBudgetError(
                f"section {sid}: max_simultaneous_roles={budget} is smaller than "
                f"primary role count {len(primary)}"
            )
        if active & silence:
            raise OrchestrationBudgetError(
                f"section {sid}: active and silent roles conflict: {sorted(active & silence)}"
            )
        gap=set(cfg.get("phrase_gap_only_roles",[]))
        if not gap <= decorative:
            raise OrchestrationBudgetError(
                f"section {sid}: phrase_gap_only_roles must be decorative roles"
            )
        for pair in cfg.get("allowed_overlaps",[]):
            if len(pair)!=2 or pair[0]==pair[1]:
                raise OrchestrationBudgetError(
                    f"section {sid}: allowed_overlaps entries must contain two distinct roles"
                )
            if pair[0] not in active or pair[1] not in active:
                raise OrchestrationBudgetError(
                    f"section {sid}: allowed overlap {pair} must reference active roles"
                )


def _primary_phrase_windows(perf: PerformanceIR, section: str, primary_roles: set[str]):
    out=[]
    for phrase in perf.phrases:
        if phrase.get("section_id") != section or phrase.get("role") not in primary_roles:
            continue
        start=float(phrase["start_beat"])
        end=start+float(phrase["duration_beats"])
        out.append((start,end,phrase["role"],phrase["phrase_id"]))
    return out


def _event_overlaps_windows(event: dict, windows) -> bool:
    a0,a1=_event_interval(event)
    if a1 <= a0:
        return False
    return any(_overlap(a0,a1,b0,b1)>1e-9 for b0,b1,_,_ in windows)


def _would_exceed_budget(candidate: dict, accepted: list[dict], budget: int) -> bool:
    c0,c1=_event_interval(candidate)
    if c1 <= c0:
        return False
    relevant=[e for e in accepted if _overlap(c0,c1,*_event_interval(e))>1e-9]
    boundaries={c0,c1}
    for e in relevant:
        e0,e1=_event_interval(e)
        boundaries.add(max(c0,e0)); boundaries.add(min(c1,e1))
    pts=sorted(boundaries)
    for a,b in zip(pts,pts[1:]):
        if b-a <= 1e-12:
            continue
        mid=(a+b)*0.5
        roles={candidate["_orchestration_role"]}
        for e in relevant:
            e0,e1=_event_interval(e)
            if e0-1e-12 <= mid < e1-1e-12:
                roles.add(e["_orchestration_role"])
        if len(roles) > budget:
            return True
    return False


def realize_orchestration_budget(ir: dict) -> dict:
    if "performance_ir" not in ir:
        return deepcopy(ir)
    if ir.get("orchestration_budget_resolved"):
        return deepcopy(ir)

    out=deepcopy(ir)
    perf=performance_ir_from_dict(out["performance_ir"])
    validate_orchestration_budget_contract(out,perf)
    spans=_section_spans(out)

    # Flatten events with role/section provenance. Event copies are restored to tracks later.
    flat=[]
    tracks_by_id={}
    for ti,track in enumerate(out.get("tracks",[])):
        role=_role_for_track(track)
        tracks_by_id[ti]=track
        for ei,event in enumerate(track.get("events",[])):
            x=dict(event)
            sid=_section_for_event(x,spans)
            x["_track_index"]=ti
            x["_event_index"]=ei
            x["_orchestration_role"]=role
            x["_orchestration_section"]=sid
            x["_orchestration_passthrough_control"]=bool(str(x.get("event_type","")).endswith("_control"))
            flat.append(x)

    removed=[]
    stage=[]

    # 1. Hard authored silence. This runs after arrangement/transition material, so downstream
    # fills may not reintroduce a silent role. A sustain that begins in the preceding section is
    # truncated at the first silent-section boundary instead of being allowed to ring through it.
    for e in flat:
        if e.get("_orchestration_passthrough_control"):
            stage.append(e)
            continue
        role=e["_orchestration_role"]
        a0,a1=_event_interval(e)
        first_silent_start=None
        starts_inside_silence=False
        for sid,(s0,s1) in spans.items():
            cfg=perf.orchestration_sections.get(sid,{})
            if role not in set(cfg.get("silence_roles",[])):
                continue
            if _overlap(a0,a1,s0,s1) <= 1e-9:
                continue
            if s0-1e-9 <= a0 < s1-1e-9:
                starts_inside_silence=True
                first_silent_start=a0
                break
            if a0 < s0 < a1 and (first_silent_start is None or s0 < first_silent_start):
                first_silent_start=s0
        if starts_inside_silence:
            removed.append((e,"silence_role"))
            continue
        if first_silent_start is not None:
            x=dict(e)
            x["duration_beats"]=max(0.0,first_silent_start-a0)
            x["orchestration_budget"]={
                **(x.get("orchestration_budget",{}) if isinstance(x.get("orchestration_budget"),dict) else {}),
                "truncated_for_silence_at":first_silent_start,
            }
            if x["duration_beats"] <= 1e-9:
                removed.append((e,"silence_role"))
            else:
                stage.append(x)
        else:
            stage.append(e)

    # 2. Decorative roles that are allowed only outside authored primary phrase bodies.
    stage2=[]
    phrase_windows={}
    for sid,cfg in perf.orchestration_sections.items():
        phrase_windows[sid]=_primary_phrase_windows(perf,sid,set(cfg.get("primary_roles",[])))
    for e in stage:
        sid=e["_orchestration_section"]
        role=e["_orchestration_role"]
        cfg=perf.orchestration_sections.get(sid,{}) if sid else {}
        if role in set(cfg.get("phrase_gap_only_roles",[])) and _event_overlaps_windows(e,phrase_windows.get(sid,[])):
            removed.append((e,"primary_phrase_overlap"))
        else:
            stage2.append(e)

    # 3. Section-local unique-role budget. Higher authored role class wins. Protected overlap
    # pairs are tie-breakers, never hidden creative decisions.
    accepted=[e for e in stage2 if e.get("_orchestration_passthrough_control")]
    by_section={}
    for e in stage2:
        if e.get("_orchestration_passthrough_control"):
            continue
        by_section.setdefault(e["_orchestration_section"],[]).append(e)

    for sid,events in by_section.items():
        if sid not in perf.orchestration_sections:
            accepted.extend(events)
            continue
        cfg=perf.orchestration_sections[sid]
        budget=int(cfg["max_simultaneous_roles"])
        pri=_priority_map(cfg)
        protected=_protected_roles(cfg)
        ordered=sorted(
            events,
            key=lambda e:(
                -pri.get(e["_orchestration_role"],0),
                -(1 if e["_orchestration_role"] in protected else 0),
                float(e.get("start_beat",0.0)),
                str(e["_orchestration_role"]),
                int(e.get("midi",-1)),
                str(e.get("drum","")),
                e["_track_index"],e["_event_index"],
            )
        )
        local=[]
        for e in ordered:
            if _would_exceed_budget(e,local,budget):
                removed.append((e,"simultaneous_role_budget"))
            else:
                local.append(e)
        accepted.extend(local)

    # Restore events to original tracks, preserving musical sort order.
    kept_map={(e["_track_index"],e["_event_index"]):e for e in accepted}
    section_reports={}
    for sid,cfg in perf.orchestration_sections.items():
        section_reports[sid]={
            "primary_roles":list(cfg.get("primary_roles",[])),
            "secondary_roles":list(cfg.get("secondary_roles",[])),
            "decorative_roles":list(cfg.get("decorative_roles",[])),
            "max_simultaneous_roles":int(cfg.get("max_simultaneous_roles",1)),
            "phrase_gap_only_roles":list(cfg.get("phrase_gap_only_roles",[])),
            "silence_roles":list(cfg.get("silence_roles",[])),
            "removed":{"silence_role":0,"primary_phrase_overlap":0,"simultaneous_role_budget":0},
        }
    for e,reason in removed:
        sid=e["_orchestration_section"]
        if sid in section_reports:
            section_reports[sid]["removed"][reason]+=1

    for ti,track in enumerate(out.get("tracks",[])):
        new=[]
        for ei,e in enumerate(track.get("events",[])):
            kept=kept_map.get((ti,ei))
            if kept is not None:
                passthrough=bool(kept.get("_orchestration_passthrough_control"))
                x={k:v for k,v in kept.items() if not k.startswith("_orchestration_") and k not in {"_track_index","_event_index"}}
                if not passthrough:
                    x["orchestration_budget"]={
                        **(x.get("orchestration_budget",{}) if isinstance(x.get("orchestration_budget"),dict) else {}),
                        "section_id":_section_for_event(x,spans),
                        "role":_role_for_track(track),
                        "kept":True,
                    }
                new.append(x)
        track["events"]=sorted(new,key=lambda e:(float(e.get("start_beat",0.0)),int(e.get("midi",-1)),str(e.get("drum",""))))

    out["orchestration_budget_resolved"]=True
    out["orchestration_budget_report"]={
        "section_count":len(section_reports),
        "removed_event_count":len(removed),
        "sections":section_reports,
        "semantics":{
            "priority_order":["primary","secondary","decorative"],
            "allowed_overlaps":"protected during budget arbitration; not a blanket ban on unlisted pairs",
            "phrase_gap_only":"decorative event must not overlap authored primary phrase body",
            "silence_roles":"hard event gate after arrangement/transition generation",
        },
    }
    return out


__all__=[
    "OrchestrationBudgetError",
    "validate_orchestration_budget_contract",
    "realize_orchestration_budget",
]
