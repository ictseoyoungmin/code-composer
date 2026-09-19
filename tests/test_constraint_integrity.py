import json
from copy import deepcopy
from pathlib import Path
from _paths import SCHEMA_ROOT

import pytest

from code_composer.agent.composition_brief import brief_from_dict, BriefValidationError
from code_composer.agent.composer_planner import compile_brief, apply_composer_plan
from code_composer.composition.arrange import arrange_ir
from code_composer.core.ir import validate_ir, IRValidationError


def _root():
    return Path(__file__).resolve().parents[1]


def _seed():
    return json.loads((_root()/"tests/fixtures/topline_ir.json").read_text())


def _brief():
    return json.loads((_root()/"tests/fixtures/composition_brief.json").read_text())


def _compiled_with_forbidden(*roles):
    seed=_seed()
    data=_brief()
    data["hard_constraints"]["forbidden_roles"]=list(roles)
    # Avoid authoring-time contradiction when lead/topline themselves are forbidden.
    if "lead" in roles or "topline" in roles:
        data["orchestration"]["default"]={"foreground_mode":"none"}
        data["orchestration"]["sections"]={
            sec["id"]:{"foreground_mode":"none"}
            for sec in data["form"]["sections"]
        }
    brief=brief_from_dict(data)
    return apply_composer_plan(seed,compile_brief(seed,brief))


@pytest.mark.parametrize("role", ["lead","topline","pad","bass","drums","arp"])
def test_each_forbidden_role_resolves_to_zero_events_and_track_is_retained(role):
    ir=_compiled_with_forbidden(role)
    resolved=arrange_ir(ir)
    track=next(t for t in resolved["tracks"] if t["id"]==role)
    assert track["events"]==[]
    assert track["hard_constraint"]["forbidden_role"]==role
    # Keep topology stable for the mix graph and downstream analysis.
    assert role in resolved["mix"]["graph"]["tracks"]


def test_compiler_promotes_hard_constraints_to_runtime_ir():
    ir=_compiled_with_forbidden("bass","drums")
    assert ir["hard_constraints"]["forbidden_roles"]==["bass","drums"]


def test_unknown_hard_constraint_key_is_rejected_at_brief_validation():
    data=_brief()
    data["hard_constraints"]["forbiden_roles"]=["bass"]
    with pytest.raises(BriefValidationError,match="unknown hard constraint key"):
        compile_brief(_seed(),brief_from_dict(data))


def test_unknown_hard_constraint_key_is_rejected_for_direct_ir():
    ir=_seed()
    ir["hard_constraints"]={"forbiden_roles":["bass"]}
    with pytest.raises(IRValidationError,match="unknown hard constraint key"):
        validate_ir(ir)


@pytest.mark.parametrize("bad", ["bass", {"bass":True}, ["bass","bass"], ["not_a_role"]])
def test_malformed_forbidden_role_contract_is_rejected(bad):
    data=_brief()
    data["hard_constraints"]["forbidden_roles"]=bad
    with pytest.raises(BriefValidationError):
        compile_brief(_seed(),brief_from_dict(data))


def test_composition_brief_schema_rejects_unknown_hard_constraint_keys():
    schema=json.loads((SCHEMA_ROOT/"composition_brief.schema.json").read_text())
    assert schema["properties"]["hard_constraints"]["additionalProperties"] is False


def test_pre_resolved_ir_cannot_bypass_forbidden_role_gate(tmp_path):
    from code_composer.render import render
    base=arrange_ir(_seed())
    assert next(t for t in base["tracks"] if t["id"]=="bass")["events"]
    base["hard_constraints"]={"forbidden_roles":["bass"]}
    base["arrangement_resolved"]=True
    _audio,_sr,rendered=render(base,str(tmp_path/"pre_resolved.wav"))
    bass=next(t for t in rendered["tracks"] if t["id"]=="bass")
    assert bass["events"]==[]
    assert bass["hard_constraint"]["forbidden_role"]=="bass"
