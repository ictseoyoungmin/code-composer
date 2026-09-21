import copy
import hashlib
import numpy as np
import pytest

from code_composer.presets import get_preset, materialize_preset, list_presets
from code_composer.audio.percussion import render_drum_event
from code_composer.render import _render_dry_track
from code_composer.validation_contracts import validate_drum_control_events, ContractValidationError
from code_composer.analysis.drummer_performance_analysis import analyze_drummer_performance
from code_composer.export.midi import midi_bytes

SR=24000
BPM=120.0
BEAT_S=60.0/BPM
OLD='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_stateful_hihat'
NEW='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_continuous_hihat'


def _sha(x):
    return hashlib.sha256(np.asarray(x,dtype=np.float64).tobytes()).hexdigest()


def _rms(x):
    x=np.asarray(x,dtype=np.float64)
    return float(np.sqrt(np.mean(x*x)+1e-18)) if len(x) else 0.0


def _ev(kind,beat,vel=.82,dur=.12):
    return {'event_type':'drum','drum':kind,'start_beat':float(beat),'duration_beats':float(dur),'velocity':float(vel)}


def _ctrl(start,duration,points):
    return {
        'event_type':'drum_control','control':'hi_hat_pedal_openness',
        'start_beat':float(start),'duration_beats':float(duration),
        'points':[{'offset_beats':float(x),'openness':float(y)} for x,y in points],
    }


def _render_track(preset,events,*,room=False,n_s=3.0):
    patch=materialize_preset(preset,role='drums')
    if not room:
        patch=copy.deepcopy(patch)
        patch['drum_graph']['kit_integration']['enabled']=False
    ir={'meta':{'global_seed':271001},'instruments':{'drums':patch}}
    track={'id':'drums','instrument':'drums','events':list(events)}
    return _render_dry_track(ir,track,int(n_s*SR),SR,BEAT_S,graph_mode=True)


def _window(x,start_s,end_s):
    return x[int(start_s*SR):int(end_s*SR)]


def test_s27i_preset_is_opt_in_and_only_upgrades_s27h_hihat_state_block():
    ids=[x['preset_id'] for x in list_presets(engine='percussion')]
    assert NEW in ids
    a=get_preset(OLD)['patch']['drum_graph']
    b=get_preset(NEW)['patch']['drum_graph']
    assert {k:v for k,v in b.items() if k!='hi_hat_state'} == {k:v for k,v in a.items() if k!='hi_hat_state'}
    assert b['hi_hat_state']['closure'] == a['hi_hat_state']['closure']
    assert b['hi_hat_state']['model']=='authored_continuous_openness_v2'
    assert b['hi_hat_state']['continuous']['control']=='hi_hat_pedal_openness'


def test_s27i_direct_hit_sources_remain_byte_exact_to_s27h():
    a=materialize_preset(OLD,role='drums')
    b=materialize_preset(NEW,role='drums')
    kinds=('kick','ride','crash','hat_tight_closed','hat_closed','hat_half_open','hat_open','hat_pedal','hat_foot_splash','snare_rimshot','tom_floor')
    for i,kind in enumerate(kinds):
        x=render_drum_event(kind,.12,SR,.84,seed=410+i,patch=a)
        y=render_drum_event(kind,.12,SR,.84,seed=410+i,patch=b)
        assert _sha(x)==_sha(y),kind


def test_s27i_no_control_keeps_s27h_discrete_closure_byte_exact():
    events=[_ev('hat_open',0,.86),_ev('hat_pedal',.5,.68,.08),_ev('kick',1.0,.92)]
    assert _sha(_render_track(OLD,events)) == _sha(_render_track(NEW,events))


def test_s27i_gradual_curve_preserves_precontact_audio_and_reduces_tail_without_new_hit():
    base=[_ev('hat_open',0,.88)]
    curve=_ctrl(0,.75,[(0,1),(.25,1),(.50,.55),(.75,0)])
    old=_render_track(NEW,base)
    new=_render_track(NEW,base+[curve])
    contact_s=.25*BEAT_S
    pre=int((contact_s-.005)*SR)
    assert _sha(old[:pre])==_sha(new[:pre])
    assert _rms(_window(new,.42,.70)) < _rms(_window(old,.42,.70))*.35
    # Control event is non-audio: before contact there is no extra onset or click.
    assert np.max(np.abs(old[:pre]-new[:pre])) == 0.0


