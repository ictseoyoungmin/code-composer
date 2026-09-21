import copy
import hashlib
import numpy as np
import pytest

from code_composer.presets import get_preset, materialize_preset, list_presets
from code_composer.audio.percussion import render_drum_event
from code_composer.audio.engines import engine_for_patch, InstrumentEngineValidationError
from code_composer.render import _render_dry_track
from code_composer.analysis.drummer_performance_analysis import analyze_drummer_performance

SR=24000
BPM=120.0
BEAT_S=60.0/BPM
OLD='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated'
NEW='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_stateful_hihat'


def _sha(x):
    return hashlib.sha256(np.asarray(x,dtype=np.float64).tobytes()).hexdigest()


def _rms(x):
    x=np.asarray(x,dtype=np.float64)
    return float(np.sqrt(np.mean(x*x)+1e-18)) if len(x) else 0.0


def _ev(kind,beat,vel=.82,dur=.08):
    return {'event_type':'drum','drum':kind,'start_beat':float(beat),'duration_beats':float(dur),'velocity':float(vel)}


def _render_track(preset,events,*,room=False):
    patch=materialize_preset(preset,role='drums')
    if not room:
        patch=copy.deepcopy(patch)
        patch['drum_graph']['kit_integration']['enabled']=False
    ir={'meta':{'global_seed':270927},'instruments':{'drums':patch}}
    track={'id':'drums','instrument':'drums','events':list(events)}
    n=int(2.5*SR)
    return _render_dry_track(ir,track,n,SR,BEAT_S,graph_mode=True)


def _window(x,start_s,end_s):
    return x[int(start_s*SR):int(end_s*SR)]


def test_s27h_preset_is_opt_in_and_only_adds_hihat_state_to_s27g_patch():
    ids=[x['preset_id'] for x in list_presets(engine='percussion')]
    assert NEW in ids
    a=get_preset(OLD)['patch']['drum_graph']
    b=get_preset(NEW)['patch']['drum_graph']
    assert 'hi_hat_state' not in a
    assert b['hi_hat_state']['enabled'] is True
    assert b['hi_hat_state']['model']=='authored_closure_damping_v1'
    assert {k:v for k,v in b.items() if k!='hi_hat_state'} == a


def test_s27h_direct_event_sources_remain_byte_exact_to_s27g():
    a=materialize_preset(OLD,role='drums')
    b=materialize_preset(NEW,role='drums')
    kinds=('kick','ride','crash','hat_tight_closed','hat_closed','hat_half_open','hat_open','hat_pedal','hat_foot_splash','snare_rimshot','tom_floor')
    for i,kind in enumerate(kinds):
        x=render_drum_event(kind,.08,SR,.84,seed=310+i,patch=a)
        y=render_drum_event(kind,.08,SR,.84,seed=310+i,patch=b)
        assert _sha(x)==_sha(y),kind


def test_s27h_authored_pedal_chokes_already_ringing_open_hat_without_touching_preclosure_audio():
    events=[_ev('hat_open',0.0,.86,.12),_ev('hat_pedal',.50,.68,.08)]
    old=_render_track(OLD,events)
    new=_render_track(NEW,events)
    close_s=.50*BEAT_S
    pre=int((close_s-.010)*SR)
    assert _sha(old[:pre])==_sha(new[:pre])
    old_tail=_rms(_window(old,close_s+.070,close_s+.230))
    new_tail=_rms(_window(new,close_s+.070,close_s+.230))
    assert new_tail < old_tail*.30


def test_s27h_half_open_transition_is_partial_while_pedal_close_is_near_full_damping():
    half=[_ev('hat_open',0.0,.86,.12),_ev('hat_half_open',.50,.70,.08)]
    pedal=[_ev('hat_open',0.0,.86,.12),_ev('hat_pedal',.50,.68,.08)]
    yh=_render_track(NEW,half)
    yp=_render_track(NEW,pedal)
    start=.50*BEAT_S+.090
    end=.50*BEAT_S+.230
    assert _rms(_window(yh,start,end)) > _rms(_window(yp,start,end))*1.8


def test_s27h_closure_does_not_gate_unrelated_kick_voice():
    base=[_ev('hat_open',0.0,.86,.12),_ev('hat_pedal',.50,.68,.08)]
    with_kick=base+[_ev('kick',.50,.94,.12)]
    y0=_render_track(NEW,base)
    y1=_render_track(NEW,with_kick)
    kick_only=_render_track(NEW,[_ev('kick',.50,.94,.12)])
    assert np.max(np.abs((y1-y0)-kick_only)) < 1e-12


def test_s27h_shared_room_retains_a_short_acoustic_decay_but_reduces_old_open_hat_smear():
    events=[_ev('hat_open',0.0,.88,.12),_ev('hat_pedal',.50,.70,.08)]
    old=_render_track(OLD,events,room=True)
    new=_render_track(NEW,events,room=True)
    close_s=.50*BEAT_S
    old_tail=_rms(_window(old,close_s+.120,close_s+.420))
    new_tail=_rms(_window(new,close_s+.120,close_s+.420))
    assert new_tail < old_tail*.82
    dry_new=_render_track(NEW,events,room=False)
    dry_tail=_rms(_window(dry_new,close_s+.120,close_s+.420))
    assert new_tail > dry_tail*1.05


def test_s27h_four_limb_sequence_remains_authored_and_playable():
    events=[
        _ev('hat_open',0.0,.82,.12), _ev('kick',0.0,.90,.12),
        _ev('hat_pedal',.50,.62,.08), _ev('snare_center',1.0,.90,.10),
        _ev('hat_closed',1.5,.74,.08), _ev('kick',2.0,.86,.12),
        _ev('hat_open',2.5,.80,.12), _ev('hat_pedal',3.0,.64,.08),
        _ev('snare_rimshot',3.0,.95,.10),
    ]
    ir={'transport':{'bpm':BPM,'beats_per_bar':4},'tracks':[{'id':'drums','instrument':'drums','events':events}]}
    rep=analyze_drummer_performance(ir)
    assert rep['playable'] is True
    assert rep['strained'] is False
    assert rep['issue_counts']=={'high':0,'medium':0,'low':0}


def test_s27h_validation_rejects_unknown_closure_target():
    p=materialize_preset(NEW,role='drums')
    p=copy.deepcopy(p)
    p['drum_graph']['hi_hat_state']['closure']['ride']={'decay_ms':12.0,'residual':.02}
    with pytest.raises(InstrumentEngineValidationError,match='unsupported'):
        engine_for_patch(p).validate_ir_patch('drums',p)
