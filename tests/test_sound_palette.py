import json
from copy import deepcopy
from pathlib import Path
import pytest

from code_composer.agent.composition_brief import brief_from_dict, BriefValidationError
from code_composer.agent.composer_planner import compile_brief, apply_composer_plan
from code_composer.analysis.sound_palette_analysis import analyze_sound_palette


def _fixture():
    root=Path(__file__).resolve().parents[1]
    return json.loads((root/'tests/fixtures/topline_ir.json').read_text())


def _brief_dict():
    root=Path(__file__).resolve().parents[1]
    # Reuse a validated dogfood-like minimal brief fixture and author sound explicitly.
    return {
      'source_prompt':'warm wide pad, short glassy lead',
      'concept':'palette validation fixture',
      'hard_constraints':{'bpm':96,'root':'D','scale':'natural_minor','forbidden_roles':[]},
      'transport':{'bpm':96,'beats_per_bar':4},
      'tonal':{'root':'D','scale':'natural_minor'},
      'form':{'sections':[{'id':'verse','bars':2,'energy':.5},{'id':'final','bars':2,'energy':.85}]},
      'materials':{'progression':[1,6,3,7],'motif':[0,2,4,2],'motif_rhythm':[.5,.5,.5,.5]},
      'rhythm':{'groove':{'steps_per_bar':16,'roles':{
        'kick':[1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0],
        'snare':[0,0,0,0,.8,0,0,0,0,0,0,0,.8,0,0,0],
        'hat':[0,0,.4,0,0,0,.4,0,0,0,.4,0,0,0,.4,0]}},
        'swing':.02,'section_profiles':{}},
      'orchestration':{'sections':{'verse':{'foreground_mode':'none'},'final':{'foreground_mode':'lead'}}},
      'harmony':{'colors':['add9','seventh']},
      'development':{'sections':{'verse':{'stage':'establish'},'final':{'stage':'culminate'}}},
      'transitions':{'final':{'entry_gain':.3,'entry_soften_beats':1.0}},
      'sound_palette':{'roles':{
        'pad':{'character':'wide soft harmonic bed','patch':{'graph':{
          'oscillators':[{'waveform':'sine','gain':.55},{'waveform':'triangle','gain':.3,'octave':1},{'waveform':'saw','gain':.15,'detune_cents':-5}],
          'unison':{'voices':5,'detune_cents':9,'stereo_width':.82},
          'envelope':{'attack':.42,'decay':.36,'sustain':.76,'release':.85},
          'filter':{'type':'lowpass','cutoff':2600,'env_amount':.12},
          'lfo':{'rate_hz':.17,'pitch_cents':3.0,'amp_depth':.02},
          'waveshaper':{'type':'tanh','drive':1.04},'output_gain':.52}}},
        'lead':{'character':'short glassy answer','patch':{'graph':{
          'oscillators':[{'waveform':'triangle','gain':.55},{'waveform':'sine','gain':.35,'octave':1},{'waveform':'square','gain':.1}],
          'unison':{'voices':2,'detune_cents':4,'stereo_width':.24},
          'envelope':{'attack':.006,'decay':.07,'sustain':.44,'release':.09},
          'filter':{'type':'bandpass','low_cutoff':420,'high_cutoff':5600},
          'waveshaper':{'type':'softclip','drive':1.18},'declick':{'ms':3.0},'output_gain':.58}}}
      }},
      'rationale':['sound is authored numerically, not inferred from words']
    }


def test_palette_absent_preserves_seed_instruments():
    seed=_fixture(); data=_brief_dict(); data.pop('sound_palette')
    before=deepcopy(seed['instruments'])
    out=apply_composer_plan(seed,compile_brief(seed,brief_from_dict(data)))
    assert out['instruments']==before


def test_agent_palette_routes_to_role_instrument_ids():
    seed=_fixture(); brief=brief_from_dict(_brief_dict())
    out=apply_composer_plan(seed,compile_brief(seed,brief))
    assert out['instruments']['pad']['graph']['unison']['voices']==5
    assert out['instruments']['lead']['graph']['filter']['type']=='bandpass'
    q=analyze_sound_palette(out)
    assert q['palette_source']=='agent_authored'
    assert q['roles']['pad']['stereo_width']==.82


def test_unsafe_palette_is_rejected():
    seed=_fixture(); data=_brief_dict()
    data['sound_palette']['roles']['lead']['patch']['graph']['oscillators'][0]['waveform']='unknown_wave'
    with pytest.raises(BriefValidationError):
        compile_brief(seed,brief_from_dict(data))


def test_unavailable_role_is_rejected():
    seed=_fixture(); data=_brief_dict()
    seed['arrangement']['roles'].pop('arp')
    data['sound_palette']['roles']['arp']={'patch':{'graph':{
      'oscillators':[{'waveform':'sine','gain':1}],
      'envelope':{'attack':.01,'decay':.1,'sustain':.5,'release':.1},
      'output_gain':.5}}}
    with pytest.raises(BriefValidationError):
        compile_brief(seed,brief_from_dict(data))


def test_agent_authored_drum_graph_compiles():
    seed=_fixture(); data=_brief_dict()
    data['sound_palette']['roles']['drums']={'character':'dry tight kit','patch':{
      'kind':'percussion','drum_graph':{
        'kick':{'pitch_start_hz':145,'pitch_end_hz':52,'pitch_decay_s':.04,'body_decay_s':.08,'sub_decay_s':.11,'body_gain':.9,'sub_gain':.08,'click_gain':.04,'click_hz':1900,'drive':1.05,'output_gain':.82},
        'snare':{'body_hz':205,'body2_hz':390,'body_gain':.3,'body2_gain':.22,'body_decay_s':.065,'noise_low_hz':1500,'noise_high_hz':7600,'noise_gain':.38,'noise_decay_s':.05,'crack_hz':3100,'crack_gain':.045,'crack_decay_s':.012,'lowpass_hz':9000,'drive':1.04,'output_gain':.5},
        'hat':{'metal_freqs':[6100,7600,9400,11700],'metal_gains':[1,.66,.38,.2],'metal_gain':.28,'noise_gain':.12,'decay_s':.022,'noise_highpass_hz':5800,'noise_lowpass_hz':15000,'output_highpass_hz':4900,'drive':1.02,'output_gain':.3}
      }}}
    out=apply_composer_plan(seed,compile_brief(seed,brief_from_dict(data)))
    assert out['instruments']['drums']['drum_graph']['kick']['pitch_end_hz']==52
