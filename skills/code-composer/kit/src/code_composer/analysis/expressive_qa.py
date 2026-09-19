from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

from .register_analysis import analyze_register_collisions


EPS=1e-9


def _role(track,event):
    return event.get("arrangement_role") or track.get("arrangement_role") or track.get("id")


def _interval(event):
    start=float(event.get("start_beat",0.0))
    end=start+max(0.0,float(event.get("duration_beats",0.0)))
    return start,end


def _overlap(a0,a1,b0,b1):
    return max(0.0,min(a1,b1)-max(a0,b0))




def _merge_intervals(intervals):
    merged=[]
    for start,end in sorted((float(a),float(b)) for a,b in intervals if float(b)>float(a)+EPS):
        if not merged or start > merged[-1][1] + EPS:
            merged.append([start,end])
        else:
            merged[-1][1]=max(merged[-1][1],end)
    return [(a,b) for a,b in merged]


def _interval_total(intervals):
    return sum(max(0.0,b-a) for a,b in intervals)


def _interval_intersection_total(a_intervals,b_intervals):
    a=_merge_intervals(a_intervals); b=_merge_intervals(b_intervals)
    i=j=0; total=0.0
    while i<len(a) and j<len(b):
        a0,a1=a[i]; b0,b1=b[j]
        total += _overlap(a0,a1,b0,b1)
        if a1 < b1 - EPS:
            i += 1
        else:
            j += 1
    return total

def _events_by_role(ir):
    out=defaultdict(list)
    for track in ir.get("tracks",[]):
        role=track.get("arrangement_role") or track.get("id")
        for event in track.get("events",[]):
            x=dict(event)
            x["_role"]=event.get("arrangement_role") or role
            out[x["_role"]].append(x)
    for role in out:
        out[role].sort(key=lambda e:(float(e.get("start_beat",0.0)),int(e.get("midi",-1))))
    return out


def _curve_span(curve):
    vals=[float(p[1]) for p in curve or []]
    return (max(vals)-min(vals)) if vals else 0.0


def _phrase_events(events,phrase):
    start=float(phrase["start_beat"])
    end=start+float(phrase["duration_beats"])
    return [e for e in events if start-EPS <= float(e.get("start_beat",-1)) < end-EPS]


def _issue(code,severity,**payload):
    return {"code":code,"severity":severity,**payload}


def _analyze_phrase_expression(ir,perf,events_by_role):
    issues=[]
    evidence=[]
    realization=perf.get("realization",{})
    micro=realization.get("microtiming",{})
    for phrase in perf.get("phrases",[]):
        role=phrase["role"]
        events=_phrase_events(events_by_role.get(role,[]),phrase)
        if not events:
            continue

        offsets=[
            float(e.get("performance",{}).get("timing_offset_ms",0.0))
            for e in events
        ]
        velocities=[float(e.get("velocity",0.0)) for e in events]
        authored_timing_span=_curve_span(phrase.get("timing_curve_ms",[]))
        authored_dynamic_span=_curve_span(phrase.get("dynamic_curve",[]))
        realized_timing_span=(max(offsets)-min(offsets)) if offsets else 0.0
        realized_velocity_span=(max(velocities)-min(velocities)) if velocities else 0.0

        row={
            "phrase_id":phrase["phrase_id"],
            "role":role,
            "event_count":len(events),
            "authored_timing_span_ms":round(authored_timing_span,6),
            "realized_timing_span_ms":round(realized_timing_span,6),
            "authored_dynamic_span":round(authored_dynamic_span,6),
            "realized_velocity_span":round(realized_velocity_span,6),
        }
        evidence.append(row)

        if len(events)>=4:
            micro_bound=float(micro.get("max_abs_ms",0.0)) if micro.get("enabled",False) else 0.0
            if authored_timing_span < 1.0 and realized_timing_span < max(1.25,2.0*micro_bound+0.25):
                issues.append(_issue(
                    "MECHANICAL_TIMING","medium",
                    phrase_id=phrase["phrase_id"],role=role,
                    observed_ms=round(realized_timing_span,4),
                    message="Phrase timing is nearly invariant; timing evidence is mechanically flat."
                ))
            if authored_dynamic_span < 0.055 and realized_velocity_span < 0.065:
                issues.append(_issue(
                    "FLAT_DYNAMICS","medium",
                    phrase_id=phrase["phrase_id"],role=role,
                    observed=round(realized_velocity_span,4),
                    message="Phrase dynamics show little authored or realized motion."
                ))

        breath=float(phrase.get("breath_after_beats",0.0))
        if breath>0:
            body_end=float(phrase["start_beat"])+float(phrase["duration_beats"])
            breath_end=body_end+breath
            overlap=0.0
            offenders=0
            for e in events_by_role.get(role,[]):
                a,b=_interval(e)
                shared=_overlap(a,b,body_end,breath_end)
                if shared>EPS:
                    overlap+=shared
                    offenders+=1
            if overlap>0.01:
                issues.append(_issue(
                    "PHRASE_NO_BREATH","medium",
                    phrase_id=phrase["phrase_id"],role=role,
                    observed_beats=round(overlap,6),
                    offender_count=offenders,
                    message="Authored post-phrase breath is occupied by same-role note sustain/events."
                ))

    return issues,evidence


