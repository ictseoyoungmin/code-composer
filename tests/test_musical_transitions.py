from copy import deepcopy

import pytest

from code_composer.composition.musical_transitions import (
    MusicalTransitionError,
    realize_musical_transitions,
)
from code_composer.composition.performance import realize_performance_ir


def _register_plan(lo,hi,center):
    return {
        "hard_range":[lo,hi],"preferred_range":[lo,hi],"center":center,
        "max_span":max(12,hi-lo),"min_intervoice_distance":0,
        "overlap_policy":"allow","motion_policy":"smooth",
    }


def _perf(transitions):
    sections={}
    for sid in ("a","b","c"):
        sections[sid]={
            "primary_roles":["lead"],"secondary_roles":["pad","bass"],
            "decorative_roles":["drums"],"max_simultaneous_roles":4,
            "allowed_overlaps":[["lead","pad"]],"phrase_gap_only_roles":[],"silence_roles":[],
        }
    return {
        "version":"1.16","phrases":[],"motif_statements":[],
        "register_plans":{
            "lead":_register_plan(48,84,66),
            "pad":_register_plan(36,72,54),
            "bass":_register_plan(28,52,40),
        },
        "orchestration_sections":sections,
        "transitions":transitions,
        "realization":{
            "seed":7,"microtiming":{"enabled":False,"max_abs_ms":0.0},
            "velocity_variation":{"enabled":False,"max_abs":0.0},
            "timing_quantization_guard_ms":0.0,"minimum_note_gap_ms":0.0,
        },
    }


def _ir(transitions):
    return {
        "meta":{"global_seed":7,"sample_rate":44100},
        "transport":{"bpm":100,"beats_per_bar":4},
        "tonal":{"root":"D","scale":"major"},
        "form":[
            {"id":"a","start_bar":0,"bars":1},
            {"id":"b","start_bar":1,"bars":1},
            {"id":"c","start_bar":2,"bars":1},
        ],
        "materials":{"motifs":{"main":{"intervals":[0],"rhythm":[1.0]}},"progressions":{},"rhythms":{}},
        "performance_ir":_perf(transitions),
        "tracks":[
            {"id":"lead","source":{"type":"resolved"},"events":[
                {"start_beat":2.5,"duration_beats":1.0,"midi":62,"velocity":.5,"section_id":"a"},
                {"start_beat":4.0,"duration_beats":.5,"midi":64,"velocity":.5,"section_id":"b"},
                {"start_beat":6.5,"duration_beats":.75,"midi":65,"velocity":.5,"section_id":"b"},
                {"start_beat":8.0,"duration_beats":.5,"midi":67,"velocity":.5,"section_id":"c"},
            ]},
            {"id":"pad","source":{"type":"resolved"},"events":[
                {"start_beat":4.0,"duration_beats":1.5,"midi":50,"velocity":.35,"section_id":"b"},
                {"start_beat":8.0,"duration_beats":1.5,"midi":52,"velocity":.35,"section_id":"c"},
            ]},
            {"id":"bass","source":{"type":"resolved"},"events":[
                {"start_beat":2.0,"duration_beats":.8,"midi":38,"velocity":.5,"section_id":"a"},
                {"start_beat":4.0,"duration_beats":.8,"midi":42,"velocity":.5,"section_id":"b"},
                {"start_beat":7.0,"duration_beats":.8,"midi":43,"velocity":.5,"section_id":"b"},
                {"start_beat":8.0,"duration_beats":.8,"midi":45,"velocity":.5,"section_id":"c"},
            ]},
            {"id":"drums","source":{"type":"resolved"},"events":[
                {"event_type":"drum","drum":"hat","start_beat":7.25,"duration_beats":.1,"velocity":.3,"section_id":"b"}
            ]},
        ],
    }


