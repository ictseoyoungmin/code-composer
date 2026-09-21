import hashlib
import numpy as np

from code_composer.presets import get_preset, materialize_preset, list_presets
from code_composer.audio.percussion import render_drum_event
from code_composer.audio.engines import engine_for_patch

SR=24000
OLD='drums.s19_core_powerful_room_authentic_strike'
NEW='drums.s19_core_powerful_room_authentic_strike_v2'


def _sha(x):
    return hashlib.sha256(np.asarray(x,dtype=np.float64).tobytes()).hexdigest()


def _mono(x):
    x=np.asarray(x,dtype=np.float64)
    return x.mean(axis=1) if x.ndim==2 else x


def _rms(x):
    x=np.asarray(x,dtype=np.float64)
    return float(np.sqrt(np.mean(x*x)+1e-18))


def _early_band_ratios(x):
    x=_mono(x)[int(.005*SR):int(.120*SR)]
    w=np.hanning(len(x))
    X=np.abs(np.fft.rfft(x*w))
    f=np.fft.rfftfreq(len(x),1/SR)
    e=X*X
    total=float(e[(f>=300)&(f<11000)].sum()+1e-18)
    def ratio(a,b):
        return float(e[(f>=a)&(f<b)].sum()/total)
    return ratio(300,1500), ratio(1500,6000), ratio(6000,11000)


def test_s27a2_preset_registered_and_only_reopens_cymbal_strike_voicing():
    ids=[x['preset_id'] for x in list_presets(engine='percussion')]
    assert NEW in ids
    old=get_preset(OLD)['patch']['drum_graph']
    new=get_preset(NEW)['patch']['drum_graph']
    for key in ('kick','snare','hat','kit_integration'):
        assert new[key] == old[key]
    assert new['cymbal_extension']['ride_tail_s'] == old['cymbal_extension']['ride_tail_s']
    assert new['cymbal_extension']['crash_tail_s'] == old['cymbal_extension']['crash_tail_s']
    assert new['cymbal_extension']['strike_model'] == 'physical_v2'


def test_s27a2_s19_core_remains_byte_exact_to_s27a():
    old=materialize_preset(OLD,role='drums')
    new=materialize_preset(NEW,role='drums')
    for kind,dur,vel,seed in (
        ('kick',.35,.91,17),('snare',.35,.87,19),('hat',.18,.72,23),
    ):
        assert _sha(render_drum_event(kind,dur,SR,vel,seed=seed,patch=old)) == _sha(render_drum_event(kind,dur,SR,vel,seed=seed,patch=new))


def test_s27a2_dense_field_reduces_bell_like_low_order_dominance():
    old=materialize_preset(OLD,role='drums')
    new=materialize_preset(NEW,role='drums')
    for kind,dur,vel,max_fraction in (
        ('ride',1.35,.82,.72),
        ('crash',1.65,.98,.82),
    ):
        a=render_drum_event(kind,dur,SR,vel,seed=17,patch=old)
        b=render_drum_event(kind,dur,SR,vel,seed=17,patch=new)
        old_low,_,_=_early_band_ratios(a)
        new_low,_,_=_early_band_ratios(b)
        assert new_low <= old_low*max_fraction


def test_s27a2_preserves_stick_attack_and_short_tail_contract():
    old=materialize_preset(OLD,role='drums')
    new=materialize_preset(NEW,role='drums')
    for kind,dur,vel,onset_floor,tail_ceiling in (
        ('ride',1.35,.82,.88,1.02),
        ('crash',1.65,.98,.88,1.02),
    ):
        a=_mono(render_drum_event(kind,dur,SR,vel,seed=17,patch=old))
        b=_mono(render_drum_event(kind,dur,SR,vel,seed=17,patch=new))
        assert _rms(b[:int(.005*SR)]) >= _rms(a[:int(.005*SR)])*onset_floor
        assert _rms(b[int(.80*SR):int(1.20*SR)]) <= _rms(a[int(.80*SR):int(1.20*SR)])*tail_ceiling


def test_s27a2_is_deterministic_seed_sensitive_and_engine_valid():
    patch=materialize_preset(NEW,role='drums')
    engine=engine_for_patch(patch)
    engine.validate_ir_patch('drums',patch)
    for kind,dur,vel in (('ride',1.35,.82),('crash',1.65,.98)):
        a=render_drum_event(kind,dur,SR,vel,seed=31,patch=patch)
        b=render_drum_event(kind,dur,SR,vel,seed=31,patch=patch)
        c=render_drum_event(kind,dur,SR,vel,seed=32,patch=patch)
        assert np.array_equal(a,b)
        assert not np.array_equal(a,c)