def _analyze_motif_identity(ir):
    issues=[]
    evidence=[]
    report=ir.get("motif_development_report",{})
    for stmt in report.get("statements",[]):
        ident=stmt.get("identity",{})
        score=float(ident.get("score",1.0))
        floor=float(stmt.get("identity_floor",0.0))
        margin=score-floor
        evidence.append({
            "statement_id":stmt.get("statement_id"),
            "identity_score":round(score,6),
            "identity_floor":round(floor,6),
            "margin":round(margin,6),
        })
        if score+1e-9 < floor:
            issues.append(_issue(
                "MOTIF_IDENTITY_LOSS","high",
                statement_id=stmt.get("statement_id"),
                observed=round(score,4),expected_min=round(floor,4),
                message="Realized motif statement falls below its Agent-authored identity floor."
            ))
    return issues,evidence


def _analyze_register(ir):
    report=analyze_register_collisions(ir)
    issues=[]
    for pair in report.get("pairs",[]):
        score=float(pair.get("collision_score",0.0))
        policies=pair.get("overlap_policies",{})
        restrictive=any(v in {"avoid","primary_wins","short_only"} for v in policies.values())
        if score > (0.18 if restrictive else 1.25):
            issues.append(_issue(
                "REGISTER_COLLISION",
                "high" if score>2.0 else "medium",
                section=pair.get("section_id"),
                roles=pair.get("roles"),
                observed=round(score,4),
                overlap_policies=deepcopy(policies),
                message="Sustained cross-role register overlap conflicts with register-space intent."
            ))
    return issues,report


def _analyze_orchestration_masking(ir,perf,events_by_role):
    issues=[]
    evidence=[]
    sections=perf.get("orchestration_sections",{})
    for sid,cfg in sections.items():
        primary=set(cfg.get("primary_roles",[]))
        subordinate=set(cfg.get("secondary_roles",[]))|set(cfg.get("decorative_roles",[]))
        allowed={tuple(sorted(x)) for x in cfg.get("allowed_overlaps",[]) if len(x)==2}
        interaction=cfg.get("ensemble_interaction",{})
        if not isinstance(interaction,dict) or not interaction.get("enabled",True):
            interaction={}
        interaction_leader=interaction.get("leader_role")
        yield_scales=interaction.get("overlap_velocity_scales",{})
        if not isinstance(yield_scales,dict):
            yield_scales={}
        if not primary or not subordinate:
            continue
        for p in sorted(primary):
            pevents=[e for e in events_by_role.get(p,[]) if e.get("section_id")==sid]
            primary_intervals=_merge_intervals([_interval(e) for e in pevents])
            primary_time=_interval_total(primary_intervals)
            if primary_time<=EPS:
                continue
            for s in sorted(subordinate):
                sevents=[e for e in events_by_role.get(s,[]) if e.get("section_id")==sid]
                subordinate_intervals=_merge_intervals([_interval(e) for e in sevents])
                shared=_interval_intersection_total(primary_intervals,subordinate_intervals)
                ratio=min(1.0,shared/max(primary_time,EPS))
                pair=tuple(sorted((p,s)))
                yield_scale=(
                    float(yield_scales[s])
                    if p==interaction_leader and s in yield_scales
                    else 1.0
                )
                dynamically_managed=yield_scale <= 0.92
                row={
                    "section_id":sid,"primary_role":p,"subordinate_role":s,
                    "shared_beats":round(shared,6),
                    "primary_active_beats":round(primary_time,6),
                    "overlap_ratio":round(ratio,6),
                    "explicitly_allowed":pair in allowed,
                    "ensemble_yield_scale":round(yield_scale,6),
                    "dynamically_managed":dynamically_managed,
                }
                evidence.append(row)
                if ratio>0.72 and pair not in allowed and not dynamically_managed:
                    issues.append(_issue(
                        "ORCHESTRATION_MASKING",
                        "medium",
                        section=sid,roles=[p,s],observed=round(ratio,4),
                        message="A subordinate role occupies most of the primary role body without an authored overlap preference."
                    ))
    return issues,evidence


def _analyze_transition_discontinuity(perf,section_analysis):
    issues=[]
    evidence=[]
    transitions=(section_analysis or {}).get("transitions",{})
    for t in perf.get("transitions",[]):
        dest=t.get("to_section")
        metric=transitions.get(dest)
        if not metric:
            continue
        d=float(metric.get("discontinuity",0.0))
        evidence.append({
            "from_section":t.get("from_section"),
            "to_section":dest,
            "discontinuity":round(d,6),
            "direction":metric.get("direction"),
        })
        # Explicit silence may intentionally create a hard edge. Do not call it a defect
        # unless the discontinuity remains extreme.
        threshold=.72 if float(t.get("silence_beats",0.0))>0 else .58
        if d>threshold:
            issues.append(_issue(
                "TRANSITION_DISCONTINUITY",
                "medium",
                from_section=t.get("from_section"),to_section=dest,
                observed=round(d,4),
                message="Rendered transition remains abruptly discontinuous relative to the authored transition plan."
            ))
    return issues,evidence


