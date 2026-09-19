from copy import deepcopy

import pytest

from code_composer.composition.orchestration_budget import (
    OrchestrationBudgetError,
    realize_orchestration_budget,
    validate_orchestration_budget_contract,
)


def _plan(active=("lead","pad","bass","arp","drums"), budget=3, gaps=("arp",), silence=()):
    primary=["lead"] if "lead" in active else []
    secondary=[r for r in ("pad","bass") if r in active]
    decorative=[r for r in ("arp","drums") if r in active]
    return {
        "primary_roles":primary,
        "secondary_roles":secondary,
        "decorative_roles":decorative,
        "max_simultaneous_roles":budget,
        "allowed_overlaps":[["lead","pad"]] if "lead" in active and "pad" in active else [],
        "phrase_gap_only_roles":[r for r in gaps if r in decorative],
        "silence_roles":list(silence),
    }


def _perf(cfg):
    active=set(cfg["primary_roles"]+cfg["secondary_roles"]+cfg["decorative_roles"]+cfg["silence_roles"])
    return {
        "version":"1.16",
        "phrases":[{
            "phrase_id":"lead_phrase","section_id":"one","role":"lead","source_material":"main",
            "start_beat":0.0,"duration_beats":4.0,
            "dynamic_curve":[[0,.5],[1,.5]],"timing_curve_ms":[[0,0],[1,0]],
            "gate_curve":[[0,1],[1,1]],
            "articulation_curve":[{"position":0,"articulation":"neutral"}],
            "accent_points":[],"breath_after_beats":0.0,
        }] if "lead" in active else [],
        "motif_statements":[],
        "register_plans":{
            r:{
                "hard_range":[24,108],"preferred_range":[36,96],"center":66,
                "max_span":48,"min_intervoice_distance":0,
                "overlap_policy":"allow","motion_policy":"free",
            } for r in active if r not in {"drums"}
        },
        "orchestration_sections":{"one":cfg},
        "transitions":[],
        "realization":{
            "seed":1,
            "microtiming":{"enabled":False,"max_abs_ms":0.0},
            "velocity_variation":{"enabled":False,"max_abs":0.0},
            "timing_quantization_guard_ms":0.0,
            "minimum_note_gap_ms":0.0,
        },
    }


def _ir(cfg, tracks):
    return {
        "transport":{"bpm":100,"beats_per_bar":4},
        "form":[{"id":"one","start_bar":0,"bars":2,"energy":1.0}],
        "materials":{"motifs":{"main":{"intervals":[0],"rhythm":[1.0]}}},
        "performance_ir":_perf(cfg),
        "tracks":tracks,
    }


def _event(start,dur,midi=60,role=None,**extra):
    x={"start_beat":start,"duration_beats":dur,"midi":midi,"velocity":.5,"section_id":"one"}
    if role: x["arrangement_role"]=role
    x.update(extra)
    return x


def test_silence_role_is_hard_gate_even_for_transition_material():
    cfg=_plan(active=("lead",),budget=1,silence=("drums",))
    tracks=[
        {"id":"lead","events":[_event(0,1,60)]},
        {"id":"drums","events":[{
            "event_type":"drum","drum":"snare","start_beat":3.75,"duration_beats":.1,
            "velocity":.7,"section_id":"one","arrangement_role":"drums",
            "transition_material":"drum_pickup",
        }]},
    ]
    out=realize_orchestration_budget(_ir(cfg,tracks))
    drums=next(t for t in out["tracks"] if t["id"]=="drums")
    assert drums["events"]==[]
    assert out["orchestration_budget_report"]["sections"]["one"]["removed"]["silence_role"]==1


def test_phrase_gap_only_decorative_role_is_removed_during_primary_phrase_only():
    cfg=_plan(active=("lead","arp"),budget=2,gaps=("arp",))
    tracks=[
        {"id":"lead","events":[_event(0,4,64)]},
        {"id":"arp","events":[
            _event(.5,.25,76),_event(2.0,.25,79),_event(4.25,.25,81),_event(5.0,.25,83)
        ]},
    ]
    out=realize_orchestration_budget(_ir(cfg,tracks))
    arp=next(t for t in out["tracks"] if t["id"]=="arp")
    assert [e["start_beat"] for e in arp["events"]]==[4.25,5.0]
    rep=out["orchestration_budget_report"]["sections"]["one"]
    assert rep["removed"]["primary_phrase_overlap"]==2


