import json
from pathlib import Path

import numpy as np
import pytest

from code_composer.audio.piano_design import (
    PianoDesignError,
    resolve_piano_design,
    validate_piano_design,
)
from code_composer.audio.piano import render_piano_note
from code_composer.agent.composition_brief import brief_from_dict, validate_brief, BriefValidationError
from code_composer.agent.composer_planner import compile_brief, apply_composer_plan


def _design(categories=None, controls=None):
    return {
        'kind':'piano',
        'piano_design':{
            'categories':categories or {},
            'controls':controls or {},
        }
    }


def _seed():
    root=Path(__file__).resolve().parents[1]
    return json.loads((root/'tests/fixtures/topline_ir.json').read_text())


def _brief(patch):
    return {
      'source_prompt':'piano physical character test','concept':'category/control split',
      'hard_constraints':{},
      'transport':{'bpm':96,'beats_per_bar':4},
      'tonal':{'root':'D','scale':'major'},
      'form':{'sections':[{'id':'main','bars':4,'energy':.7}]},
      'materials':{'progression':[1,5,6,4],'motif':[0,2,4,2],'motif_rhythm':[.5,.5,.5,.5]},
      'rhythm':{
        'groove':{'steps_per_bar':16,'roles':{'kick':[0]*16,'snare':[0]*16,'hat':[0]*16}},
        'section_profiles':{'main':{'density':0,'kick':0,'snare':0,'hat':0,'fill':0}},
      },
      'orchestration':{'sections':{'main':{'foreground_mode':'lead'}}},
      'harmony':{'colors':['triad']},
      'development':{'sections':{'main':{'stage':'establish'}}},
      'transitions':{},
      'sound_palette':{'roles':{'lead':{'patch':patch}}},
    }


def test_categories_and_numeric_controls_are_separate_namespaces():
    patch=_design(
        {'body':'concert_grand','hammer':'soft_felt'},
        {'stereo_width':.31,'base_decay_s':2.75,'hammer_noise_gain':.041},
    )
    resolved=resolve_piano_design(patch)
    meta=resolved['piano_design_resolved']
    assert meta['categories']['body']=='concert_grand'
    assert meta['categories']['hammer']=='soft_felt'
    assert meta['controls']['stereo_width']==.31
    # Numeric controls are absolute and win over category-derived baselines.
    assert resolved['piano_graph']['strings']['stereo_width']==.31
    assert resolved['piano_graph']['strings']['base_decay_s']==2.75
    assert resolved['piano_graph']['hammer']['noise_gain']==.041


def test_category_is_not_a_subjective_vocabulary_slot():
    with pytest.raises(PianoDesignError):
        validate_piano_design({'categories':{'body':'warm'},'controls':{}})


def test_unknown_numeric_control_is_rejected():
    with pytest.raises(PianoDesignError):
        validate_piano_design({'categories':{},'controls':{'warmth':.8}})


def test_legacy_graph_and_new_design_cannot_be_mixed():
    patch=_design()
    patch['piano_graph']={'strings':{}}
    with pytest.raises(PianoDesignError):
        resolve_piano_design(patch)


def test_category_topology_changes_render_without_numeric_overrides():
    a=_design({'body':'concert_grand','hammer':'medium_felt','stringing':'concert','soundboard':'open_board','perspective':'player'})
    b=_design({'body':'upright','hammer':'medium_felt','stringing':'compact','soundboard':'dry_board','perspective':'close'})
    xa=render_piano_note(60,.8,22050,a,velocity=.7)
    xb=render_piano_note(60,.8,22050,b,velocity=.7)
    n=min(len(xa),len(xb))
    corr=np.corrcoef(xa[:n,0],xb[:n,0])[0,1]
    assert corr < .985
    ra=resolve_piano_design(a)['piano_graph']
    rb=resolve_piano_design(b)['piano_graph']
    assert ra['strings']['base_decay_s'] != rb['strings']['base_decay_s']


def test_direct_control_changes_same_category_render():
    base={'body':'studio_grand','hammer':'medium_felt','stringing':'concert','soundboard':'balanced_board','perspective':'player'}
    a=_design(base,{'detune_cents':.25,'stereo_width':.25})
    b=_design(base,{'detune_cents':1.6,'stereo_width':.92})
    xa=render_piano_note(64,.8,22050,a,velocity=.7)
    xb=render_piano_note(64,.8,22050,b,velocity=.7)
    n=min(len(xa),len(xb))
    assert not np.array_equal(xa[:n],xb[:n])


def test_brief_compiler_resolves_piano_design_to_graph():
    seed=_seed()
    patch=_design(
        {'body':'upright','hammer':'dense_felt','stringing':'compact','soundboard':'dry_board','perspective':'close'},
        {'output_gain':.54,'stereo_width':.38},
    )
    brief=brief_from_dict(_brief(patch))
    validate_brief(brief,seed)
    ir=apply_composer_plan(seed,compile_brief(seed,brief))
    inst_id=ir['arrangement']['roles']['lead']['instrument']
    inst=ir['instruments'][inst_id]
    assert 'piano_design' not in inst
    assert 'piano_graph' in inst
    assert inst['piano_design_resolved']['categories']['body']=='upright'
    assert inst['piano_graph']['strings']['stereo_width']==.38


def test_brief_rejects_category_control_collision_that_breaks_invariant():
    seed=_seed()
    patch=_design(
        {'hammer':'soft_felt'},
        {'hammer_low_cutoff_hz':5000,'hammer_soft_high_cutoff_hz':3000},
    )
    brief=brief_from_dict(_brief(patch))
    with pytest.raises(BriefValidationError):
        validate_brief(brief,seed)
