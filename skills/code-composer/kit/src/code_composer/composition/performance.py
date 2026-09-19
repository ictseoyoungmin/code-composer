from __future__ import annotations

from copy import deepcopy
import random

from ..agent.expressive_score_plan import (
    ExpressiveValidationContext,
    build_validation_context_from_composition,
)
from .motif_development import (
    MotifDevelopmentError,
    realize_motif_statements,
    validate_motif_development_contract,
)
from .musical_transitions import (
    MusicalTransitionError,
    realize_musical_transitions,
    validate_musical_transition_contract,
)
from .register_voicing import (
    RegisterVoicingError,
    realize_register_and_voicing,
    validate_register_voicing_contract,
)
from .orchestration_budget import (
    OrchestrationBudgetError,
    realize_orchestration_budget,
    validate_orchestration_budget_contract,
)
from .ensemble_interaction import (
    EnsembleInteractionError,
    realize_ensemble_interaction,
    validate_ensemble_interaction_contract,
)

from ..agent.performance_ir import (
    PerformanceIR,
    PerformanceIRValidationError,
    performance_ir_from_dict,
    performance_ir_to_dict,
    validate_performance_ir,
)


ARTICULATION_GATE = {
    "legato": 1.08,
    "tenuto": 1.00,
    "neutral": 0.88,
    "staccato": 0.52,
    "accent": 0.82,
    "marcato": 0.68,
    "pizzicato": 0.42,
    "harmonic": 0.94,
    "spiccato": 0.34,
}

ARTICULATION_VELOCITY = {
    "legato": 0.00,
    "tenuto": 0.00,
    "neutral": 0.00,
    "staccato": -0.01,
    "accent": 0.07,
    "marcato": 0.11,
    "pizzicato": 0.03,
    "harmonic": -0.02,
    "spiccato": 0.05,
}


def _stable_rng(seed: int, namespace: str) -> random.Random:
    x = int(seed) & 0xFFFFFFFF
    for ch in namespace.encode("utf-8"):
        x = ((x * 1664525) + ch + 1013904223) & 0xFFFFFFFF
    return random.Random(x)


def _interp_curve(points, position: float) -> float:
    p = max(0.0, min(1.0, float(position)))
    if p <= float(points[0][0]):
        return float(points[0][1])
    if p >= float(points[-1][0]):
        return float(points[-1][1])
    for (x0,y0),(x1,y1) in zip(points,points[1:]):
        x0=float(x0); x1=float(x1)
        if x0 <= p <= x1:
            if x1 <= x0:
                return float(y1)
            u=(p-x0)/(x1-x0)
            return float(y0)+(float(y1)-float(y0))*u
    return float(points[-1][1])


def _articulation_at(points, position: float) -> str:
    p=max(0.0,min(1.0,float(position)))
    current=points[0]["articulation"]
    for item in points:
        if float(item["position"]) <= p + 1e-12:
            current=item["articulation"]
        else:
            break
    return current


def _role_ids_from_ir(ir: dict) -> tuple[str,...]:
    roles=ir.get("arrangement",{}).get("roles",{})
    if isinstance(roles,dict) and roles:
        return tuple(roles.keys())
    return tuple(t.get("id") for t in ir.get("tracks",[]) if t.get("id"))


def performance_context_from_ir(ir: dict) -> ExpressiveValidationContext:
    beats_per_bar=float(ir.get("transport",{}).get("beats_per_bar",4.0))
    materials=ir.get("materials",{}).get("motifs",{})
    return build_validation_context_from_composition(
        form=ir.get("form",[]),
        role_ids=_role_ids_from_ir(ir),
        source_material_ids=tuple(materials.keys()),
        beats_per_bar=beats_per_bar,
    )


def validate_ir_performance_contract(ir: dict) -> None:
    raw=ir.get("performance_ir")
    if raw is None:
        return
    try:
        perf=raw if isinstance(raw,PerformanceIR) else performance_ir_from_dict(raw)
        validate_performance_ir(perf,performance_context_from_ir(ir))
        validate_motif_development_contract(ir,perf)
        validate_musical_transition_contract(ir,perf)
        validate_register_voicing_contract(ir,perf)
        validate_orchestration_budget_contract(ir,perf)
        validate_ensemble_interaction_contract(ir,perf)
    except (PerformanceIRValidationError,MotifDevelopmentError,MusicalTransitionError,RegisterVoicingError,OrchestrationBudgetError,EnsembleInteractionError):
        raise
    except Exception as exc:
        raise PerformanceIRValidationError(str(exc)) from exc


