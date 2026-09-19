from copy import deepcopy

from code_composer.analysis.expressive_qa import (
    analyze_expressive_qa,
    compare_expressive_qa,
)


def _base():
    perf={
        "version":"1.16",
        "phrases":[{
            "phrase_id":"p1","section_id":"a","role":"lead","source_material":"main",
            "start_beat":0.0,"duration_beats":4.0,
            "dynamic_curve":[[0,.5],[1,.5]],
            "timing_curve_ms":[[0,0],[1,0]],
            "gate_curve":[[0,1],[1,1]],
            "articulation_curve":[{"position":0,"articulation":"neutral"}],
            "accent_points":[],"breath_after_beats":.5,
        }],
        "motif_statements":[],
        "register_plans":{
            "lead":{"hard_range":[48,84],"preferred_range":[55,76],"center":64,"max_span":24,"min_intervoice_distance":0,"overlap_policy":"primary_wins","motion_policy":"smooth"},
            "pad":{"hard_range":[48,84],"preferred_range":[55,76],"center":60,"max_span":24,"min_intervoice_distance":0,"overlap_policy":"avoid","motion_policy":"oblique"},
        },
        "orchestration_sections":{
            "a":{"primary_roles":["lead"],"secondary_roles":["pad"],"decorative_roles":[],"max_simultaneous_roles":2,"allowed_overlaps":[],"phrase_gap_only_roles":[],"silence_roles":[]},
            "b":{"primary_roles":["lead"],"secondary_roles":[],"decorative_roles":[],"max_simultaneous_roles":1,"allowed_overlaps":[],"phrase_gap_only_roles":[],"silence_roles":["pad"]},
        },
        "transitions":[{
            "from_section":"a","to_section":"b",
            "harmonic_anticipation":{"enabled":False},
            "pickup":{"enabled":False},
            "bass_approach":{"type":"none"},
            "cadence_extension":{},
            "texture_subtraction":{},
            "silence_beats":0.0,
            "register_preparation":{},
            "rhythm_fill":{},
        }],
        "realization":{"seed":1,"microtiming":{"enabled":False,"max_abs_ms":0.0},"velocity_variation":{"enabled":False,"max_abs":0.0},"timing_quantization_guard_ms":0.0,"minimum_note_gap_ms":0.0},
    }
    lead_events=[]
    for i,m in enumerate([60,62,64,65,67]):
        lead_events.append({
            "start_beat":float(i),"duration_beats":1.15 if i==3 else .75,
            "midi":m,"velocity":.5,"section_id":"a","arrangement_role":"lead",
            "performance":{"timing_offset_ms":0.0},
        })
    pad_events=[
        {"start_beat":0.0,"duration_beats":4.0,"midi":61,"velocity":.35,"section_id":"a","arrangement_role":"pad"}
    ]
    return {
        "transport":{"bpm":100,"beats_per_bar":4},
        "form":[{"id":"a","start_bar":0,"bars":1},{"id":"b","start_bar":1,"bars":1}],
        "performance_ir":perf,
        "tracks":[
            {"id":"lead","events":lead_events},
            {"id":"pad","events":pad_events},
        ],
        "motif_development_report":{"statements":[]},
    }


def test_detects_mechanical_flat_masking_collision_and_missing_breath():
    ir=_base()
    section={
        "transitions":{"b":{"discontinuity":.81,"before_rms":.1,"after_rms":.01,"direction":"down"}}
    }
    q=analyze_expressive_qa(ir,section)
    codes={i["code"] for i in q["issues"]}
    assert "MECHANICAL_TIMING" in codes
    assert "FLAT_DYNAMICS" in codes
    assert "REGISTER_COLLISION" in codes
    assert "ORCHESTRATION_MASKING" in codes
    assert "TRANSITION_DISCONTINUITY" in codes
    assert "PHRASE_NO_BREATH" in codes


def test_clean_revision_resolves_target_codes():
    before=analyze_expressive_qa(
        _base(),
        {"transitions":{"b":{"discontinuity":.81,"before_rms":.1,"after_rms":.01,"direction":"down"}}},
    )
    ir=_base()
    phrase=ir["performance_ir"]["phrases"][0]
    phrase["dynamic_curve"]=[[0,.42],[.55,.75],[1,.46]]
    phrase["timing_curve_ms"]=[[0,0],[.6,5],[1,9]]
    # Remove pad masking/collision and enforce actual breath.
    ir["tracks"][1]["events"]=[]
    ir["tracks"][0]["events"]=[
        dict(e,velocity=v,performance={"timing_offset_ms":t})
        for e,v,t in zip(ir["tracks"][0]["events"][:4],[.42,.55,.75,.50],[0,2,5,8])
    ]
    ir["tracks"][0]["events"][-1]["duration_beats"]=.65
    after=analyze_expressive_qa(
        ir,
        {"transitions":{"b":{"discontinuity":.18,"before_rms":.05,"after_rms":.06,"direction":"flat"}}},
    )
    cmp=compare_expressive_qa(
        before,after,
        ["MECHANICAL_TIMING","FLAT_DYNAMICS","REGISTER_COLLISION","ORCHESTRATION_MASKING","TRANSITION_DISCONTINUITY","PHRASE_NO_BREATH"]
    )
    assert cmp["improved"] is True
    assert cmp["after_issue_count"]==0
    assert cmp["resolved_count"]>=6


