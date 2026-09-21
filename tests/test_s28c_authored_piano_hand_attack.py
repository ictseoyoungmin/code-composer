import copy
import numpy as np
import pytest

from code_composer.render import _piano_events_with_authored_attack, _render_dry_track
from code_composer.audio.piano_design import resolve_piano_design
from code_composer.presets import materialize_preset
from code_composer.validation_contracts import validate_runtime_extensions, ContractValidationError


def _patch():
    return resolve_piano_design(materialize_preset('piano.concert_grand_natural', role='piano'))


def test_absent_authored_attack_is_identity():
    events=[{'midi':60,'start_beat':1.0,'duration_beats':.5,'velocity':.7}]
    assert _piano_events_with_authored_attack(events,60/120)==events


def test_explicit_attack_offsets_shift_only_note_onsets():
    beat_s=60/120
    events=[
        {'midi':38,'start_beat':1.0,'duration_beats':1.0,'velocity':.7,'performance':{'piano_attack_offset_ms':0}},
        {'midi':50,'start_beat':1.0,'duration_beats':1.0,'velocity':.7,'performance':{'piano_attack_offset_ms':4}},
        {'midi':62,'start_beat':1.0,'duration_beats':1.0,'velocity':.7,'performance':{'piano_attack_offset_ms':11}},
        {'midi':74,'start_beat':1.0,'duration_beats':1.0,'velocity':.7,'performance':{'piano_attack_offset_ms':15}},
    ]
    got=_piano_events_with_authored_attack(events,beat_s)
    offsets=[(g['start_beat']-1.0)*beat_s*1000 for g in got]
    assert np.allclose(offsets,[0,4,11,15],atol=1e-9)
    assert [g['duration_beats'] for g in got]==[1,1,1,1]
    assert events[1]['start_beat']==1.0


def test_piano_control_is_never_shifted():
    control={'event_type':'piano_control','control':'sustain_pedal','start_beat':0.0,'duration_beats':1.0,
             'points':[{'offset_beats':0.0,'position':1.0},{'offset_beats':1.0,'position':1.0}]}
    assert _piano_events_with_authored_attack([control],.5)[0]==control


def test_attack_offset_is_deterministic_and_independent_of_global_seed():
    patch=_patch(); beat_s=60/92; n=int(2*beat_s*24000)
    event={'midi':60,'start_beat':.5,'duration_beats':.4,'velocity':.72,
           'performance':{'piano_attack_offset_ms':15.0}}
    def run(seed):
        ir={'meta':{'global_seed':seed},'instruments':{'p':patch}}
        track={'id':'piano','instrument':'p','gain':1.0,'pan':0.0,'events':[copy.deepcopy(event)]}
        return _render_dry_track(ir,track,n,24000,beat_s,graph_mode=False)
    a=run(10); b=run(10)
    assert np.array_equal(a,b)


def test_validator_accepts_authored_hand_roll_range():
    ir={'transport':{'bpm':92},'instruments':{'p':_patch()},'tracks':[{'id':'p','instrument':'p','events':[
        {'midi':38,'start_beat':1.0,'duration_beats':.5,'velocity':.7,'performance':{'piano_attack_offset_ms':0}},
        {'midi':74,'start_beat':1.0,'duration_beats':.5,'velocity':.7,'performance':{'piano_attack_offset_ms':15}},
    ]}]}
    validate_runtime_extensions(ir)


def test_validator_rejects_excessive_attack_offset():
    ir={'transport':{'bpm':92},'instruments':{'p':_patch()},'tracks':[{'id':'p','instrument':'p','events':[
        {'midi':60,'start_beat':1.0,'duration_beats':.5,'velocity':.7,'performance':{'piano_attack_offset_ms':25}},
    ]}]}
    with pytest.raises(ContractValidationError): validate_runtime_extensions(ir)


def test_validator_rejects_negative_offset_before_piece_start():
    ir={'transport':{'bpm':92},'instruments':{'p':_patch()},'tracks':[{'id':'p','instrument':'p','events':[
        {'midi':60,'start_beat':0.0,'duration_beats':.5,'velocity':.7,'performance':{'piano_attack_offset_ms':-5}},
    ]}]}
    with pytest.raises(ContractValidationError): validate_runtime_extensions(ir)