def attach_performance_ir(ir: dict, performance_ir: PerformanceIR | dict) -> dict:
    out=deepcopy(ir)
    perf=(
        performance_ir
        if isinstance(performance_ir,PerformanceIR)
        else performance_ir_from_dict(performance_ir)
    )
    validate_performance_ir(perf,performance_context_from_ir(out))
    validate_motif_development_contract(out,perf)
    validate_musical_transition_contract(out,perf)
    validate_register_voicing_contract(out,perf)
    validate_orchestration_budget_contract(out,perf)
    validate_ensemble_interaction_contract(out,perf)
    out["performance_ir"]=performance_ir_to_dict(perf)
    for key in (
        "performance_resolved","performance_report",
        "motif_development_resolved","motif_development_report",
        "musical_transitions_resolved","musical_transition_report",
        "register_voicing_resolved","register_voicing_report",
        "orchestration_budget_resolved","orchestration_budget_report",
        "ensemble_interaction_resolved","ensemble_interaction_report",
    ):
        out.pop(key,None)
    return out


def _phrase_schedule_check(phrases) -> None:
    by_role={}
    for phrase in phrases:
        by_role.setdefault(phrase["role"],[]).append(phrase)
    for role,items in by_role.items():
        items=sorted(items,key=lambda p:(float(p["start_beat"]),p["phrase_id"]))
        for a,b in zip(items,items[1:]):
            a_end=(
                float(a["start_beat"])
                + float(a["duration_beats"])
                + float(a.get("breath_after_beats",0.0))
            )
            if a_end > float(b["start_beat"]) + 1e-9:
                raise PerformanceIRValidationError(
                    f"phrases for role {role} overlap authored breath: "
                    f"{a['phrase_id']} -> {b['phrase_id']}"
                )


def _accent_by_onset(phrase: dict, onset_beats: list[float]) -> dict[float,float]:
    if not onset_beats:
        return {}
    start=float(phrase["start_beat"])
    duration=float(phrase["duration_beats"])
    assigned={x:0.0 for x in onset_beats}
    for accent in phrase.get("accent_points",[]):
        target=start+float(accent["position"])*duration
        onset=min(onset_beats,key=lambda x:(abs(x-target),x))
        assigned[onset]+=float(accent["amount"])
    return assigned


