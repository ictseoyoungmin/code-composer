import json
from pathlib import Path
from _paths import SCHEMA_ROOT, PACKAGED_SCHEMA_ROOT, SOURCE_ROOT

import jsonschema

from code_composer.agent.composition_brief import brief_from_dict
from code_composer.agent.composer_planner import compile_brief, apply_composer_plan
from code_composer.audio.piano_design import validate_piano_design, resolve_piano_design
from code_composer.pipeline.validation import validate_ir

ROOT=Path(__file__).resolve().parents[1]


def _json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def test_checked_in_examples_are_valid_current_ir():
    for rel in ('examples/basic/demo_ir.json','examples/basic/high_level_ir.json'):
        validate_ir(_json(ROOT/rel))


def test_high_level_example_is_compiler_output():
    seed=_json(ROOT/'examples/basic/seed_ir.json')
    brief=brief_from_dict(_json(ROOT/'examples/basic/composition_brief.json'))
    plan=compile_brief(seed,brief)
    expected=apply_composer_plan(seed,plan)
    expected['meta']['title']='Night Road — Compiled Composition Brief Example'
    expected['meta']['version']='1.15.5'
    assert expected == _json(ROOT/'examples/basic/high_level_ir.json')


def test_composition_brief_schema_matches_example():
    schema=_json(SCHEMA_ROOT/'composition_brief.schema.json')
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(_json(ROOT/'examples/basic/composition_brief.json'),schema)


def test_piano_design_schema_matches_runtime_optional_surfaces():
    schema=_json(SCHEMA_ROOT/'piano_design.schema.json')
    jsonschema.Draft202012Validator.check_schema(schema)
    designs=[
        {},
        {'categories':{'body':'concert_grand'}},
        {'controls':{'stereo_width':0.4}},
        _json(ROOT/'examples/concert_piano_patch.json')['piano_design'],
        _json(ROOT/'examples/upright_piano_patch.json')['piano_design'],
        _json(ROOT/'examples/electric_tine_piano_patch.json')['piano_design'],
        _json(ROOT/'examples/electric_reed_piano_patch.json')['piano_design'],
        _json(ROOT/'examples/electric_fm_piano_patch.json')['piano_design'],
    ]
    for design in designs:
        jsonschema.validate(design,schema)
        assert validate_piano_design(design) is True


def test_representative_piano_examples_use_current_authoring_surface():
    for rel in (
        'examples/concert_piano_patch.json','examples/upright_piano_patch.json',
        'examples/electric_tine_piano_patch.json','examples/electric_reed_piano_patch.json',
        'examples/electric_fm_piano_patch.json',
    ):
        patch=_json(ROOT/rel)
        assert patch['kind']=='piano'
        assert 'piano_design' in patch
        assert 'piano_graph' not in patch
        resolved=resolve_piano_design(patch)
        assert ('piano_graph' in resolved) ^ ('electric_piano_graph' in resolved)
        assert 'piano_design' not in resolved


def test_packaged_reference_surface_is_schema_only_and_agent_skill_excludes_musical_examples():
    for p in sorted(PACKAGED_SCHEMA_ROOT.glob("*.json")):
        assert (SCHEMA_ROOT/p.name).read_bytes() == p.read_bytes()
    ref_examples=SOURCE_ROOT/"reference"/"examples"
    assert not list(ref_examples.glob("*.json"))
    text=(ref_examples/"README.md").read_text(encoding="utf-8")
    assert "does not ship finished" in text
