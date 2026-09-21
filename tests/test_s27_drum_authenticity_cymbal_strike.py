import hashlib
import numpy as np

from code_composer.presets import get_preset, materialize_preset, list_presets
from code_composer.audio.percussion import render_drum_event
from code_composer.audio.engines import engine_for_patch

SR=24000
OLD='drums.s19_core_powerful_room'
NEW='drums.s19_core_powerful_room_authentic_strike'


def _sha(x):
    return hashlib.sha256(np.asarray(x,dtype=np.float64).tobytes()).hexdigest()


def _rms(x):
    x=np.asarray(x,dtype=np.float64)
    return float(np.sqrt(np.mean(x*x)+1e-18))


def _mono(x):
    x=np.asarray(x,dtype=np.float64)
    return x.mean(axis=1) if x.ndim==2 else x


def test_s27a_preset_registered_and_only_opens_cymbal_strike_source():
    ids=[x['preset_id'] for x in list_presets(engine='percussion')]
    assert NEW in ids
    old=get_preset(OLD)['patch']['drum_graph']
    new=get_preset(NEW)['patch']['drum_graph']
    for key in ('kick','snare','hat','kit_integration'):
        assert new[key] == old[key]
    assert new['cymbal_extension']['ride_tail_s'] == old['cymbal_extension']['ride_tail_s']
    assert new['cymbal_extension']['crash_tail_s'] == old['cymbal_extension']['crash_tail_s']
    assert new['cymbal_extension']['strike_model'] == 'physical_v1'


def test_s27a_s19_core_events_remain_byte_exact_to_s26():
    old=materialize_preset(OLD,role='drums')
    new=materialize_preset(NEW,role='drums')
    for kind,dur,vel,seed in (
        ('kick',.35,.91,17),('snare',.35,.87,19),('hat',.18,.72,23),
    ):
        a=render_drum_event(kind,dur,SR,vel,seed=seed,patch=old)
        b=render_drum_event(kind,dur,SR,vel,seed=seed,patch=new)
        assert _sha(a)==_sha(b)


def test_s27a_physical_cymbal_strike_is_deterministic_and_changes_source():
    old=materialize_preset(OLD,role='drums')
    new=materialize_preset(NEW,role='drums')
    for kind,dur,vel in (('ride',1.35,.82),('crash',1.65,.98)):
        a=render_drum_event(kind,dur,SR,vel,seed=31,patch=new)
        b=render_drum_event(kind,dur,SR,vel,seed=31,patch=new)
        c=render_drum_event(kind,dur,SR,vel,seed=32,patch=new)
        legacy=render_drum_event(kind,dur,SR,vel,seed=31,patch=old)
        assert np.array_equal(a,b)
        assert not np.array_equal(a,c)
        assert not np.array_equal(a,legacy)


def test_s27a_strike_authority_in_first_five_ms_without_tail_regression():
    old=materialize_preset(OLD,role='drums')
    new=materialize_preset(NEW,role='drums')
    cases=(('ride',1.35,.82,.90),('crash',1.65,.98,1.20))
    for kind,dur,vel,min_ratio in cases:
        a=_mono(render_drum_event(kind,dur,SR,vel,seed=17,patch=old))
        b=_mono(render_drum_event(kind,dur,SR,vel,seed=17,patch=new))
        onset_old=_rms(a[:int(.005*SR)])
        onset_new=_rms(b[:int(.005*SR)])
        tail_old=_rms(a[int(.80*SR):int(1.20*SR)])
        tail_new=_rms(b[int(.80*SR):int(1.20*SR)])
        assert onset_new >= onset_old*min_ratio
        assert tail_new <= tail_old*1.02


def test_s27a_authored_velocity_changes_contact_shape_not_only_level():
    patch=materialize_preset(NEW,role='drums')
    for kind,dur in (('ride',1.35),('crash',1.65)):
        soft=_mono(render_drum_event(kind,dur,SR,.42,seed=41,patch=patch))
        hard=_mono(render_drum_event(kind,dur,SR,1.0,seed=41,patch=patch))
        soft_ratio=_rms(soft[:int(.005*SR)])/_rms(soft[int(.020*SR):int(.080*SR)])
        hard_ratio=_rms(hard[:int(.005*SR)])/_rms(hard[int(.020*SR):int(.080*SR)])
        assert hard_ratio > soft_ratio*1.08


def test_s27a_engine_validates_and_preserves_room_tail_contract():
    patch=materialize_preset(NEW,role='drums')
    engine=engine_for_patch(patch)
    engine.validate_ir_patch('drums',patch)
    assert engine.tail_seconds(patch) >= 1.65
