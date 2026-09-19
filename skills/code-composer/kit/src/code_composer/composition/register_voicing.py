from __future__ import annotations

from copy import deepcopy
from itertools import product

from ..agent.performance_ir import PerformanceIR, performance_ir_from_dict


class RegisterVoicingError(ValueError):
    pass


def _role_for_track(track: dict) -> str | None:
    # Canonical current arrangement uses role IDs as track IDs. Preserve an
    # explicit event/track role when one exists for future multi-track roles.
    return track.get("arrangement_role") or track.get("id")


def _octave_candidates(midi: int, hard_range: list[int]) -> list[int]:
    lo, hi = map(int, hard_range)
    out=[]
    for k in range(-11,12):
        n=int(midi)+12*k
        if lo <= n <= hi:
            out.append(n)
    return sorted(set(out))


def _preferred_distance(note: int, preferred: list[int]) -> int:
    lo,hi=map(int,preferred)
    if note < lo:
        return lo-note
    if note > hi:
        return note-hi
    return 0


def _voice_motion_cost(candidate: tuple[int,...], previous: tuple[int,...] | None, policy: str) -> float:
    if not previous or policy == "free":
        return 0.0
    a=tuple(sorted(previous)); b=tuple(sorted(candidate))
    n=min(len(a),len(b))
    if not n:
        return 0.0
    aa=a[:n]; bb=b[:n]
    motions=[bb[i]-aa[i] for i in range(n)]
    abs_motion=sum(abs(x) for x in motions)
    if policy == "smooth":
        return 0.70*abs_motion
    if policy == "stepwise_preferred":
        return 0.55*abs_motion + sum(max(0,abs(x)-2)*0.65 for x in motions)
    if policy == "oblique":
        moving=sum(1 for x in motions if x != 0)
        stationary=n-moving
        return 0.58*abs_motion + 0.9*moving - 0.45*stationary
    if policy == "contrary":
        cost=0.55*abs_motion
        if n >= 2:
            low=motions[0]; high=motions[-1]
            if low and high:
                if low*high > 0:
                    cost += 8.0
                elif low*high < 0:
                    cost -= 1.0
        return cost
    return 0.0


def _candidate_cost(
    candidate: tuple[int,...],
    original: tuple[int,...],
    plan: dict,
    previous: tuple[int,...] | None,
    previous_original: tuple[int,...] | None,
) -> float:
    preferred=plan["preferred_range"]
    center=float(plan["center"])
    # Preferred range is a strong authored target, center is a softer gravity
    # point. A tiny shift cost preserves the source octave when choices tie.
    pref=sum(_preferred_distance(n,preferred) for n in candidate)
    center_cost=sum(abs(n-center) for n in candidate)/max(1,len(candidate))
    shift=sum(abs(a-b) for a,b in zip(candidate,original))
    motion=_voice_motion_cost(candidate,previous,plan.get("motion_policy","free"))
    # Register allocation may move notes by octaves, but it should not casually
    # rewrite the melodic/voice-leading contour authored upstream. Penalize a
    # direction flip whenever an octave-equivalent alternative can avoid it.
    contour_penalty=0.0
    if previous and previous_original:
        n=min(len(candidate),len(original),len(previous),len(previous_original))
        for i in range(n):
            src=int(original[i])-int(previous_original[i])
            dst=int(candidate[i])-int(previous[i])
            if src == 0 and dst != 0:
                contour_penalty += 3.0
            elif src != 0 and dst != 0 and src*dst < 0:
                contour_penalty += 9.0
    return 4.0*pref + 0.12*center_cost + 0.055*shift + motion + contour_penalty


def _valid_voicing(candidate: tuple[int,...], plan: dict) -> bool:
    notes=tuple(sorted(candidate))
    if len(notes) > 1:
        if notes[-1]-notes[0] > int(plan["max_span"]):
            return False
        minimum=int(plan["min_intervoice_distance"])
        if any((b-a) < minimum for a,b in zip(notes,notes[1:])):
            return False
    return True


def _allocate_group(
    events: list[dict],
    plan: dict,
    previous: tuple[int,...] | None,
    previous_original: tuple[int,...] | None = None,
):
    indexed=sorted(enumerate(events),key=lambda pair:(int(pair[1]["midi"]),pair[0]))
    original=tuple(int(e["midi"]) for _,e in indexed)
    candidate_lists=[]
    for note in original:
        candidates=_octave_candidates(note,plan["hard_range"])
        if not candidates:
            raise RegisterVoicingError(
                f"MIDI {note} has no octave-equivalent pitch inside hard_range {plan['hard_range']}"
            )
        candidate_lists.append(candidates)

    best=None
    for combo in product(*candidate_lists):
        if tuple(sorted(combo)) != tuple(combo):
            continue
        if not _valid_voicing(combo,plan):
            continue
        cost=_candidate_cost(tuple(combo),original,plan,previous,previous_original)
        tie=(round(cost,9), tuple(abs(a-b) for a,b in zip(combo,original)), tuple(combo))
        if best is None or tie < best[0]:
            best=(tie,tuple(combo))
    if best is None:
        raise RegisterVoicingError(
            f"no octave-equivalent voicing satisfies hard_range={plan['hard_range']}, "
            f"max_span={plan['max_span']}, min_intervoice_distance={plan['min_intervoice_distance']} "
            f"for notes {list(original)}"
        )

    resolved=best[1]
    out=[dict(e) for e in events]
    for (orig_index,event),base,resolved_note in zip(indexed,original,resolved):
        x=dict(event)
        x["midi"]=int(resolved_note)
        x["register_voicing"]={
            **(x.get("register_voicing",{}) if isinstance(x.get("register_voicing"),dict) else {}),
            "base_midi":int(base),
            "resolved_midi":int(resolved_note),
            "octave_shift":int(resolved_note-base),
            "hard_range":list(plan["hard_range"]),
            "preferred_range":list(plan["preferred_range"]),
            "center":float(plan["center"]),
            "motion_policy":plan.get("motion_policy","free"),
        }
        out[orig_index]=x
    return out,tuple(sorted(resolved)),tuple(sorted(original))


