import json
from copy import deepcopy
from pathlib import Path

import pytest

from code_composer.agent.composition_brief import brief_from_dict, BriefValidationError
from code_composer.agent.composer_planner import compile_brief, apply_composer_plan
from code_composer.pipeline.validation import validate_ir as validate_pipeline_ir
from code_composer.core.ir import IRValidationError
from code_composer.render import render


ROOT=Path(__file__).resolve().parents[1]

def _seed():
    ir=json.loads((ROOT/"tests/fixtures/topline_ir.json").read_text())
    ir["meta"]["sample_rate"]=8000
    return ir

def _brief():
    return json.loads((ROOT/"tests/fixtures/composition_brief.json").read_text())

@pytest.mark.parametrize("mutation",[
    lambda d: d["transitions"]["final"].update({"entry_gain":"oops"}),
    lambda d: d["transitions"]["final"].update({"unknown_transition_knob":0.5}),
    lambda d: d["development"]["sections"]["verse"].update({"rhythm_density_scale":"oops"}),
    lambda d: d["development"]["families"].update({"bad":["missing_section"]}),
    lambda d: d["harmony"]["sections"]["verse"].update({"colors":["not_a_color"]}),
    lambda d: d["harmony"]["sections"].update({"missing_section":{"colors":["add9"]}}),
    lambda d: d["rhythm"]["section_profiles"].update({"missing_section":{"density":0.5}}),
])
def test_invalid_brief_contracts_fail_before_compile(mutation):
    data=_brief()
    mutation(data)
    with pytest.raises(BriefValidationError):
        compile_brief(_seed(),brief_from_dict(data))

def test_direct_ir_invalid_piano_design_fails_aggregate_validation():
    ir=_seed()
    inst_id=ir["arrangement"]["roles"]["lead"]["instrument"]
    ir["instruments"][inst_id]={
        "kind":"piano",
        "piano_design":{"categories":{"body":"warm"},"controls":{}},
    }
    with pytest.raises(IRValidationError):
        validate_pipeline_ir(ir)

def test_direct_ir_invalid_runtime_development_fails_validation():
    ir=apply_composer_plan(_seed(),compile_brief(_seed(),brief_from_dict(_brief())))
    ir["arrangement_development"]["sections"]["verse"]["rhythm_density_scale"]="oops"
    with pytest.raises(IRValidationError):
        validate_pipeline_ir(ir)

def test_direct_ir_invalid_runtime_harmony_fails_validation():
    ir=apply_composer_plan(_seed(),compile_brief(_seed(),brief_from_dict(_brief())))
    ir["harmonic_grammar"]["sections"]["verse"]["colors"]=["not_a_color"]
    with pytest.raises(IRValidationError):
        validate_pipeline_ir(ir)

def test_direct_ir_invalid_transition_profile_fails_validation():
    ir=apply_composer_plan(_seed(),compile_brief(_seed(),brief_from_dict(_brief())))
    ir["arrangement"]["profiles"]["final"]["entry_gain"]="oops"
    with pytest.raises(IRValidationError):
        validate_pipeline_ir(ir)

def test_validated_brief_compiles_validates_and_renders(tmp_path):
    seed=_seed()
    data=_brief()
    # Keep the closure test fast while preserving a transition boundary.
    for sec in data["form"]["sections"]:
        sec["bars"]=1
    brief=brief_from_dict(data)
    plan=compile_brief(seed,brief)
    ir=apply_composer_plan(seed,plan)

    validate_pipeline_ir(ir)
    audio,sr,resolved=render(ir,str(tmp_path/"closure.wav"))
    assert sr==8000
    assert len(audio)>0
    assert (tmp_path/"closure.wav").exists()
    assert resolved["arrangement_resolved"] is True
