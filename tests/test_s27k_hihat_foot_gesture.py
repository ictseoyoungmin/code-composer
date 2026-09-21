import copy
import hashlib
import numpy as np
import pytest

from code_composer.presets import list_presets, materialize_preset
from code_composer.audio.percussion import render_drum_event, render_hi_hat_pedal_control
from code_composer.render import _render_dry_track
from code_composer.validation_contracts import validate_drum_control_events
from code_composer.audio.engines.percussion import PercussionEngine
from code_composer.analysis.drummer_performance_analysis import analyze_drummer_performance

SR=24000
BPM=120.0
BEAT_S=60.0/BPM
NEW='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_foot_gesture'
OLD='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_persistent_hihat'

def _sha(x): return hashlib.sha256(np.asarray(x,dtype=np.float64).tobytes()).hexdigest()
def _rms(x):
    x=np.asarray(x,dtype=np.float64)
    return float(np.sqrt(np.mean(x*x)+1e-18)) if len(x) else 0.0

def _ctrl(points,dur=1.0,start=0.0):
    return {'event_type':'drum_control','control':'hi_hat_pedal_openness','start_beat':float(start),'duration_beats':float(dur),'points':[{'offset_beats':float(a),'openness':float(b)} for a,b in points]}
def _ev(kind,beat,vel=.8,dur=.1): return {'event_type':'drum','drum':kind,'start_beat':float(beat),'duration_beats':float(dur),'velocity':float(vel)}

def _render_track(preset,events,*,room=False,n_s=3.0,seed=272401):
    patch=materialize_preset(preset,role='drums')
    if not room:
        patch=copy.deepcopy(patch); patch['drum_graph']['kit_integration']['enabled']=False
    ir={'meta':{'global_seed':seed},'instruments':{'drums':patch}}
    track={'id':'drums','instrument':'drums','events':list(events)}
    return _render_dry_track(ir,track,int(n_s*SR),SR,BEAT_S,graph_mode=True)

def test_s27k_factory_preset_and_pedal_audio_contract():
    assert NEW in [x['preset_id'] for x in list_presets(engine='percussion')]
    p=materialize_preset(NEW,role='drums'); hh=p['drum_graph']['hi_hat_state']
    assert hh['model']=='authored_persistent_openness_v3'
    assert hh['pedal_audio']['enabled'] is True
    assert hh['pedal_audio']['model']=='authored_motion_plate_contact_v3'
    assert hh['pedal_audio']['collision_profiles']['chick']['gain_scale']==0.0
    assert hh['pedal_audio']['collision_profiles']['splash']['gain_scale']==0.0
    assert hh['pedal_audio']['chick_output_gain']==2.0
    assert hh['pedal_audio']['splash_output_gain']==1.25
    assert hh['pedal_audio']['collision_profiles']['chick']['enabled'] is True
    assert hh['pedal_audio']['collision_profiles']['splash']['enabled'] is True
    PercussionEngine().validate_ir_patch("drums",p)

def test_s27k_old_s27j_control_remains_silent_as_standalone_event():
    ev=_ctrl([(0,1.0),(.12,0.0)],.12)
    old=materialize_preset(OLD,role='drums'); new=materialize_preset(NEW,role='drums')
    a=render_hi_hat_pedal_control(ev,SR,BEAT_S,123,old)
    b=render_hi_hat_pedal_control(ev,SR,BEAT_S,123,new)
    assert a.shape==(0,2)
    assert len(b)>0 and _rms(b)>1e-5

def test_s27k_fast_close_produces_chick_but_slow_close_is_silent():
    p=materialize_preset(NEW,role='drums')
    fast=render_hi_hat_pedal_control(_ctrl([(0,1),(.12,0)],.12),SR,BEAT_S,1,p)
    slow=render_hi_hat_pedal_control(_ctrl([(0,1),(1.0,0)],1.0),SR,BEAT_S,1,p)
    assert _rms(fast)>1e-4
    assert len(slow)==0 or _rms(slow)<_rms(fast)*.05

def test_s27k_fast_release_from_clamped_state_produces_longer_splash():
    p=materialize_preset(NEW,role='drums')
    close=render_hi_hat_pedal_control(_ctrl([(0,1),(.10,0)],.10),SR,BEAT_S,7,p)
    splash=render_hi_hat_pedal_control(_ctrl([(0,0),(.10,.85)],.10),SR,BEAT_S,7,p)
    assert _rms(splash)>1e-4
    lo=int(.18*SR); hi=min(len(splash),int(.42*SR))
    late_s=_rms(splash[lo:hi])
    late_c=_rms(close[lo:min(len(close),hi)]) if len(close)>lo else 0.0
    assert late_s>late_c*1.4

def test_s27k_partial_motion_not_reaching_contact_does_not_make_foot_hit():
    p=materialize_preset(NEW,role='drums')
    x=render_hi_hat_pedal_control(_ctrl([(0,1),(.15,.32)],.15),SR,BEAT_S,2,p)
    assert len(x)==0