def _ab_transition():
    return {
        "from_section":"a","to_section":"b",
        "harmonic_anticipation":{
            "enabled":True,"role":"pad","beats":1.0,"target_degree":4,
            "chord_intervals":[0,2,4],"velocity":.4,"gate":.9,
        },
        "pickup":{
            "enabled":True,"role":"lead","beats":.75,
            "degrees":[5,7],"rhythm":[.25,.25],"octave":4,"velocity":.55,
        },
        "bass_approach":{"type":"scale","beats":.75,"direction":"below","steps":2,"velocity":.48},
        "cadence_extension":{},"texture_subtraction":{},"silence_beats":0.0,
        "register_preparation":{"lead":{"semitones":2,"beats":.75}},
        "rhythm_fill":{"role":"drums","events":[
            {"offset_beats":-.5,"drum":"hat","duration_beats":.08,"velocity":.25},
            {"offset_beats":-.25,"drum":"snare","duration_beats":.10,"velocity":.35},
        ]},
    }


def _bc_transition():
    return {
        "from_section":"b","to_section":"c",
        "harmonic_anticipation":{"enabled":False},"pickup":{"enabled":False},
        "bass_approach":{"type":"none"},
        "cadence_extension":{"roles":["lead"],"beats":1.0},
        "texture_subtraction":{"roles":["bass","drums"],"beats":1.0},
        "silence_beats":.5,
        "register_preparation":{"lead":{"semitones":-2,"beats":.5}},
        "rhythm_fill":{"role":"drums","events":[
            {"offset_beats":-.25,"drum":"snare","duration_beats":.10,"velocity":.32}
        ]},
    }


def test_transition_material_is_explicit_and_structurally_distinct():
    out=realize_musical_transitions(_ir([_ab_transition(),_bc_transition()]))
    rep=out["musical_transition_report"]["transitions"]
    assert rep[0]["harmonic_anticipation_events"]==3
    assert rep[0]["pickup_events"]==2
    assert rep[0]["bass_approach_events"]==2
    assert rep[0]["rhythm_fill_events"]==2
    assert rep[0]["register_prepared_events"]>=1
    assert rep[1]["cadence_extended_events"]>=1
    assert rep[1]["texture_subtraction_removed"]>=1
    assert rep[1]["silence_removed"]>=0
    assert rep[1]["rhythm_fill_events"]==1

    pad=next(t for t in out["tracks"] if t["id"]=="pad")
    ant=[e for e in pad["events"] if e.get("transition_material")=="harmonic_anticipation"]
    assert len(ant)==3 and {e["start_beat"] for e in ant}=={3.0}

    lead=next(t for t in out["tracks"] if t["id"]=="lead")
    pickup=[e for e in lead["events"] if e.get("transition_material")=="pickup"]
    assert len(pickup)==2
    assert max(e["start_beat"] for e in pickup)<4.0
    prepared=[e for e in lead["events"] if e.get("musical_transition",{}).get("register_preparation")]
    assert any(e["midi"]==66 for e in prepared)  # original target C? 64 + 2


def test_explicit_silence_removes_existing_material_but_not_authored_fill_added_afterward():
    out=realize_musical_transitions(_ir([_bc_transition()]))
    drums=next(t for t in out["tracks"] if t["id"]=="drums")
    # Existing hat at 7.25 is removed by texture subtraction/silence, explicit snare at 7.75 survives.
    assert [(e.get("drum"),e["start_beat"]) for e in drums["events"]]==[("snare",7.75)]


def test_transition_realization_is_deterministic_and_idempotent():
    ir=_ir([_ab_transition(),_bc_transition()])
    a=realize_musical_transitions(ir)
    b=realize_musical_transitions(ir)
    assert a==b
    assert realize_musical_transitions(a)==a


def test_missing_target_bass_event_fails_instead_of_inventing_destination():
    ir=_ir([_ab_transition()])
    bass=next(t for t in ir["tracks"] if t["id"]=="bass")
    bass["events"]=[e for e in bass["events"] if e["start_beat"]<4.0]
    with pytest.raises(MusicalTransitionError):
        realize_musical_transitions(ir)


