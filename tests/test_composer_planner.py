import json
from copy import deepcopy
from pathlib import Path
from _paths import SOURCE_ROOT
import pytest

from code_composer.agent.composition_brief import (
    brief_from_dict, BriefValidationError
)
from code_composer.agent.composer_planner import (
    compile_brief, apply_composer_plan, plan_to_dict
)


def _paths():
    root=Path(__file__).resolve().parents[1]
    return root/root.name if False else root


def _seed():
    root=Path(__file__).resolve().parents[1]
    return json.loads((root/'tests/fixtures/topline_ir.json').read_text())


def _brief_dict():
    root=Path(__file__).resolve().parents[1]
    return json.loads((root/'tests/fixtures/composition_brief.json').read_text())


def test_agent_authored_brief_compiles_deterministically():
    seed=_seed(); brief=brief_from_dict(_brief_dict())
    a=compile_brief(seed,brief); b=compile_brief(seed,brief)
    assert plan_to_dict(a)==plan_to_dict(b)
    out=apply_composer_plan(seed,a)
    assert out['transport']['bpm']==90
    assert out['tonal']=={'root':'E','scale':'natural_minor'}
    assert out['materials']['progressions']['home']['degrees']==[1,4,6,5]
    assert out['materials']['motifs']['main']['intervals']==[0,4,6,5,3,2,1,0]
    assert out['composer_plan']['source']=='agent_authored_composition_brief'


def test_hard_constraint_conflict_is_rejected():
    data=_brief_dict(); data['transport']['bpm']=96
    with pytest.raises(BriefValidationError):
        compile_brief(_seed(),brief_from_dict(data))


def test_forbidden_foreground_role_is_rejected():
    data=_brief_dict()
    data['orchestration']['sections']['final']={'foreground_mode':'topline'}
    with pytest.raises(BriefValidationError):
        compile_brief(_seed(),brief_from_dict(data))


def test_transition_and_prefill_are_compiled_without_semantic_inference():
    seed=_seed(); brief=brief_from_dict(_brief_dict())
    out=apply_composer_plan(seed,compile_brief(seed,brief))
    assert out['arrangement']['profiles']['final']['entry_gain']==0.05
    assert out['arrangement']['profiles']['final']['entry_soften_beats']==2.5
    assert out['rhythm_engine']['section_profiles']['verse']['fill']>=0.95


def test_canonical_planner_contains_no_style_vocabulary_tables():
    root=Path(__file__).resolve().parents[1]
    text=(SOURCE_ROOT/'agent/composer_planner.py').read_text()
    forbidden=('STYLE_PRESETS','STYLE_MATERIALS','STYLE_ALIASES','parse_composer_intent','mood_map')
    assert all(token not in text for token in forbidden)
def test_brief_can_replace_seed_form_structure():
    data=_brief_dict()
    data['form']['sections']=[
        {'id':'intro','bars':2,'energy':0.22},
        {'id':'main','bars':4,'energy':0.68},
        {'id':'final','bars':4,'energy':0.96},
    ]
    data['orchestration']['sections']={
        'intro':{'foreground_mode':'none'},
        'main':{'foreground_mode':'none'},
        'final':{'foreground_mode':'sparse','sparse_role':'lead','sparse_density_scale':0.22},
    }
    data['harmony']['sections']={}
    data['rhythm']['section_profiles']={}
    data['development']['sections']={
        'intro':{'stage':'establish'},
        'main':{'stage':'develop'},
        'final':{'stage':'culminate'},
    }
    data['transitions']={'main':{'entry_gain':0.5,'entry_soften_beats':0.75},'final':{'entry_gain':0.1,'entry_soften_beats':1.5}}
    brief=brief_from_dict(data)
    plan=compile_brief(_seed(),brief)
    out=apply_composer_plan(_seed(),plan)
    assert [(s['id'],s['start_bar'],s['bars']) for s in out['form']]==[
        ('intro',0,2),('main',2,4),('final',6,4)
    ]
