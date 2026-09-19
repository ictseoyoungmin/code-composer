from __future__ import annotations

from collections import defaultdict
from itertools import combinations


def _event_role(track,event):
    return event.get("arrangement_role") or track.get("arrangement_role") or track.get("id")


def _section_importance(perf: dict, section_id: str, role: str) -> float:
    cfg=perf.get("orchestration_sections",{}).get(section_id,{})
    if role in cfg.get("primary_roles",[]): return 1.0
    if role in cfg.get("secondary_roles",[]): return 0.72
    if role in cfg.get("decorative_roles",[]): return 0.45
    if role in cfg.get("silence_roles",[]): return 0.0
    return 0.60


def _policy(perf: dict, role: str) -> str:
    return perf.get("register_plans",{}).get(role,{}).get("overlap_policy","allow")


def analyze_register_collisions(resolved_ir: dict) -> dict:
    """Measure cross-role register occupancy without making a creative decision.

    Collision evidence is based on time overlap, pitch proximity and authored role
    importance. E3 reports the evidence; later Agent revision decides whether the
    overlap is musically intentional.
    """
    perf=resolved_ir.get("performance_ir",{})
    events=[]
    for track in resolved_ir.get("tracks",[]):
        for e in track.get("events",[]):
            if "midi" not in e or e.get("event_type")=="drum":
                continue
            start=float(e.get("start_beat",0.0)); dur=float(e.get("duration_beats",0.0))
            if dur <= 0: continue
            events.append({
                "role":_event_role(track,e),
                "section_id":e.get("section_id","unknown"),
                "start":start,"end":start+dur,"midi":int(e["midi"]),
            })

    aggregates=defaultdict(lambda:{
        "event_pair_count":0,"shared_beats":0.0,"weighted_collision":0.0,
        "closest_pitch_distance":128,
    })
    for a,b in combinations(events,2):
        if a["role"]==b["role"]:
            continue
        shared=max(0.0,min(a["end"],b["end"])-max(a["start"],b["start"]))
        if shared <= 1e-12:
            continue
        pitch_distance=abs(a["midi"]-b["midi"])
        # One octave is the edge of the register-collision observation window.
        proximity=max(0.0,1.0-pitch_distance/12.0)
        if proximity <= 0:
            continue
        section=a["section_id"] if a["section_id"]==b["section_id"] else f"{a['section_id']}|{b['section_id']}"
        role_a,role_b=sorted((a["role"],b["role"]))
        key=(section,role_a,role_b)
        importance=(_section_importance(perf,a["section_id"],a["role"])+
                    _section_importance(perf,b["section_id"],b["role"]))/2.0
        contribution=shared*proximity*importance
        x=aggregates[key]
        x["event_pair_count"]+=1
        x["shared_beats"]+=shared
        x["weighted_collision"]+=contribution
        x["closest_pitch_distance"]=min(x["closest_pitch_distance"],pitch_distance)

    pairs=[]
    total=0.0
    for (section,a,b),x in sorted(aggregates.items()):
        total+=x["weighted_collision"]
        policies={a:_policy(perf,a),b:_policy(perf,b)}
        intents=[]
        for role,policy in policies.items():
            if policy != "allow":
                intents.append({"role":role,"policy":policy})
        pairs.append({
            "section_id":section,"roles":[a,b],
            "event_pair_count":x["event_pair_count"],
            "shared_beats":round(x["shared_beats"],6),
            "collision_score":round(x["weighted_collision"],6),
            "closest_pitch_distance":x["closest_pitch_distance"],
            "overlap_policies":policies,
            "policy_intent":intents,
        })
    return {
        "collision_score":round(total,6),
        "pair_count":len(pairs),
        "pairs":pairs,
        "semantics":"time overlap × within-octave pitch proximity × authored role importance",
    }


__all__=["analyze_register_collisions"]