def test_e4_budget_remains_final_gate_for_e5_transition_material():
    t=_ab_transition()
    ir=_ir([t])
    # The A section declares drums hard-silent. E5 authors fill; E4 must remove it afterward.
    ir["performance_ir"]["orchestration_sections"]["a"]["silence_roles"]=["drums"]
    ir["performance_ir"]["orchestration_sections"]["a"]["decorative_roles"]=[]
    ir["performance_ir"]["orchestration_sections"]["a"]["max_simultaneous_roles"]=3
    out=realize_performance_ir(ir)
    drums=next(tr for tr in out["tracks"] if tr["id"]=="drums")
    assert not any(e.get("transition_material")=="rhythm_fill" for e in drums["events"])


def test_e5_transition_material_is_not_rewritten_by_adjacent_e1_phrase():
    t=_ab_transition()
    ir=_ir([t])
    ir["performance_ir"]["phrases"]=[{
        "phrase_id":"lead_a","section_id":"a","role":"lead","source_material":"main",
        "start_beat":0.0,"duration_beats":4.0,
        "dynamic_curve":[[0,.2],[1,.2]],"timing_curve_ms":[[0,15],[1,15]],
        "gate_curve":[[0,.5],[1,.5]],
        "articulation_curve":[{"position":0,"articulation":"staccato"}],
        "accent_points":[],"breath_after_beats":0.0,
    }]
    out=realize_performance_ir(ir)
    lead=next(tr for tr in out["tracks"] if tr["id"]=="lead")
    pickup=[e for e in lead["events"] if e.get("transition_material")=="pickup"]
    assert pickup
    assert all(e["velocity"]==pytest.approx(.55) for e in pickup)
    assert all("performance" not in e for e in pickup)

from code_composer.agent.expressive_score_plan import (
    ExpressivePlanValidationError, ExpressiveValidationContext,
    expressive_score_plan_from_dict, validate_expressive_score_plan,
)


def _plan_for_validation(transition):
    return {
        "version":"1.16","narrative":{"arc":"transition contract validation"},
        "phrases":[],"motif_statements":[],
        "register_plans":{
            "lead":_register_plan(48,84,66),"pad":_register_plan(36,72,54),"bass":_register_plan(28,52,40),
        },
        "orchestration_sections":{
            "a":{"primary_roles":["lead"],"secondary_roles":["pad","bass"],"decorative_roles":["drums"],"max_simultaneous_roles":4,"allowed_overlaps":[],"phrase_gap_only_roles":[],"silence_roles":[]},
            "b":{"primary_roles":["lead"],"secondary_roles":["pad","bass"],"decorative_roles":["drums"],"max_simultaneous_roles":4,"allowed_overlaps":[],"phrase_gap_only_roles":[],"silence_roles":[]},
        },
        "transitions":[transition],
    }


def _validation_context():
    return ExpressiveValidationContext(
        section_ids=("a","b"),role_ids=("lead","pad","bass","drums"),
        source_material_ids=("main",),section_spans={"a":(0.0,4.0),"b":(4.0,8.0)}
    )


def test_old_ambiguous_transition_contract_is_rejected():
    bad={
        "from_section":"a","to_section":"b",
        "harmonic_anticipation":{"enabled":True,"beats":1.0,"target_degree":5},
        "pickup":{"enabled":False},"bass_approach":{"type":"none"},
        "cadence_extension":{},"texture_subtraction":{},"silence_beats":0,
        "register_preparation":{},"rhythm_fill":{},
    }
    plan=expressive_score_plan_from_dict(_plan_for_validation(bad))
    with pytest.raises(ExpressivePlanValidationError):
        validate_expressive_score_plan(plan,_validation_context())


def test_pickup_requires_explicit_degrees_and_matching_rhythm():
    bad=_ab_transition()
    bad=deepcopy(bad)
    bad["pickup"]["rhythm"]=[.25]
    plan=expressive_score_plan_from_dict(_plan_for_validation(bad))
    with pytest.raises(ExpressivePlanValidationError):
        validate_expressive_score_plan(plan,_validation_context())
