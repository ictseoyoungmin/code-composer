import json
from copy import deepcopy
from pathlib import Path
from _paths import SCHEMA_ROOT

import jsonschema
import pytest

from code_composer.agent.expressive_score_plan import (
    ExpressivePlanValidationError,
    ExpressiveValidationContext,
    expressive_score_plan_from_dict,
)
from code_composer.agent.performance_ir import compile_performance_ir
from code_composer.analysis.expressive_qa import analyze_expressive_qa
from code_composer.composition.motif_development import (
    MotifDevelopmentError,
    apply_transform_chain,
    realize_motif_statements,
)
from code_composer.composition.performance import attach_performance_ir, realize_performance_ir


ROOT=Path(__file__).resolve().parents[1]
SOURCE={"intervals":[0,1,3,4,3,1,2,0],"rhythm":[.5]*8}


def _context():
    return ExpressiveValidationContext(
        section_ids=("one",),role_ids=("lead",),source_material_ids=("motif_A",),
        section_spans={"one":(0.0,8.0)},
    )


def _base_ir():
    return {
        "transport":{"bpm":84,"beats_per_bar":4},
        "tonal":{"root":"D","scale":"major"},
        "form":[{"id":"one","start_bar":0,"bars":2,"energy":.6}],
        "materials":{"motifs":{"motif_A":deepcopy(SOURCE)}},
        "tracks":[{"id":"lead","source":{"type":"resolved"},"events":[
            {"start_beat":0.0,"duration_beats":.42,"midi":62,"velocity":.55,
             "section_id":"one","arrangement_role":"lead"}
        ]}],
    }


def _plan(statement, *, duration=4.0):
    return {
        "version":"1.16","narrative":{"arc":"H3 motif semantic test"},
        "phrases":[{
            "phrase_id":"p","section_id":"one","role":"lead",
            "source_material":statement["statement_id"],
            "start_beat":0.0,"duration_beats":duration,
            "dynamic_curve":[[0,.5],[1,.5]],
            "timing_curve_ms":[[0,0],[1,0]],
            "gate_curve":[[0,1],[1,1]],
            "articulation_curve":[{"position":0,"articulation":"neutral"}],
            "accent_points":[],"breath_after_beats":0.0,
        }],
        "motif_statements":[statement],
        "register_plans":{"lead":{
            "hard_range":[48,84],"preferred_range":[55,76],"center":64,
            "max_span":24,"min_intervoice_distance":0,
            "overlap_policy":"allow","motion_policy":"smooth",
        }},
        "orchestration_sections":{"one":{
            "primary_roles":["lead"],"secondary_roles":[],"decorative_roles":[],
            "max_simultaneous_roles":1,"allowed_overlaps":[],
            "phrase_gap_only_roles":[],"silence_roles":[],
        }},
        "transitions":[],
    }


def test_call_is_explicit_content_not_exact_alias():
    statement={
        "statement_id":"call_1","source_motif_id":"motif_A","section_id":"one",
        "transform_chain":[{
            "op":"call","intervals":[1,2,4,5],"rhythm":[.25,.5,.5,.75]
        }],
        "identity_floor":.0,
    }
    out=apply_transform_chain(SOURCE,statement)
    assert out["intervals"] == [1,2,4,5]
    assert out["rhythm"] == [.25,.5,.5,.75]
    assert out["relation"] == {"role":"call"}
    assert out["intervals"] != SOURCE["intervals"]


def test_response_must_reference_earlier_call_statement():
    call={
        "statement_id":"call_1","source_motif_id":"motif_A","section_id":"one",
        "transform_chain":[{"op":"call","intervals":[0,1,3,4],"rhythm":[.5]*4}],
        "identity_floor":.4,
    }
    response={
        "statement_id":"response_1","source_motif_id":"motif_A","section_id":"one",
        "transform_chain":[{
            "op":"response","intervals":[4,3,1,0],"rhythm":[.5,.5,.75,1.0],
            "responds_to":"call_1",
        }],
        "identity_floor":.3,
    }
    data=_plan(call)
    data["motif_statements"]=[call,response]
    data["phrases"][0]["source_material"]="response_1"
    plan=expressive_score_plan_from_dict(data)
    compile_performance_ir(plan,_context(),seed=1)

    bad=deepcopy(data)
    bad["motif_statements"][1]["transform_chain"][0]["responds_to"]="ghost"
    with pytest.raises(ExpressivePlanValidationError):
        compile_performance_ir(expressive_score_plan_from_dict(bad),_context(),seed=1)

    bad=deepcopy(data)
    bad["motif_statements"][0]["transform_chain"]=[{"op":"exact"}]
    with pytest.raises(ExpressivePlanValidationError):
        compile_performance_ir(expressive_score_plan_from_dict(bad),_context(),seed=1)


def test_public_schema_requires_explicit_call_and_response_relation():
    schema=json.loads((SCHEMA_ROOT/"expressive_score_plan.schema.json").read_text())
    data=json.loads((ROOT/"examples/v1.16/after_the_rain_expressive_score_plan.json").read_text())

    bad=deepcopy(data)
    call=next(s for s in bad["motif_statements"] if s["statement_id"]=="stmt_bloom_call")
    call["transform_chain"]=[{"op":"call"}]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad,schema)

    bad=deepcopy(data)
    response=next(s for s in bad["motif_statements"] if s["statement_id"]=="stmt_bloom_response")
    op=next(x for x in response["transform_chain"] if x["op"]=="response")
    op.pop("responds_to")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad,schema)


def test_identity_floor_is_reachable_as_e6_qa_evidence():
    statement={
        "statement_id":"weak_identity","source_motif_id":"motif_A","section_id":"one",
        "transform_chain":[{"op":"inversion"}],
        "identity_floor":.95,
    }
    plan=expressive_score_plan_from_dict(_plan(statement))
    perf=compile_performance_ir(plan,_context(),seed=3,realization={
        "microtiming":{"enabled":False,"max_abs_ms":0},
        "velocity_variation":{"enabled":False,"max_abs":0},
    })
    attached=attach_performance_ir(_base_ir(),perf)
    resolved=realize_performance_ir(attached)
    statement_report=resolved["motif_development_report"]["statements"][0]
    assert statement_report["identity"]["score"] < .95
    assert statement_report["identity_target_met"] is False

    qa=analyze_expressive_qa(resolved,{})
    issue=next(i for i in qa["issues"] if i["code"]=="MOTIF_IDENTITY_LOSS")
    assert issue["statement_id"] == "weak_identity"
    assert issue["expected_min"] == .95


def test_identity_hard_min_is_separate_explicit_validity_constraint():
    statement={
        "statement_id":"hard_guard","source_motif_id":"motif_A","section_id":"one",
        "transform_chain":[{"op":"inversion"}],
        "identity_floor":.95,
        "identity_hard_min":.90,
    }
    # Structured contract is valid; source-aware motif execution enforces the hard minimum.
    plan=expressive_score_plan_from_dict(_plan(statement))
    perf=compile_performance_ir(plan,_context(),seed=1)
    with pytest.raises(MotifDevelopmentError):
        attach_performance_ir(_base_ir(),perf)


def test_identity_hard_min_cannot_exceed_soft_quality_floor():
    statement={
        "statement_id":"bad_thresholds","source_motif_id":"motif_A","section_id":"one",
        "transform_chain":[{"op":"exact"}],
        "identity_floor":.50,
        "identity_hard_min":.75,
    }
    with pytest.raises(ExpressivePlanValidationError):
        compile_performance_ir(expressive_score_plan_from_dict(_plan(statement)),_context(),seed=1)
