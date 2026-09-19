from copy import deepcopy

import pytest

from code_composer.agent.expressive_score_plan import (
    ExpressivePlanValidationError,
    ExpressiveValidationContext,
    expressive_score_plan_from_dict,
)
from code_composer.agent.performance_ir import compile_performance_ir
from code_composer.composition.performance import attach_performance_ir, realize_performance_ir


def _base_ir():
    events=[]
    pitches=[60,62,64,65,64,62,61,60,67]
    starts=[0,.5,1,1.5,2,2.5,3,3.5,4.25]  # final event sits in authored breath
    for s,m in zip(starts,pitches):
        events.append({
            "start_beat":s,
            "duration_beats":.42,
            "midi":m,
            "velocity":.55,
            "section_id":"one",
            "arrangement_role":"lead",
        })
    return {
        "transport":{"bpm":84,"beats_per_bar":4},
        "form":[{"id":"one","start_bar":0,"bars":2,"energy":.7}],
        "materials":{"motifs":{"main":{"intervals":[0,1,2,3,2,1,0,0],"rhythm":[.5]*8}}},
        "tracks":[{
            "id":"lead","instrument":"lead","source":{"type":"resolved"},"events":events,
        }],
    }


def _context():
    return ExpressiveValidationContext(
        section_ids=("one",),
        role_ids=("lead",),
        source_material_ids=("main",),
        section_spans={"one":(0.0,8.0)},
    )


def _plan(kind):
    if kind=="lyrical":
        dyn=[[0,.38],[.55,.78],[1,.42]]
        timing=[[0,0],[.55,3.0],[1,10.0]]
        gate=[[0,.90],[.55,1.15],[1,.82]]
        art=[
            {"position":0,"articulation":"tenuto"},
            {"position":.45,"articulation":"legato"},
            {"position":.88,"articulation":"tenuto"},
        ]
        accents=[{"position":.55,"amount":.08}]
    elif kind=="whispered":
        dyn=[[0,.28],[.50,.46],[1,.24]]
        timing=[[0,5.0],[.6,10.0],[1,15.0]]
        gate=[[0,.68],[.5,.78],[1,.58]]
        art=[
            {"position":0,"articulation":"neutral"},
            {"position":.55,"articulation":"staccato"},
            {"position":.9,"articulation":"tenuto"},
        ]
        accents=[]
    else:
        dyn=[[0,.62],[.42,.90],[1,.58]]
        timing=[[0,-6.0],[.5,-2.0],[1,2.0]]
        gate=[[0,.76],[.42,.88],[1,.72]]
        art=[
            {"position":0,"articulation":"accent"},
            {"position":.42,"articulation":"marcato"},
            {"position":.82,"articulation":"accent"},
        ]
        accents=[{"position":.42,"amount":.06}]

    return {
        "version":"1.16",
        "narrative":{"arc":f"{kind} phrase realization"},
        "phrases":[{
            "phrase_id":f"phrase_{kind}",
            "section_id":"one",
            "role":"lead",
            "source_material":"main",
            "start_beat":0.0,
            "duration_beats":4.0,
            "dynamic_curve":dyn,
            "timing_curve_ms":timing,
            "gate_curve":gate,
            "articulation_curve":art,
            "accent_points":accents,
            "apex_position":.5,
            "breath_after_beats":.5,
        }],
        "motif_statements":[],
        "register_plans":{
            "lead":{
                "hard_range":[48,84],
                "preferred_range":[55,76],
                "center":64,
                "max_span":24,
                "min_intervoice_distance":0,
                "overlap_policy":"allow",
                "motion_policy":"smooth",
            }
        },
        "orchestration_sections":{
            "one":{
                "primary_roles":["lead"],
                "secondary_roles":[],
                "decorative_roles":[],
                "max_simultaneous_roles":1,
                "allowed_overlaps":[],
                "phrase_gap_only_roles":[],
                "silence_roles":[],
            }
        },
        "transitions":[],
    }


def _realized(kind,seed=123):
    plan=expressive_score_plan_from_dict(_plan(kind))
    perf=compile_performance_ir(
        plan,_context(),seed=seed,
        realization={
            "microtiming":{"enabled":True,"max_abs_ms":2.5},
            "velocity_variation":{"enabled":True,"max_abs":.012},
            "timing_quantization_guard_ms":0.0,
            "minimum_note_gap_ms":1.0,
        },
    )
    ir=attach_performance_ir(_base_ir(),perf)
    return realize_performance_ir(ir)


