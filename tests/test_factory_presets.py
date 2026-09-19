import json
from pathlib import Path
import pytest

from code_composer.presets import list_presets, get_preset, materialize_preset, PresetError
from code_composer.agent.composition_brief import brief_from_dict, validate_brief
from code_composer.agent.composer_planner import compile_brief, apply_composer_plan

ROOT=Path(__file__).resolve().parents[1]


def _seed():
    return json.loads((ROOT/'tests/fixtures/topline_ir.json').read_text())


def _brief(preset_id, **extra):
    spec={'preset_id':preset_id, **extra}
    return {
      'source_prompt':'preset-system protocol test', 'concept':'factory preset materialization',
      'hard_constraints':{}, 'transport':{'bpm':96,'beats_per_bar':4},
      'tonal':{'root':'D','scale':'major'},
      'form':{'sections':[{'id':'main','bars':2,'energy':.7}]},
      'materials':{'progression':[1,5,6,4],'motif':[0,2,4,2],'motif_rhythm':[.5,.5,.5,.5]},
      'rhythm':{'groove':{'steps_per_bar':16,'roles':{'kick':[0]*16,'snare':[0]*16,'hat':[0]*16}},'section_profiles':{'main':{'density':0,'kick':0,'snare':0,'hat':0,'fill':0}}},
      'orchestration':{'sections':{'main':{'foreground_mode':'lead'}}},
      'harmony':{'colors':['triad']}, 'development':{'sections':{'main':{'stage':'establish'}}},
      'transitions':{}, 'sound_palette':{'roles':{'lead':spec}}
    }


def test_factory_catalog_is_small_versioned_and_contains_no_musical_content():
    presets=list_presets()
    assert 4 <= len(presets) <= 19
    assert any(x['preset_id']=='bowed.violin.synthetic_warm' for x in presets)
    for meta in presets:
        assert meta['version']=='1.0.0'
        assert meta['musical_content'] is False
        assert 'patch' not in meta
        assert meta['strengths'] and meta['limitations'] and meta['recommended_roles']


def test_materialization_is_deterministic_and_records_exact_provenance():
    a=materialize_preset('bowed.violin.synthetic_warm',role='lead')
    b=materialize_preset('bowed.violin.synthetic_warm',role='lead')
    assert a==b
    assert a['preset_provenance']=={'preset_id':'bowed.violin.synthetic_warm','preset_version':'1.0.0','materialized':True}
    assert a['bowed_string_graph']['vibrato']['depth_cents']==17


def test_song_local_override_changes_materialized_patch_without_mutating_factory():
    base=materialize_preset('bowed.violin.synthetic_warm',role='lead')
    changed=materialize_preset('bowed.violin.synthetic_warm',role='lead',patch_overrides={'bowed_string_graph':{'vibrato':{'depth_cents':28}}})
    assert base['bowed_string_graph']['vibrato']['depth_cents']==17
    assert changed['bowed_string_graph']['vibrato']['depth_cents']==28
    assert get_preset('bowed.violin.synthetic_warm')['patch']['bowed_string_graph']['vibrato']['depth_cents']==17


def test_identity_fields_cannot_be_overridden():
    with pytest.raises(PresetError):
        materialize_preset('bowed.violin.synthetic_warm',role='lead',patch_overrides={'engine':'generic'})


def test_brief_can_select_preset_and_music_ir_materializes_full_patch():
    seed=_seed(); brief=brief_from_dict(_brief('bowed.violin.synthetic_warm'))
    validate_brief(brief,seed)
    ir=apply_composer_plan(seed,compile_brief(seed,brief))
    iid=ir['arrangement']['roles']['lead']['instrument']
    patch=ir['instruments'][iid]
    assert patch['engine']=='bowed_string'
    assert patch['bowed_string_graph']['body']['resonances_hz']
    assert patch['preset_provenance']['preset_id']=='bowed.violin.synthetic_warm'
    assert ir['sound_palette_resolved']['roles']['lead']['preset_id']=='bowed.violin.synthetic_warm'


def test_piano_preset_materializes_then_resolves_piano_design():
    seed=_seed(); brief=brief_from_dict(_brief('piano.concert_grand'))
    validate_brief(brief,seed)
    ir=apply_composer_plan(seed,compile_brief(seed,brief))
    iid=ir['arrangement']['roles']['lead']['instrument']; patch=ir['instruments'][iid]
    assert patch['kind']=='piano' and 'piano_graph' in patch and 'piano_design' not in patch
    assert patch['preset_provenance']['preset_id']=='piano.concert_grand'


def test_catalog_filters_are_capability_metadata_not_style_mapping():
    bowed=list_presets(engine='bowed_string',role='lead')
    assert [x['preset_id'] for x in bowed]==['bowed.violin.synthetic_warm']
    assert list_presets(family='violin')[0]['expression_capabilities']['vibrato_depth_cents'] is True

def test_agent_catalog_matches_runtime_metadata_exactly():
    catalog=json.loads((ROOT/'skills/code-composer/kit/presets/CATALOG.json').read_text())
    assert catalog['presets']==list_presets()
    assert all('patch' not in x for x in catalog['presets'])

def test_preset_cli_list_and_show(capsys):
    from code_composer.app.presets_cli import main
    assert main(['list','--engine','bowed_string'])==0
    listed=json.loads(capsys.readouterr().out)
    assert listed[0]['preset_id']=='bowed.violin.synthetic_warm' and 'patch' not in listed[0]
    assert main(['show','piano.concert_grand'])==0
    shown=json.loads(capsys.readouterr().out)
    assert shown['engine']=='piano' and 'patch' not in shown


def test_preset_cli_materialize(capsys):
    from code_composer.app.presets_cli import main
    assert main(['materialize','generic.clean_lead','--role','lead'])==0
    patch=json.loads(capsys.readouterr().out)
    assert patch['preset_provenance']['preset_id']=='generic.clean_lead'
    assert patch['graph']['oscillators']


def test_agent_surface_exposes_factory_preset_capability():
    surface=json.loads((ROOT/'skills/code-composer/kit/surface.json').read_text())
    assert surface['capabilities']['presets']=={
        'entrypoint':'code-composer-presets',
        'workflow':'workflows/select-preset.md',
    }
    assert surface['factory_presets']['policy']=='sonic capability only; no musical content; fully materialized into canonical Music IR'