def validate_register_voicing_contract(ir: dict, performance_ir: PerformanceIR | dict) -> None:
    """Preflight concrete resolved events where they already exist.

    Arrangement-authored sources may not contain concrete pitches until after
    resolution; those are checked during `realize_register_and_voicing` before
    synthesis. Resolved direct-IR inputs fail early here.
    """
    perf=(performance_ir if isinstance(performance_ir,PerformanceIR)
          else performance_ir_from_dict(performance_ir))
    plans=perf.register_plans
    for track in ir.get("tracks",[]):
        role=_role_for_track(track)
        if role not in plans or track.get("source",{}).get("type") != "resolved":
            continue
        plan=plans[role]
        groups={}
        for e in track.get("events",[]):
            if "midi" not in e or e.get("event_type")=="drum":
                continue
            groups.setdefault(round(float(e.get("start_beat",0.0)),9),[]).append(e)
        previous=None; previous_original=None
        for onset in sorted(groups):
            _,previous,previous_original=_allocate_group(
                groups[onset],plan,previous,previous_original
            )


def realize_register_and_voicing(ir: dict) -> dict:
    if "performance_ir" not in ir:
        return deepcopy(ir)
    if ir.get("register_voicing_resolved"):
        return deepcopy(ir)

    out=deepcopy(ir)
    perf=performance_ir_from_dict(out["performance_ir"])
    plans=perf.register_plans
    reports=[]

    for track in out.get("tracks",[]):
        role=_role_for_track(track)
        plan=plans.get(role)
        if not plan:
            continue
        groups={}
        passthrough=[]
        for idx,e in enumerate(track.get("events",[])):
            if "midi" not in e or e.get("event_type")=="drum":
                passthrough.append((idx,dict(e)))
                continue
            groups.setdefault(round(float(e.get("start_beat",0.0)),9),[]).append((idx,dict(e)))

        result=[dict(e) for e in track.get("events",[])]
        previous=None
        previous_original=None
        shifted=0
        outside_preferred=0
        max_observed_span=0
        onset_reports=[]
        for onset in sorted(groups):
            indexed_group=groups[onset]
            group=[e for _,e in indexed_group]
            allocated,previous,previous_original=_allocate_group(
                group,plan,previous,previous_original
            )
            pitches=sorted(int(e["midi"]) for e in allocated)
            span=(pitches[-1]-pitches[0]) if len(pitches)>1 else 0
            max_observed_span=max(max_observed_span,span)
            for (global_index,base_event),resolved_event in zip(indexed_group,allocated):
                result[global_index]=resolved_event
                if int(base_event["midi"]) != int(resolved_event["midi"]):
                    shifted+=1
                if _preferred_distance(int(resolved_event["midi"]),plan["preferred_range"]):
                    outside_preferred+=1
            onset_reports.append({
                "start_beat":onset,
                "base_pitches":[int(e["midi"]) for e in group],
                "resolved_pitches":[int(e["midi"]) for e in allocated],
                "span":span,
            })

        result.sort(key=lambda e:(float(e.get("start_beat",0.0)),int(e.get("midi",0))))
        track["events"]=result
        reports.append({
            "role":role,
            "event_count":sum(len(v) for v in groups.values()),
            "shifted_event_count":shifted,
            "outside_preferred_count":outside_preferred,
            "max_observed_simultaneous_span":max_observed_span,
            "hard_range":list(plan["hard_range"]),
            "preferred_range":list(plan["preferred_range"]),
            "motion_policy":plan.get("motion_policy","free"),
            "onsets":onset_reports,
        })

    out["register_voicing_resolved"]=True
    out["register_voicing_report"]={
        "role_count":len(reports),
        "roles":reports,
        "semantics":{
            "pitch_change":"octave-equivalent only",
            "max_span":"simultaneous voicing span",
            "preferred_range":"optimization target, not hard constraint",
        },
    }
    return out


__all__=[
    "RegisterVoicingError",
    "validate_register_voicing_contract",
    "realize_register_and_voicing",
]