def test_s27i_partial_contact_retains_more_energy_than_full_close():
    hit=[_ev('hat_open',0,.88)]
    half=_ctrl(0,.75,[(0,1),(.20,1),(.75,.55)])
    full=_ctrl(0,.75,[(0,1),(.20,1),(.75,0)])
    yh=_render_track(NEW,hit+[half])
    yf=_render_track(NEW,hit+[full])
    assert _rms(_window(yh,.42,.70)) > _rms(_window(yf,.42,.70))*2.0


def test_s27i_reopening_reduces_future_loss_but_never_restores_dissipated_energy():
    hit=[_ev('hat_open',0,.90)]
    close_reopen=_ctrl(0,1.0,[(0,1),(.20,1),(.45,.12),(.70,.12),(1.0,1)])
    always_open=_ctrl(0,1.0,[(0,1),(1.0,1)])
    yr=_render_track(NEW,hit+[close_reopen])
    yo=_render_track(NEW,hit+[always_open])
    # After re-opening, remaining energy can ring but must stay below never-contacted source.
    assert _rms(_window(yr,.55,.78)) < _rms(_window(yo,.55,.78))*.55
    assert _rms(_window(yr,.62,.76)) > 0.0


def test_s27i_control_never_ducks_unrelated_kick_voice():
    curve=_ctrl(0,.75,[(0,1),(.25,1),(.75,0)])
    base=[_ev('hat_open',0,.86),curve]
    with_kick=base+[_ev('kick',.75,.94,.12)]
    y0=_render_track(NEW,base)
    y1=_render_track(NEW,with_kick)
    kick=_render_track(NEW,[_ev('kick',.75,.94,.12)])
    assert np.max(np.abs((y1-y0)-kick)) < 1e-12


def test_s27i_control_contract_rejects_malformed_or_overlapping_curves():
    patch=materialize_preset(NEW,role='drums')
    good=_ctrl(0,.5,[(0,1),(.5,0)])
    ir={'instruments':{'drums':patch},'tracks':[{'id':'drums','instrument':'drums','events':[good]}]}
    validate_drum_control_events(ir)
    bad=copy.deepcopy(ir)
    bad['tracks'][0]['events'][0]['points'][0]['openness']=1.2
    with pytest.raises(ContractValidationError,match='openness'):
        validate_drum_control_events(bad)
    overlap=copy.deepcopy(ir)
    overlap['tracks'][0]['events'].append(_ctrl(.25,.5,[(0,1),(.5,.2)]))
    with pytest.raises(ContractValidationError,match='overlaps'):
        validate_drum_control_events(overlap)


def test_s27i_four_limb_evidence_counts_control_as_left_foot_and_remains_playable():
    events=[
        _ev('hat_open',0,.84),_ev('kick',0,.92),
        _ctrl(.25,.75,[(0,1),(.35,.55),(.75,.1)]),
        _ev('snare_center',1.0,.90,.10),_ev('kick',2.0,.88),
        _ev('hat_open',2.5,.80),_ev('snare_rimshot',3.0,.95,.10),
    ]
    ir={'transport':{'bpm':BPM,'beats_per_bar':4},'tracks':[{'id':'drums','instrument':'drums','events':events}]}
    rep=analyze_drummer_performance(ir)
    assert rep['playable'] is True
    assert rep['issue_counts']['high']==0
    assert rep['limb_event_counts']=={'hands':4,'right_foot':2,'left_foot':1}
    assert any(x['drum']=='hat_pedal_control' and x['limb']=='left_foot' for x in rep['assignments'])


def test_s27i_midi_export_omits_control_event_without_losing_drum_notes():
    patch=materialize_preset(NEW,role='drums')
    events=[_ev('hat_open',0,.84),_ctrl(.1,.5,[(0,1),(.5,0)]),_ev('kick',1,.9)]
    ir={
        'meta':{'global_seed':1},'transport':{'bpm':120,'beats_per_bar':4},
        'tonal':{'root':'C','scale':'major'},'form':[],
        'materials':{'motifs':{},'progressions':{},'rhythms':{}},
        'instruments':{'drums':patch},
        'tracks':[{'id':'drums','instrument':'drums','source':{'type':'resolved'},'events':events}],
        'mix':{},
    }
    _,manifest,_=midi_bytes(ir,resolve=False)
    assert manifest['tracks'][0]['note_events']==2
