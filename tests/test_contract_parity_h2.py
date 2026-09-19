import json
from copy import deepcopy
from pathlib import Path
from _paths import SCHEMA_ROOT, PACKAGED_SCHEMA_ROOT

import jsonschema
import pytest

from code_composer.agent.expressive_score_plan import (
    ExpressiveValidationContext,
    expressive_score_plan_from_dict,
    validate_expressive_score_plan,
    ExpressivePlanValidationError,
)
from code_composer.agent.performance_ir import (
    compile_performance_ir,
    performance_ir_to_dict,
    performance_ir_from_dict,
    validate_performance_ir,
    PerformanceIRValidationError,
)


ROOT=Path(__file__).resolve().parents[1]


def _plan():
    return json.loads(
        (ROOT/"examples/v1.16/after_the_rain_expressive_score_plan.json").read_text()
    )


def _ctx():
    return ExpressiveValidationContext(
        section_ids=("dawn","memory","bloom","stillness","horizon"),
        role_ids=("lead","pad","bass","arp","drums","topline"),
        source_material_ids=("motif_A",),
        section_spans={
            "dawn":(0,16),"memory":(16,32),"bloom":(32,48),
            "stillness":(48,64),"horizon":(64,84),
        },
    )


def _schema(name):
    return json.loads((SCHEMA_ROOT/name).read_text())


def _schema_rejects(data,schema):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(data,schema)


def _runtime_rejects_plan(data):
    with pytest.raises(ExpressivePlanValidationError):
        validate_expressive_score_plan(expressive_score_plan_from_dict(data),_ctx())


@pytest.mark.parametrize("mutator",[
    lambda d: d["transitions"][0].update({"harmonic_anticipation":{"enabled":True}}),
    lambda d: d["transitions"][0].update({"pickup":{"enabled":True}}),
    lambda d: d["transitions"][0].update({"cadence_extension":{"roles":["lead"]}}),
    lambda d: d["transitions"][0].update({"texture_subtraction":{"beats":1.0}}),
    lambda d: d["transitions"][0].update({"bass_approach":{"type":"step","beats":.5,"velocity":.4}}),
    lambda d: d["transitions"][0].update({"rhythm_fill":{"role":"drums"}}),
    lambda d: d["phrases"][0].update({"dynamic_curve":[[0,1.2],[1,.5]]}),
    lambda d: d["phrases"][0].update({"timing_curve_ms":[[0,0],[1,31]]}),
    lambda d: d["phrases"][0].update({"gate_curve":[[0,0.0],[1,1.0]]}),
    lambda d: d["motif_statements"][0].update({
        "transform_chain":[{"op":"cadence_rewrite","intervals":[]}]
    }),
    lambda d: d["orchestration_sections"]["dawn"].update({
        "primary_roles":["lead","lead"]
    }),
])
def test_expressible_structural_invalidity_is_rejected_by_schema_and_runtime(mutator):
    data=_plan()
    mutator(data)
    _schema_rejects(data,_schema("expressive_score_plan.schema.json"))
    _runtime_rejects_plan(data)


def test_performance_ir_reuses_full_nested_contracts():
    plan=expressive_score_plan_from_dict(_plan())
    perf=performance_ir_to_dict(compile_performance_ir(plan,_ctx(),seed=7))
    schema=_schema("performance_ir.schema.json")

    cases=[]

    d=deepcopy(perf)
    d["phrases"][0]["dynamic_curve"]=[[0,1.4],[1,.3]]
    cases.append(d)

    d=deepcopy(perf)
    d["motif_statements"][0]["transform_chain"]=[{"op":"response","intervals":[],"rhythm":[]}]
    cases.append(d)

    d=deepcopy(perf)
    d["orchestration_sections"]["dawn"]["primary_roles"]=["lead","lead"]
    cases.append(d)

    d=deepcopy(perf)
    d["transitions"][0]["pickup"]={"enabled":True}
    cases.append(d)

    for invalid in cases:
        _schema_rejects(invalid,schema)
        with pytest.raises(PerformanceIRValidationError):
            validate_performance_ir(performance_ir_from_dict(invalid),_ctx())


def test_python_only_cross_reference_invariant_is_explicitly_residual():
    data=_plan()
    data["phrases"][0]["role"]="ghost"

    # JSON Schema validates local structure, while context-aware role membership
    # remains intentionally Python-only and is documented in x-python-only-invariants.
    schema=_schema("expressive_score_plan.schema.json")
    jsonschema.validate(data,schema)
    assert any(
        "cross references" in x
        for x in schema["x-python-only-invariants"]
    )
    _runtime_rejects_plan(data)


def test_python_only_relational_range_invariant_is_explicitly_residual():
    data=_plan()
    data["register_plans"]["lead"]["hard_range"]=[90,40]

    schema=_schema("expressive_score_plan.schema.json")
    jsonschema.validate(data,schema)
    assert any(
        "range ordering" in x
        for x in schema["x-python-only-invariants"]
    )
    _runtime_rejects_plan(data)


def test_python_only_pickup_sum_invariant_is_explicitly_residual():
    data=_plan()
    t=data["transitions"][1]
    t["pickup"]["beats"]=.5
    t["pickup"]["rhythm"]=[.4,.4]

    schema=_schema("expressive_score_plan.schema.json")
    jsonschema.validate(data,schema)
    assert any(
        "pickup rhythm" in x
        for x in schema["x-python-only-invariants"]
    )
    _runtime_rejects_plan(data)


def test_schema_packaged_copies_remain_byte_identical():
    for name in ["expressive_score_plan.schema.json","performance_ir.schema.json"]:
        assert (SCHEMA_ROOT/name).read_bytes() == (
            PACKAGED_SCHEMA_ROOT/name
        ).read_bytes()
