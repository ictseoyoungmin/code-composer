import copy
import hashlib
import numpy as np

from code_composer.presets import get_preset, materialize_preset, list_presets
from code_composer.audio.percussion import render_drum_event, render_hi_hat_pedal_control
from code_composer.audio.engines import engine_for_patch

SR=24000
BEAT_S=.5
OLD='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_foot_gesture'
NEW='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_foot_gesture_metal_hihat'

def _mono(x):
    x=np.asarray(x,dtype=np.float64)
    return x.mean(axis=1) if x.ndim==2 else x

def _rms(x):
    x=np.asarray(x,dtype=np.float64)
    return float(np.sqrt(np.mean(x*x)+1e-18)) if len(x) else 0.0

def _sha(x):
    return hashlib.sha256(np.asarray(x,dtype=np.float64).tobytes()).hexdigest()

def _window(x,a,b):
    x=_mono(x); return x[int(a*SR):min(len(x),int(b*SR))]

def _flatness(x,a=.015,b=.16):
    y=_window(x,a,b)
    X=np.abs(np.fft.rfft(y*np.hanning(len(y))))+1e-12
    f=np.fft.rfftfreq(len(y),1/SR)
    S=X[(f>=3000)&(f<=11000)]
    return float(np.exp(np.mean(np.log(S)))/np.mean(S))

def _dominant_power_share(x,a=.015,b=.16):
    y=_window(x,a,b)
    X=(np.abs(np.fft.rfft(y*np.hanning(len(y))))+1e-12)**2
    f=np.fft.rfftfreq(len(y),1/SR)
    S=X[(f>=3000)&(f<=11000)]
    return float(S.max()/S.sum())

def _ctrl(points,dur=.2):
    return {
        'event_type':'drum_control','control':'hi_hat_pedal_openness',
        'start_beat':0.0,'duration_beats':float(dur),
        'points':[{'offset_beats':float(a),'openness':float(b)} for a,b in points],
    }

def test_s27br1_new_preset_reopens_only_hihat_source_plus_dependent_foot_level_calibration():
    ids=[x['preset_id'] for x in list_presets(engine='percussion')]
    assert NEW in ids
    old=get_preset(OLD)['patch']['drum_graph']
    new=get_preset(NEW)['patch']['drum_graph']
    for key in old:
        if key not in {'hi_hat_mechanics','hi_hat_state'}:
            assert new[key]==old[key]
    old_state=copy.deepcopy(old['hi_hat_state']); new_state=copy.deepcopy(new['hi_hat_state'])
    for st in (old_state,new_state):
        st['pedal_audio'].pop('chick_output_gain',None)
        st['pedal_audio'].pop('splash_output_gain',None)
    assert new_state==old_state
    mech=new['hi_hat_mechanics']
    assert mech['model']=='two_plate_modal_contact_v2'
    assert mech['collision_model']=='modal_plate_excitation_v2'
    engine_for_patch(materialize_preset(NEW,role='drums')).validate_ir_patch('drums',materialize_preset(NEW,role='drums'))

def test_s27br1_non_hihat_sources_remain_byte_exact():
    a=materialize_preset(OLD,role='drums'); b=materialize_preset(NEW,role='drums')
    for i,k in enumerate(('kick','snare_center','snare_rimshot','tom_high','tom_floor','ride','crash')):
        x=render_drum_event(k,.14,SR,.84,seed=71+i,patch=a)
        y=render_drum_event(k,.14,SR,.84,seed=71+i,patch=b)
        assert _sha(x)==_sha(y), k

def test_s27br1_collision_is_metal_modal_not_broadband_friction_texture():
    old=materialize_preset(OLD,role='drums'); new=materialize_preset(NEW,role='drums')
    a=render_drum_event('hat_half_open',.05,SR,.84,seed=41,patch=old)
    b=render_drum_event('hat_half_open',.05,SR,.84,seed=41,patch=new)
    # The rejected path was almost white/noise-like in the hi-hat band.  The
    # replacement should be distinctly more structured, yet not collapse to a
    # single bell partial.
    assert _flatness(b) < _flatness(a)*.72
    assert .22 < _flatness(b) < .68
    assert _dominant_power_share(b) < .085

def test_s27br1_modal_recontact_remains_a_material_part_of_half_open_sound():
    p=materialize_preset(NEW,role='drums')
    x=render_drum_event('hat_half_open',.05,SR,.84,seed=41,patch=p)
    muted=copy.deepcopy(p)
    muted['drum_graph']['hi_hat_mechanics']['states']['half_open']['collision_gain']=0.0
    y=render_drum_event('hat_half_open',.05,SR,.84,seed=41,patch=muted)
    delta=_rms(_window(x,.015,.16)-_window(y,.015,.16))
    assert delta > _rms(_window(y,.015,.16))*.8

def test_s27br1_accepted_stick_hat_presence_is_not_lost_with_noise_layer_removed():
    old=materialize_preset(OLD,role='drums'); new=materialize_preset(NEW,role='drums')
    floors={'hat_tight_closed':.78,'hat_closed':.78,'hat_half_open':.75,'hat_open':.82}
    for i,(kind,floor) in enumerate(floors.items()):
        a=render_drum_event(kind,.05,SR,.84,seed=41+i,patch=old)
        b=render_drum_event(kind,.05,SR,.84,seed=41+i,patch=new)
        assert _rms(b) >= _rms(a)*floor, kind
        assert _rms(b) <= _rms(a)*1.22, kind

def test_s27br1_pedal_state_decay_hierarchy_survives_metal_collision_rework():
    p=materialize_preset(NEW,role='drums')
    tight=render_drum_event('hat_tight_closed',.05,SR,.82,seed=17,patch=p)
    closed=render_drum_event('hat_closed',.05,SR,.82,seed=17,patch=p)
    half=render_drum_event('hat_half_open',.05,SR,.82,seed=17,patch=p)
    opened=render_drum_event('hat_open',.05,SR,.82,seed=17,patch=p)
    assert _rms(_window(tight,.08,.09)) < _rms(_window(half,.08,.12))*.18
    assert _rms(_window(closed,.08,.12)) < _rms(_window(half,.08,.12))*.18
    assert _rms(_window(opened,.20,.40)) > _rms(_window(half,.20,.34))*1.25

def test_s27br1_s27k_r2_control_gestures_remain_audible_after_source_rework():
    old=materialize_preset(OLD,role='drums'); new=materialize_preset(NEW,role='drums')
    chick=_ctrl([(0,1),(.12,0)],.12)
    splash=_ctrl([(0,1),(.10,0),(.20,.86)],.20)
    for ev in (chick,splash):
        a=render_hi_hat_pedal_control(ev,SR,BEAT_S,81,old)
        b=render_hi_hat_pedal_control(ev,SR,BEAT_S,81,new)
        assert _rms(b)>1e-4
        ratio=_rms(b)/_rms(a)
        assert .70 < ratio < 1.35

def test_s27br1_new_hihat_is_deterministic_and_seed_sensitive():
    p=materialize_preset(NEW,role='drums')
    for kind in ('hat_closed','hat_half_open','hat_open'):
        a=render_drum_event(kind,.05,SR,.79,seed=91,patch=p)
        b=render_drum_event(kind,.05,SR,.79,seed=91,patch=p)
        c=render_drum_event(kind,.05,SR,.79,seed=92,patch=p)
        assert np.array_equal(a,b)
        assert not np.array_equal(a,c)
