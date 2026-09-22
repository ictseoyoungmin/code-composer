import json
from copy import deepcopy
from pathlib import Path

import pytest

from code_composer.agent.composition_brief import brief_from_dict, BriefValidationError
from code_composer.agent.composer_planner import compile_brief, apply_composer_plan
from code_composer.composition.arrange import arrange_ir
from code_composer.analysis.form_development_analysis import analyze_form_development
from code_composer.validation_contracts import validate_runtime_extensions, ContractValidationError

ROOT=Path(__file__).resolve().parents[1]


def _seed():
    return json.loads((ROOT/'tests/fixtures/topline_ir.json').read_text())


def _brief():
    return json.loads((ROOT/'tests/fixtures/composition_brief.json').read_text())


def _with_variants(data):
    data=deepcopy(data)
    data['materials']['motif_variants']={
        'verse_shape':{
            'intervals':[0,4,6,5,3,2,1,0],
            'rhythm':[.5,.5,.5,.5,.5,.5,.5,.5],
            'identity_floor':.90,
            'identity_hard_min':.70,
        },
        'final_lift':{
            'intervals':[0,4,6,7,5,3,2,0],
            'rhythm':[.5,.5,.5,.5,.5,.5,.5,.5],
            'identity_floor':.62,
            'identity_hard_min':.45,
        },
    }
    data['development']['families']={'arc':['verse','final']}
    data['development']['sections']['verse']['motif_variant']='verse_shape'
    data['development']['sections']['final']['motif_variant']='final_lift'
    data['orchestration']['sections']['verse']={'foreground_mode':'lead'}
    data['orchestration']['sections']['final']={'foreground_mode':'lead'}
    return data


def test_brief_materializes_explicit_section_motif_variants():
    data=_with_variants(_brief())
    brief=brief_from_dict(data)
    out=apply_composer_plan(_seed(),compile_brief(_seed(),brief))
    assert out['arrangement_development']['sections']['verse']['motif_variant']=='verse_shape'
    assert out['arrangement_development']['sections']['final']['motif_variant']=='final_lift'
    assert out['materials']['motifs']['verse_shape']['source_motif_id']=='main'
    assert out['materials']['motifs']['final_lift']['identity']['score'] > .45
    assert out['materials']['motifs']['final_lift']['identity_hard_min']==.45


def test_unknown_motif_variant_reference_is_rejected_in_brief():
    data=_brief()
    data['development']['sections']['verse']['motif_variant']='ghost'
    with pytest.raises(BriefValidationError,match='unknown motif variant'):
        compile_brief(_seed(),brief_from_dict(data))


def test_explicit_identity_hard_min_rejects_unrelated_variant():
    data=_brief()
    data['materials']['motif_variants']={
        'unrelated':{
            'intervals':[0,-5,7,-4,8,-3,9,-2],
            'rhythm':[1.5,.25,.25,1.5,.25,.25,1.5,.25],
            'identity_floor':.80,
            'identity_hard_min':.75,
        }
    }
    data['development']['sections']['final']['motif_variant']='unrelated'
    with pytest.raises(BriefValidationError,match='below hard minimum'):
        compile_brief(_seed(),brief_from_dict(data))


def test_arranger_uses_section_variant_and_reports_lineage():
    data=_with_variants(_brief())
    planned=apply_composer_plan(_seed(),compile_brief(_seed(),brief_from_dict(data)))
    resolved=arrange_ir(planned)
    lead=next(t for t in resolved['tracks'] if t['id']=='lead')
    by_section={m['section_id']:m for m in lead['arrangement_meta']}
    assert by_section['verse']['motif_id']=='verse_shape'
    assert by_section['final']['motif_id']=='final_lift'
    assert by_section['final']['motif_identity']['score'] > .45
    assert all(e['motif_id']=='verse_shape' for e in lead['events'] if e['section_id']=='verse')
    assert all(e['motif_lineage']['source_motif_id']=='main' for e in lead['events'])
    report=analyze_form_development(resolved)
    row={r['section_id']:r for r in report['sections']}
    assert row['verse']['motif_id']=='verse_shape'
    assert row['final']['motif_id']=='final_lift'
    assert report['families']['arc']['distinct_motifs'] == 2


def test_runtime_unknown_variant_is_rejected_before_arrangement():
    ir=_seed()
    ir['arrangement_development']={
        'enabled':True,'families':{},'default':{},
        'sections':{'verse':{'stage':'develop','motif_variant':'ghost'},'final':{'stage':'culminate'}},
    }
    with pytest.raises(ContractValidationError,match='unknown motif'):
        validate_runtime_extensions(ir)


def test_no_variant_surface_preserves_existing_arrangement_exactly():
    ir=_seed()
    control=arrange_ir(ir)
    treatment=deepcopy(ir)
    treatment['arrangement_development']={
        'enabled':True,
        'families':{},
        'default':{'stage':'develop'},
        'sections':{sid:{'stage':'develop'} for sid in ('verse','final')},
    }
    # Development stage alone must not choose or mutate motif material.
    out=arrange_ir(treatment)
    c_lead=next(t for t in control['tracks'] if t['id']=='lead')
    o_lead=next(t for t in out['tracks'] if t['id']=='lead')
    assert [(e['start_beat'],e['duration_beats'],e['midi'],e['velocity']) for e in c_lead['events']] == [
        (e['start_beat'],e['duration_beats'],e['midi'],e['velocity']) for e in o_lead['events']
    ]