def test_s27k_direct_drum_sources_remain_s27j_byte_exact():
    a=materialize_preset(OLD,role='drums'); b=materialize_preset(NEW,role='drums')
    for i,k in enumerate(('hat_open','hat_half_open','hat_closed','hat_pedal','hat_foot_splash','kick','snare_rimshot','ride')):
        x=render_drum_event(k,.12,SR,.83,seed=33+i,patch=a)
        y=render_drum_event(k,.12,SR,.83,seed=33+i,patch=b)
        assert _sha(x)==_sha(y), k

def test_s27k_fast_control_adds_audio_but_preserves_later_snare_identity():
    control=_ctrl([(0,1),(.12,0)],.12,0)
    combo=_render_track(NEW,[control,_ev('snare_center',2.0,.86)],n_s=2)
    foot=_render_track(NEW,[control],n_s=2)
    snare=_render_track(NEW,[_ev('snare_center',2.0,.86)],n_s=2)
    assert np.max(np.abs((combo-foot)-snare))<1e-12

def test_s27k_control_still_counts_as_one_left_foot_authored_action():
    events=[_ctrl([(0,1),(.10,0),(.18,.8)],.18,0),_ev('kick',0,.9),_ev('snare_center',1,.85)]
    ir={'transport':{'bpm':120,'beats_per_bar':4},'tracks':[{'id':'d','instrument':'d','events':events}]}
    rep=analyze_drummer_performance(ir)
    lf=[x for x in rep['assignments'] if x['limb']=='left_foot']
    assert len(lf)==1 and lf[0]['drum']=='hat_pedal_control'

def test_s27k_ir_validation_accepts_motion_curve_and_rejects_bad_pedal_audio_patch():
    patch=materialize_preset(NEW,role='drums'); events=[_ctrl([(0,1),(.10,0),(.20,.8)],.20)]
    ir={'meta':{'global_seed':17},'form':[],'instruments':{'d':patch},'tracks':[{'id':'d','instrument':'d','events':events}]}
    validate_drum_control_events(ir)
    bad=copy.deepcopy(patch); bad['drum_graph']['hi_hat_state']['pedal_audio']['contact_threshold']=2.0
    with pytest.raises(Exception): PercussionEngine().validate_ir_patch("drums",bad)

def test_s27k_fast_close_reopen_renders_audible_control_consequence():
    y=_render_track(NEW,[_ctrl([(0,1),(.10,0),(.20,.85)],.20)],n_s=1.5)
    assert _rms(y)>1e-4


def _max_step(x,a,b):
    mono=np.asarray(x,dtype=np.float64).mean(axis=1)
    seg=mono[int(a*SR):min(len(mono),int(b*SR))]
    return float(np.max(np.abs(np.diff(seg)))) if len(seg)>1 else 0.0

def _crest(x,a,b):
    mono=np.asarray(x,dtype=np.float64).mean(axis=1)
    seg=mono[int(a*SR):min(len(mono),int(b*SR))]
    if len(seg)==0: return 0.0
    return float(np.max(np.abs(seg))/max(_rms(seg),1e-18))

def _r1_patch_from_r2(p):
    r1=copy.deepcopy(p)
    pa=r1['drum_graph']['hi_hat_state']['pedal_audio']
    pa['model']='authored_motion_microcontact_v2'
    pa['chick_output_gain']=1.0
    pa['splash_output_gain']=1.0
    pa['collision_profiles']['chick'].update({'enabled':True,'pulse_ms':.42,'density_scale':1.3,'gain_scale':.62})
    pa['collision_profiles']['splash'].update({'enabled':True,'pulse_ms':.72,'density_scale':1.55,'gain_scale':.48})
    return r1

def test_s27k_r2_control_splash_removes_broadband_microcontact_layer():
    p=materialize_preset(NEW,role='drums')
    r1=_r1_patch_from_r2(p)
    gesture=_ctrl([(0,1),(.10,0),(.20,.86)],.20)
    old=render_hi_hat_pedal_control(gesture,SR,BEAT_S,273102,r1)
    new=render_hi_hat_pedal_control(gesture,SR,BEAT_S,273102,p)
    assert _max_step(new,.18,.42) < _max_step(old,.18,.42)*.90
    assert _rms(new[int(.18*SR):int(.42*SR)]) > 1e-5

def test_s27k_r2_control_chick_keeps_plate_contact_without_fabric_layer():
    p=materialize_preset(NEW,role='drums')
    r1=_r1_patch_from_r2(p)
    gesture=_ctrl([(0,1),(.12,0)],.12)
    old=render_hi_hat_pedal_control(gesture,SR,BEAT_S,273102,r1)
    new=render_hi_hat_pedal_control(gesture,SR,BEAT_S,273102,p)
    assert _max_step(new,.02,.16) < _max_step(old,.02,.16)*.60
    assert _rms(new[int(.02*SR):int(.16*SR)]) > 1e-4