def _lead_events(ir):
    return ir["tracks"][0]["events"]


def test_same_pitch_identity_three_distinct_phrase_realizations():
    outs=[_realized(k) for k in ("lyrical","whispered","urgent")]
    pitches=[[e["midi"] for e in _lead_events(x)] for x in outs]
    assert pitches[0]==pitches[1]==pitches[2]
    assert pitches[0]==[60,62,64,65,64,62,61,60]  # breath removed trailing event

    velocities=[[e["velocity"] for e in _lead_events(x)] for x in outs]
    starts=[[e["start_beat"] for e in _lead_events(x)] for x in outs]
    durations=[[e["duration_beats"] for e in _lead_events(x)] for x in outs]
    assert len({tuple(x) for x in velocities})==3
    assert len({tuple(x) for x in starts})==3
    assert len({tuple(x) for x in durations})==3


def test_same_plan_and_seed_is_exactly_deterministic():
    a=_realized("lyrical",260916)
    b=_realized("lyrical",260916)
    assert a==b


def test_different_seed_changes_only_bounded_micro_variation_not_pitch_identity():
    a=_realized("lyrical",1)
    b=_realized("lyrical",2)
    ea=_lead_events(a); eb=_lead_events(b)
    assert [e["midi"] for e in ea]==[e["midi"] for e in eb]
    assert [e["start_beat"] for e in ea] != [e["start_beat"] for e in eb]
    assert [e["velocity"] for e in ea] != [e["velocity"] for e in eb]
    assert [e["performance"]["dynamic_target"] for e in ea] == [
        e["performance"]["dynamic_target"] for e in eb
    ]


def test_performance_metadata_preserves_base_and_authored_evidence():
    out=_realized("lyrical",7)
    ev=_lead_events(out)[3]
    p=ev["performance"]
    assert p["phrase_id"]=="phrase_lyrical"
    assert p["base_velocity"]==.55
    assert p["base_duration_beats"]==.42
    assert "dynamic_target" in p
    assert "authored_timing_ms" in p
    assert "microtiming_ms" in p
    assert "gate_multiplier" in p
    assert p["articulation"] in {"tenuto","legato"}


def test_breath_removes_role_events_after_phrase_body():
    out=_realized("whispered")
    assert all(e["start_beat"] < 4.0 for e in _lead_events(out))
    report=out["performance_report"]["phrases"][0]
    assert report["removed_for_breath"]==1


def test_overlapping_phrase_or_authored_breath_is_rejected():
    data=_plan("lyrical")
    second=deepcopy(data["phrases"][0])
    second["phrase_id"]="phrase_second"
    second["start_beat"]=4.25
    second["duration_beats"]=2.0
    second["breath_after_beats"]=0.0
    data["phrases"].append(second)
    plan=expressive_score_plan_from_dict(data)
    with pytest.raises(ExpressivePlanValidationError):
        compile_performance_ir(plan,_context(),seed=1)


def test_disabled_microvariation_uses_authored_curves_exactly():
    plan=expressive_score_plan_from_dict(_plan("lyrical"))
    perf=compile_performance_ir(
        plan,_context(),seed=999,
        realization={
            "microtiming":{"enabled":False,"max_abs_ms":0.0},
            "velocity_variation":{"enabled":False,"max_abs":0.0},
            "timing_quantization_guard_ms":0.0,
        },
    )
    out=realize_performance_ir(attach_performance_ir(_base_ir(),perf))
    events=_lead_events(out)
    assert events[0]["velocity"]==pytest.approx(.38)
    assert events[0]["start_beat"]==pytest.approx(0.0)
    assert events[0]["duration_beats"]==pytest.approx(.42*.90*1.0)
    mid=events[4]
    assert mid["performance"]["articulation"]=="legato"
    assert mid["performance"]["accent_amount"]==pytest.approx(.08)


def test_realization_is_idempotent():
    once=_realized("urgent")
    twice=realize_performance_ir(once)
    assert twice==once