def test_motif_identity_loss_is_evidence_only():
    ir=_base()
    ir["motif_development_report"]={
        "statements":[{
            "statement_id":"s1","identity_floor":.75,
            "identity":{"score":.62},
        }]
    }
    q=analyze_expressive_qa(ir,{})
    issue=next(i for i in q["issues"] if i["code"]=="MOTIF_IDENTITY_LOSS")
    assert issue["observed"]==.62
    assert issue["expected_min"]==.75


def test_compare_does_not_mutate_reports():
    before={"issues":[{"code":"FLAT_DYNAMICS","severity":"medium"}]}
    after={"issues":[]}
    a=deepcopy(before); b=deepcopy(after)
    cmp=compare_expressive_qa(before,after,["FLAT_DYNAMICS"])
    assert cmp["improved"]
    assert before==a and after==b


def test_orchestration_masking_uses_role_occupancy_union_not_polyphonic_note_sum():
    ir=_base()
    # Transition-like polyphonic pad chord occupies only the final 0.765 beat window.
    ir["tracks"][0]["events"]=[
        {"start_beat":0.0,"duration_beats":.75,"midi":64,"velocity":.5,"section_id":"a","arrangement_role":"lead","performance":{"timing_offset_ms":0}},
        {"start_beat":1.5,"duration_beats":.70,"midi":67,"velocity":.5,"section_id":"a","arrangement_role":"lead","performance":{"timing_offset_ms":0}},
        {"start_beat":3.5,"duration_beats":.23,"midi":71,"velocity":.5,"section_id":"a","arrangement_role":"lead","performance":{"timing_offset_ms":0}},
        {"start_beat":3.75,"duration_beats":.23,"midi":74,"velocity":.5,"section_id":"a","arrangement_role":"lead","performance":{"timing_offset_ms":0}},
    ]
    ir["tracks"][1]["events"]=[
        {"start_beat":3.25,"duration_beats":.765,"midi":50,"velocity":.35,"section_id":"a","arrangement_role":"pad"},
        {"start_beat":3.25,"duration_beats":.765,"midi":54,"velocity":.35,"section_id":"a","arrangement_role":"pad"},
        {"start_beat":3.25,"duration_beats":.765,"midi":59,"velocity":.35,"section_id":"a","arrangement_role":"pad"},
    ]
    # Remove unrelated phrase/transition findings to isolate masking evidence.
    ir["performance_ir"]["phrases"]=[]
    ir["performance_ir"]["transitions"]=[]
    q=analyze_expressive_qa(ir,{})
    row=next(x for x in q["evidence"]["orchestration_masking"] if x["primary_role"]=="lead" and x["subordinate_role"]=="pad")
    assert row["overlap_ratio"]==0.240838
    assert not any(i["code"]=="ORCHESTRATION_MASKING" for i in q["issues"])


def test_compare_blocks_target_success_when_new_non_target_high_issue_appears():
    before={"issues":[{"code":"TRANSITION_DISCONTINUITY","severity":"medium","to_section":"b"}]}
    after={"issues":[{"code":"REGISTER_COLLISION","severity":"high","section":"b","roles":["lead","pad"]}]}
    cmp=compare_expressive_qa(before,after,["TRANSITION_DISCONTINUITY"])
    assert cmp["target_improved"] is True
    assert cmp["regression_free"] is False
    assert cmp["introduced_high_medium_count"]==1
    assert cmp["introduced_non_target"][0]["code"]=="REGISTER_COLLISION"
    assert cmp["improved"] is False


def test_compare_allows_target_success_when_only_new_low_non_target_evidence_appears():
    before={"issues":[{"code":"FLAT_DYNAMICS","severity":"medium","phrase_id":"p"}]}
    after={"issues":[{"code":"COSMETIC_NOTE","severity":"low","section":"a"}]}
    cmp=compare_expressive_qa(before,after,["FLAT_DYNAMICS"])
    assert cmp["target_improved"] is True
    assert cmp["introduced_non_target_count"]==1
    assert cmp["introduced_high_medium_count"]==0
    assert cmp["regression_free"] is True
    assert cmp["improved"] is True


def test_compare_without_explicit_targets_still_blocks_new_high_issue():
    before={"issues":[
        {"code":"FLAT_DYNAMICS","severity":"medium","phrase_id":"p1"},
        {"code":"MECHANICAL_TIMING","severity":"medium","phrase_id":"p1"},
    ]}
    after={"issues":[
        {"code":"REGISTER_COLLISION","severity":"high","section":"a","roles":["lead","pad"]}
    ]}
    cmp=compare_expressive_qa(before,after)
    assert cmp["target_improved"] is True
    assert cmp["introduced_high_medium_count"]==1
    assert cmp["regression_free"] is False
    assert cmp["improved"] is False
