import numpy as np
import pytest

from code_composer.audio.piano import render_piano_note
from code_composer.analysis.piano_analysis import spectral_centroid,stereo_balance,tail_rms,decay_ratio
from code_composer.agent.composition_brief import brief_from_dict,validate_brief,BriefValidationError


def _patch():
    return {
        'kind':'piano',
        'piano_graph':{
            'strings':{
                'max_partials':16,'base_decay_s':3.2,'decay_keytrack':.55,
                'partial_decay_power':.58,'spectral_rolloff':1.36,
                'velocity_brightness':.78,'inharmonicity':.00016,
                'low_strings':1,'mid_strings':2,'high_strings':3,
                'detune_cents':.65,'stereo_width':.72,
            },
            'hammer':{
                'gain':.12,'noise_gain':.06,'decay_s':.018,
                'low_cutoff_hz':700,'soft_high_cutoff_hz':3000,
                'hard_high_cutoff_hz':12000,'tonal_gain':.035,
            },
            'damper':{'release_s':.18,'pedal_release_s':1.8},
            'resonance':{'gain':.022,'pedal_gain':.08,'decay_s':2.6},
            'soundboard':{'gain':.018,'pedal_gain':.045,'cross':.32},
            'body_filter':{'soft_cutoff_hz':3600,'hard_cutoff_hz':15000},
            'declick_ms':.35,'output_gain':.62,
        }
    }


def test_velocity_opens_piano_brightness():
    sr=44100; p=_patch()
    soft=render_piano_note(60,1.0,sr,p,velocity=.25)
    hard=render_piano_note(60,1.0,sr,p,velocity=.92)
    c0=spectral_centroid(soft,sr,.35)
    c1=spectral_centroid(hard,sr,.35)
    assert c1 > c0*1.18


def test_register_changes_image_and_spectrum():
    sr=44100; p=_patch()
    low=render_piano_note(40,1.0,sr,p,velocity=.72)
    high=render_piano_note(80,1.0,sr,p,velocity=.72)
    assert stereo_balance(low) < -0.05
    assert stereo_balance(high) > 0.05
    assert spectral_centroid(high,sr,.35) > spectral_centroid(low,sr,.35)*1.4


def test_pedal_extends_tail():
    sr=44100; p=_patch()
    dry=render_piano_note(60,.7,sr,p,velocity=.7,performance={'pedal':False})
    wet=render_piano_note(60,.7,sr,p,velocity=.7,performance={'pedal':True})
    # Compare a fixed late region common in musical note-off behavior.
    i=int(.78*sr); j=int(.86*sr)
    dry_tail=float(np.sqrt(np.mean(dry[i:min(j,len(dry))]**2)))
    wet_tail=float(np.sqrt(np.mean(wet[i:min(j,len(wet))]**2)))
    assert len(wet)>len(dry)
    assert wet_tail > dry_tail*1.35


def test_piano_render_is_deterministic():
    p=_patch()
    a=render_piano_note(64,.9,44100,p,velocity=.63,performance={'pedal':True})
    b=render_piano_note(64,.9,44100,p,velocity=.63,performance={'pedal':True})
    assert np.array_equal(a,b)


def _brief(seed_ir,patch):
    # Build minimum valid brief by reusing fixture musical data but explicitly piano-designing lead.
    return {
      'source_prompt':'piano engine validator test','concept':'deterministic piano',
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


def test_brief_validator_accepts_piano_patch(topline_ir_fixture=None):
    import json
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    seed=json.loads((root/'tests/fixtures/topline_ir.json').read_text())
    brief=brief_from_dict(_brief(seed,_patch()))
    validate_brief(brief,seed)


def test_brief_validator_rejects_bad_pedal_release():
    import json
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    seed=json.loads((root/'tests/fixtures/topline_ir.json').read_text())
    bad=_patch(); bad['piano_graph']['damper']={'release_s':1.0,'pedal_release_s':.2}
    brief=brief_from_dict(_brief(seed,bad))
    with pytest.raises(BriefValidationError):
        validate_brief(brief,seed)


def test_composer_compiles_piano_patch_to_role_instrument():
    import json
    from pathlib import Path
    from code_composer.agent.composer_planner import compile_brief,apply_composer_plan
    root=Path(__file__).resolve().parents[1]
    seed=json.loads((root/'tests/fixtures/topline_ir.json').read_text())
    brief=brief_from_dict(_brief(seed,_patch()))
    plan=compile_brief(seed,brief)
    ir=apply_composer_plan(seed,plan)
    lead_inst=ir['arrangement']['roles']['lead']['instrument']
    assert ir['instruments'][lead_inst]['kind']=='piano'
    assert 'piano_graph' in ir['instruments'][lead_inst]


def test_low_register_rings_longer_than_treble():
    sr=44100; p=_patch()
    low=render_piano_note(40,1.2,sr,p,velocity=.70)
    high=render_piano_note(80,1.2,sr,p,velocity=.70)
    assert decay_ratio(low,sr) > decay_ratio(high,sr)*2.5
