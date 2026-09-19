import json
from copy import deepcopy
from pathlib import Path
from _paths import SCHEMA_ROOT, PACKAGED_SCHEMA_ROOT, SOURCE_ROOT

import jsonschema
import pytest

from code_composer.agent.expressive_score_plan import (
    ExpressivePlanValidationError,
    ExpressiveValidationContext,
    expressive_score_plan_from_dict,
    expressive_score_plan_to_dict,
    validate_expressive_score_plan,
)
from code_composer.agent.performance_ir import (
    PerformanceIRValidationError,
    compile_performance_ir,
    performance_ir_to_dict,
    performance_ir_from_dict,
    validate_performance_ir,
)


ROOT=Path(__file__).resolve().parents[1]


def _plan_dict():
    return json.loads(
        (ROOT/"examples/v1.16/after_the_rain_expressive_score_plan.json").read_text()
    )


def _context():
    return ExpressiveValidationContext(
        section_ids=("dawn","memory","bloom","stillness","horizon"),
        role_ids=("lead","pad","bass","arp","drums","topline"),
        source_material_ids=("motif_A",),
        section_spans={
            "dawn":(0.0,16.0),
            "memory":(16.0,32.0),
            "bloom":(32.0,48.0),
            "stillness":(48.0,64.0),
            "horizon":(64.0,84.0),
        },
    )


def test_expressive_schema_and_python_validator_accept_reference_example():
    data=_plan_dict()
    schema=json.loads((SCHEMA_ROOT/"expressive_score_plan.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(data,schema)
    plan=expressive_score_plan_from_dict(data)
    validate_expressive_score_plan(plan,_context())
    assert expressive_score_plan_to_dict(plan)==data


@pytest.mark.parametrize("mutator",[
    lambda d: d["phrases"][0].update({"section_id":"ghost"}),
    lambda d: d["phrases"][0].update({"role":"ghost"}),
    lambda d: d["phrases"][0].update({"source_material":"ghost"}),
    lambda d: d["phrases"][1].update({"phrase_id":d["phrases"][0]["phrase_id"]}),
    lambda d: d["phrases"][0].update({"dynamic_curve":[[0.0,.4],[.8,.7],[.7,.5],[1.0,.3]]}),
    lambda d: d["register_plans"]["lead"].update({"preferred_range":[40,77]}),
    lambda d: d["orchestration_sections"]["dawn"]["silence_roles"].append("lead"),
    lambda d: d["transitions"][0].update({"to_section":"bloom"}),
    lambda d: d["motif_statements"][3]["transform_chain"][0].pop("length"),
])
def test_cross_reference_and_invariant_failures_are_rejected(mutator):
    data=_plan_dict()
    mutator(data)
    plan=expressive_score_plan_from_dict(data)
    with pytest.raises(ExpressivePlanValidationError):
        validate_expressive_score_plan(plan,_context())


def test_phrase_must_stay_inside_authored_section_span():
    data=_plan_dict()
    data["phrases"][0]["duration_beats"]=18.0
    plan=expressive_score_plan_from_dict(data)
    with pytest.raises(ExpressivePlanValidationError):
        validate_expressive_score_plan(plan,_context())


def test_performance_ir_compiles_without_creative_mutation():
    plan=expressive_score_plan_from_dict(_plan_dict())
    ir=compile_performance_ir(
        plan,_context(),seed=260916,
        realization={
            "microtiming":{"max_abs_ms":9.0},
            "velocity_variation":{"max_abs":0.018},
        },
    )
    validate_performance_ir(ir,_context())
    d=performance_ir_to_dict(ir)

    assert d["phrases"]==_plan_dict()["phrases"]
    assert d["motif_statements"]==_plan_dict()["motif_statements"]
    assert d["register_plans"]==_plan_dict()["register_plans"]
    assert d["orchestration_sections"]==_plan_dict()["orchestration_sections"]
    assert d["transitions"]==_plan_dict()["transitions"]
    assert d["realization"]["seed"]==260916
    assert d["realization"]["microtiming"]["max_abs_ms"]==9.0
    assert d["realization"]["velocity_variation"]["max_abs"]==0.018


def test_performance_ir_roundtrip():
    plan=expressive_score_plan_from_dict(_plan_dict())
    ir=compile_performance_ir(plan,_context(),seed=11)
    data=performance_ir_to_dict(ir)
    rebuilt=performance_ir_from_dict(data)
    validate_performance_ir(rebuilt,_context())
    assert performance_ir_to_dict(rebuilt)==data


def test_compiled_performance_ir_matches_public_schema():
    plan=expressive_score_plan_from_dict(_plan_dict())
    ir=compile_performance_ir(plan,_context(),seed=260916)
    data=performance_ir_to_dict(ir)
    schema=json.loads((SCHEMA_ROOT/"performance_ir.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(data,schema)


def test_performance_ir_realization_bounds_are_strict():
    plan=expressive_score_plan_from_dict(_plan_dict())
    with pytest.raises(PerformanceIRValidationError):
        compile_performance_ir(
            plan,_context(),seed=1,
            realization={"microtiming":{"max_abs_ms":31.0}},
        )


def test_packaged_expressive_schemas_match_agent_facing_contracts_and_music_examples_are_not_shipped():
    for name in ("expressive_score_plan.schema.json", "performance_ir.schema.json"):
        assert (SCHEMA_ROOT/name).read_bytes() == (PACKAGED_SCHEMA_ROOT/name).read_bytes()
    ref_examples=SOURCE_ROOT/"reference"/"examples"
    assert not list(ref_examples.glob("*.json"))