def _realize_phrase_on_track(
    events: list[dict],
    phrase: dict,
    realization: dict,
    bpm: float,
) -> tuple[list[dict],dict]:
    start=float(phrase["start_beat"])
    duration=float(phrase["duration_beats"])
    end=start+duration
    breath=float(phrase.get("breath_after_beats",0.0))
    breath_end=end+breath

    inside=[
        e for e in events
        if start-1e-9 <= float(e.get("start_beat",-1)) < end-1e-9
    ]
    onset_values=sorted({round(float(e["start_beat"]),9) for e in inside})
    accent_map=_accent_by_onset(phrase,onset_values)

    micro_cfg=realization["microtiming"]
    vel_cfg=realization["velocity_variation"]
    seed=int(realization["seed"])
    max_micro=float(micro_cfg["max_abs_ms"]) if micro_cfg["enabled"] else 0.0
    max_vel=float(vel_cfg["max_abs"]) if vel_cfg["enabled"] else 0.0
    guard=float(realization.get("timing_quantization_guard_ms",0.0))
    min_gap_ms=float(realization.get("minimum_note_gap_ms",0.0))
    beat_ms=60000.0/float(bpm)

    onset_offsets={}
    previous_new=None
    for onset_index,onset in enumerate(onset_values):
        position=max(0.0,min(1.0,(onset-start)/max(duration,1e-12)))
        authored_ms=_interp_curve(phrase["timing_curve_ms"],position)
        rng=_stable_rng(seed,f"phrase:{phrase['phrase_id']}:onset:{onset_index}")
        micro_ms=(rng.random()*2.0-1.0)*max_micro if max_micro>0 else 0.0
        total_ms=authored_ms+micro_ms
        if abs(total_ms)<guard:
            total_ms=0.0
        new_onset=onset+total_ms/beat_ms
        new_onset=max(0.0,start,new_onset)
        if previous_new is not None and onset > onset_values[onset_index-1]+1e-9:
            minimum=previous_new+min_gap_ms/beat_ms
            if new_onset < minimum:
                new_onset=minimum
                total_ms=(new_onset-onset)*beat_ms
        # An onset authored inside the phrase may not be pushed beyond its phrase body.
        new_onset=min(new_onset,max(start,end-1e-6))
        onset_offsets[onset]=(new_onset,total_ms,authored_ms,micro_ms)
        previous_new=new_onset

    output=[]
    transformed=0
    removed_for_breath=0
    for event_index,e in enumerate(events):
        old_start=float(e.get("start_beat",-1))
        # E5 transition material is already explicitly authored. It must not be
        # re-shaped by an adjacent E1 phrase envelope or deleted by phrase breath.
        if isinstance(e.get("musical_transition"),dict):
            output.append(dict(e))
            continue
        if end-1e-9 <= old_start < breath_end-1e-9:
            removed_for_breath+=1
            continue
        if not (start-1e-9 <= old_start < end-1e-9):
            output.append(dict(e))
            continue

        onset_key=round(old_start,9)
        new_start,total_ms,authored_ms,micro_ms=onset_offsets[onset_key]
        position=max(0.0,min(1.0,(old_start-start)/max(duration,1e-12)))
        articulation=_articulation_at(phrase["articulation_curve"],position)
        dynamic_target=_interp_curve(phrase["dynamic_curve"],position)
        gate_target=_interp_curve(phrase["gate_curve"],position)
        accent=float(accent_map.get(onset_key,0.0))

        vrng=_stable_rng(
            seed,
            f"phrase:{phrase['phrase_id']}:velocity:{event_index}:{e.get('midi','drum')}"
        )
        vel_micro=(vrng.random()*2.0-1.0)*max_vel if max_vel>0 else 0.0
        final_velocity=(
            dynamic_target
            + accent
            + ARTICULATION_VELOCITY[articulation]
            + vel_micro
        )
        final_velocity=max(0.01,min(1.0,final_velocity))

        gate_multiplier=gate_target*ARTICULATION_GATE[articulation]
        old_duration=float(e.get("duration_beats",0.0))
        final_duration=max(1e-5,old_duration*gate_multiplier)
        # `breath_after` means actual silence after the phrase body.
        final_duration=min(final_duration,max(1e-5,end-new_start))

        x=dict(e)
        x["start_beat"]=round(new_start,9)
        x["duration_beats"]=round(final_duration,9)
        x["velocity"]=round(final_velocity,6)
        existing_performance=(x.get("performance",{}) if isinstance(x.get("performance"),dict) else {})
        existing_expression=(
            existing_performance.get("instrument_expression",{})
            if isinstance(existing_performance.get("instrument_expression"),dict)
            else {}
        )
        phrase_expression={}
        for control,points in phrase.get("instrument_expression_curves",{}).items():
            phrase_expression[control]=round(_interp_curve(points,position),6)
        # Event-local expression is the most specific authoring surface and wins
        # over the phrase envelope. The phrase envelope fills only missing controls.
        merged_expression={**phrase_expression,**existing_expression}

        x["performance"]={
            **existing_performance,
            "phrase_id":phrase["phrase_id"],
            "phrase_position":round(position,6),
            "base_start_beat":round(old_start,9),
            "base_duration_beats":round(old_duration,9),
            "base_velocity":round(float(e.get("velocity",0.8)),6),
            "dynamic_target":round(dynamic_target,6),
            "accent_amount":round(accent,6),
            "articulation":articulation,
            "gate_curve":round(gate_target,6),
            "gate_multiplier":round(gate_multiplier,6),
            "authored_timing_ms":round(authored_ms,6),
            "microtiming_ms":round(micro_ms,6),
            "timing_offset_ms":round(total_ms,6),
            "velocity_microvariation":round(vel_micro,6),
        }
        if merged_expression:
            x["performance"]["instrument_expression"]=merged_expression
        if phrase_expression:
            x["performance"]["phrase_instrument_expression"]=phrase_expression
        output.append(x)
        transformed+=1

    output.sort(key=lambda e:(float(e.get("start_beat",0.0)),int(e.get("midi",0))))
    report={
        "phrase_id":phrase["phrase_id"],
        "role":phrase["role"],
        "event_count":transformed,
        "removed_for_breath":removed_for_breath,
        "start_beat":start,
        "duration_beats":duration,
        "breath_after_beats":breath,
    }
    if phrase.get("instrument_expression_curves"):
        report["instrument_expression_controls"]=sorted(phrase["instrument_expression_curves"])
    return output,report


def realize_performance_ir(ir: dict) -> dict:
    if "performance_ir" not in ir:
        return deepcopy(ir)
    if ir.get("performance_resolved"):
        return deepcopy(ir)

    out=realize_motif_statements(ir)
    out=realize_musical_transitions(out)
    out=realize_register_and_voicing(out)
    out=realize_orchestration_budget(out)
    perf=performance_ir_from_dict(out["performance_ir"])
    validate_performance_ir(perf,performance_context_from_ir(out))
    _phrase_schedule_check(perf.phrases)

    bpm=float(out["transport"]["bpm"])
    report=[]
    phrases_by_role={}
    for phrase in perf.phrases:
        phrases_by_role.setdefault(phrase["role"],[]).append(phrase)

    for track in out.get("tracks",[]):
        role=track.get("id")
        phrases=sorted(
            phrases_by_role.get(role,[]),
            key=lambda p:(float(p["start_beat"]),p["phrase_id"]),
        )
        if not phrases:
            continue
        events=[dict(e) for e in track.get("events",[])]
        for phrase in phrases:
            events,phrase_report=_realize_phrase_on_track(
                events,phrase,perf.realization,bpm
            )
            report.append(phrase_report)
        track["events"]=events

    out["performance_resolved"]=True
    out["performance_report"]={
        "phrase_count":len(perf.phrases),
        "phrases":report,
        "realization":deepcopy(perf.realization),
    }
    out=realize_ensemble_interaction(out)
    return out


__all__=[
    "ARTICULATION_GATE","ARTICULATION_VELOCITY",
    "performance_context_from_ir","validate_ir_performance_contract",
    "attach_performance_ir","realize_performance_ir",
]