def analyze_expressive_qa(resolved_ir: dict, section_analysis: dict | None=None) -> dict:
    """Evidence-only QA for v1.16 expressive composition.

    This function never mutates plans or events. It measures the resolved result so
    the Composer Agent can decide whether and how to revise structured intent.
    """
    perf=resolved_ir.get("performance_ir")
    if not isinstance(perf,dict):
        return {"issue_count":0,"issues":[],"evidence":{},"semantics":"no performance_ir"}

    events_by_role=_events_by_role(resolved_ir)
    issues=[]
    phrase_issues,phrase_ev=_analyze_phrase_expression(resolved_ir,perf,events_by_role)
    motif_issues,motif_ev=_analyze_motif_identity(resolved_ir)
    register_issues,register_ev=_analyze_register(resolved_ir)
    orch_issues,orch_ev=_analyze_orchestration_masking(resolved_ir,perf,events_by_role)
    transition_issues,transition_ev=_analyze_transition_discontinuity(perf,section_analysis)

    for group in (phrase_issues,motif_issues,register_issues,orch_issues,transition_issues):
        issues.extend(group)

    severity_order={"high":0,"medium":1,"low":2}
    issues.sort(key=lambda x:(severity_order.get(x.get("severity","low"),9),x["code"],str(x.get("section","")),str(x.get("phrase_id",""))))
    counts=defaultdict(int)
    for issue in issues:
        counts[issue["code"]]+=1

    return {
        "issue_count":len(issues),
        "issue_counts":dict(sorted(counts.items())),
        "issues":issues,
        "evidence":{
            "phrases":phrase_ev,
            "motif_identity":motif_ev,
            "register_collisions":register_ev,
            "orchestration_masking":orch_ev,
            "transition_discontinuity":transition_ev,
            "ensemble_interaction":deepcopy(resolved_ir.get("ensemble_interaction_report",{})),
        },
        "semantics":{
            "role":"measurement only; no automatic musical rewrite",
            "codes":[
                "MECHANICAL_TIMING","FLAT_DYNAMICS","MOTIF_IDENTITY_LOSS",
                "REGISTER_COLLISION","ORCHESTRATION_MASKING",
                "TRANSITION_DISCONTINUITY","PHRASE_NO_BREATH",
            ],
        },
    }


def compare_expressive_qa(before: dict, after: dict, target_codes: list[str] | tuple[str,...] | None=None) -> dict:
    """Compare evidence across an Agent-authored revision.

    Target improvement is necessary but not sufficient. A revision is only accepted as
    `improved` when it also introduces no new non-target HIGH/MEDIUM issues.
    """
    explicit_targets=bool(target_codes)
    targets=set(target_codes or [])
    if not targets:
        targets={i.get("code") for i in before.get("issues",[])}|{i.get("code") for i in after.get("issues",[])}
        targets.discard(None)

    def code_counts(report, allowed=None):
        out=defaultdict(int)
        for issue in report.get("issues",[]):
            code=issue.get("code")
            if code is None or (allowed is not None and code not in allowed):
                continue
            out[code]+=1
        return dict(out)

    def fingerprint(issue):
        roles=issue.get("roles")
        if isinstance(roles,list):
            roles=tuple(roles)
        return (
            issue.get("code"), issue.get("severity","low"),
            issue.get("section"), issue.get("phrase_id"), issue.get("statement_id"),
            issue.get("from_section"), issue.get("to_section"), roles,
        )

    b=code_counts(before,targets); a=code_counts(after,targets)
    rows=[]
    for code in sorted(targets):
        bv=b.get(code,0); av=a.get(code,0)
        rows.append({"code":code,"before":bv,"after":av,"delta":av-bv})
    target_before=sum(x["before"] for x in rows)
    target_after=sum(x["after"] for x in rows)
    target_improved=target_after < target_before

    before_fp={fingerprint(i) for i in before.get("issues",[])}
    introduced=[]
    for issue in after.get("issues",[]):
        if fingerprint(issue) in before_fp:
            continue
        if explicit_targets and issue.get("code") in targets:
            continue
        introduced.append(deepcopy(issue))
    introduced_high_medium=[i for i in introduced if i.get("severity","low") in {"high","medium"}]
    regression_free=not introduced_high_medium

    return {
        "targets":sorted(targets),
        "before_issue_count":target_before,
        "after_issue_count":target_after,
        "resolved_count":sum(max(0,x["before"]-x["after"]) for x in rows),
        "introduced_count":sum(max(0,x["after"]-x["before"]) for x in rows),
        "by_code":rows,
        "target_improved":target_improved,
        "global_before_issue_count":len(before.get("issues",[])),
        "global_after_issue_count":len(after.get("issues",[])),
        "introduced_non_target":introduced,
        "introduced_non_target_count":len(introduced),
        "introduced_high_medium":introduced_high_medium,
        "introduced_high_medium_count":len(introduced_high_medium),
        "regression_free":regression_free,
        "improved":bool(target_improved and regression_free),
    }


__all__=["analyze_expressive_qa","compare_expressive_qa"]