def test_max_simultaneous_roles_preserves_authored_priority():
    cfg=_plan(active=("lead","pad","bass","arp"),budget=2,gaps=())
    tracks=[
        {"id":"lead","events":[_event(0,2,64)]},
        {"id":"pad","events":[_event(0,2,52)]},
        {"id":"bass","events":[_event(0,2,40)]},
        {"id":"arp","events":[_event(0,1,76)]},
    ]
    out=realize_orchestration_budget(_ir(cfg,tracks))
    kept={t["id"] for t in out["tracks"] if t["events"]}
    # lead is primary. pad and bass are both secondary, but lead/pad is authored as a protected overlap.
    assert kept=={"lead","pad"}
    rep=out["orchestration_budget_report"]["sections"]["one"]
    assert rep["removed"]["simultaneous_role_budget"]==2


def test_primary_count_cannot_exceed_simultaneous_budget():
    cfg={
        "primary_roles":["lead","pad"],"secondary_roles":[],"decorative_roles":[],
        "max_simultaneous_roles":1,"allowed_overlaps":[["lead","pad"]],
        "phrase_gap_only_roles":[],"silence_roles":[],
    }
    ir=_ir(cfg,[{"id":"lead","events":[]},{"id":"pad","events":[]}])
    with pytest.raises(OrchestrationBudgetError):
        validate_orchestration_budget_contract(ir,ir["performance_ir"])


def test_allowed_overlap_pair_must_reference_active_roles():
    cfg=_plan(active=("lead","pad"),budget=2,gaps=())
    cfg["allowed_overlaps"]=[["lead","bass"]]
    ir=_ir(cfg,[{"id":"lead","events":[]},{"id":"pad","events":[]}])
    with pytest.raises(OrchestrationBudgetError):
        validate_orchestration_budget_contract(ir,ir["performance_ir"])


def test_budget_realization_is_deterministic_and_idempotent():
    cfg=_plan(active=("lead","pad","bass","arp"),budget=2,gaps=())
    tracks=[
        {"id":"lead","events":[_event(0,2,64)]},
        {"id":"pad","events":[_event(0,2,52)]},
        {"id":"bass","events":[_event(0,2,40)]},
        {"id":"arp","events":[_event(0,1,76)]},
    ]
    ir=_ir(cfg,tracks)
    a=realize_orchestration_budget(ir)
    b=realize_orchestration_budget(ir)
    assert a==b
    assert realize_orchestration_budget(a)==a


def test_sustain_is_truncated_at_boundary_of_section_where_role_becomes_silent():
    perf={
        "version":"1.16","phrases":[],"motif_statements":[],"register_plans":{},
        "orchestration_sections":{
            "a":{"primary_roles":["pad"],"secondary_roles":[],"decorative_roles":[],"max_simultaneous_roles":1,"allowed_overlaps":[],"phrase_gap_only_roles":[],"silence_roles":[]},
            "b":{"primary_roles":["lead"],"secondary_roles":[],"decorative_roles":[],"max_simultaneous_roles":1,"allowed_overlaps":[],"phrase_gap_only_roles":[],"silence_roles":["pad"]},
        },
        "transitions":[],"realization":{"seed":1,"microtiming":{"enabled":False,"max_abs_ms":0.0},"velocity_variation":{"enabled":False,"max_abs":0.0},"timing_quantization_guard_ms":0.0,"minimum_note_gap_ms":0.0},
    }
    ir={
        "transport":{"bpm":100,"beats_per_bar":4},
        "form":[{"id":"a","start_bar":0,"bars":1},{"id":"b","start_bar":1,"bars":1}],
        "performance_ir":perf,
        "tracks":[
            {"id":"pad","events":[{"start_beat":3.0,"duration_beats":2.0,"midi":52,"velocity":.5,"section_id":"a"}]},
            {"id":"lead","events":[{"start_beat":4.0,"duration_beats":1.0,"midi":64,"velocity":.6,"section_id":"b"}]},
        ],
    }
    out=realize_orchestration_budget(ir)
    pad=next(t for t in out["tracks"] if t["id"]=="pad")
    assert len(pad["events"])==1
    assert pad["events"][0]["duration_beats"]==pytest.approx(1.0)
    assert pad["events"][0]["orchestration_budget"]["truncated_for_silence_at"]==pytest.approx(4.0)
