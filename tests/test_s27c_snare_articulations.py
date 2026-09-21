import copy
import hashlib
import numpy as np

from code_composer.presets import get_preset, materialize_preset, list_presets
from code_composer.audio.percussion import render_drum_event
from code_composer.audio.engines import engine_for_patch
from code_composer.export.midi import DRUM_NOTES

SR=24000
OLD='drums.s19_core_powerful_room_authentic_strike_v2_hihat'
NEW='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare'


def _mono(x):
    x=np.asarray(x,dtype=np.float64)
    return x.mean(axis=1) if x.ndim==2 else x


def _rms(x):
    x=np.asarray(x,dtype=np.float64)
    return float(np.sqrt(np.mean(x*x)+1e-18)) if len(x) else 0.0


def _sha(x):
    return hashlib.sha256(np.asarray(x,dtype=np.float64).tobytes()).hexdigest()


def _window(x,a,b):
    x=_mono(x)
    return x[int(a*SR):min(len(x),int(b*SR))]


def _centroid(x,a=0,b=.08):
    y=_window(x,a,b)
    X=np.abs(np.fft.rfft(y*np.hanning(len(y))))+1e-12
    f=np.fft.rfftfreq(len(y),1/SR)
    return float(np.sum(f*X)/np.sum(X))


def test_s27c_preset_registered_and_only_adds_explicit_snare_mechanics():
    ids=[x['preset_id'] for x in list_presets(engine='percussion')]
    assert NEW in ids
    old=get_preset(OLD)['patch']['drum_graph']
    new=get_preset(NEW)['patch']['drum_graph']
    for key in ('kick','snare','hat','ride','crash','cymbal_extension','kit_integration','hi_hat_mechanics'):
        assert new[key] == old[key]
    assert new['snare_mechanics']['enabled'] is True
    assert new['snare_mechanics']['model'] == 'coupled_head_wire_rim_v1'


def test_s27c_preserves_all_preexisting_drum_event_renderers_byte_exact():
    old=materialize_preset(OLD,role='drums')
    new=materialize_preset(NEW,role='drums')
    for kind,dur,vel,seed in (
        ('kick',.35,.91,17),('snare',.35,.87,19),('hat',.18,.72,23),
        ('hat_closed',.05,.78,25),('hat_open',.05,.82,27),
        ('ride',1.35,.82,29),('crash',1.65,.98,31),
    ):
        assert _sha(render_drum_event(kind,dur,SR,vel,seed=seed,patch=old)) == _sha(render_drum_event(kind,dur,SR,vel,seed=seed,patch=new))


def test_s27c_center_preserves_legacy_snare_backbeat_authority():
    p=materialize_preset(NEW,role='drums')
    legacy=render_drum_event('snare',.22,SR,.86,seed=17,patch=p)
    center=render_drum_event('snare_center',.05,SR,.86,seed=17,patch=p)
    assert _rms(center) >= _rms(legacy)*.85
    assert _rms(center) <= _rms(legacy)*1.45
    assert _rms(_window(center,0,.020)) >= _rms(_window(legacy,0,.020))*.85
    assert _rms(_window(center,0,.020)) <= _rms(_window(legacy,0,.020))*1.40


def test_s27c_ghost_is_performance_soft_but_keeps_audible_wire_tail():
    p=materialize_preset(NEW,role='drums')
    center=render_drum_event('snare_center',.05,SR,.86,seed=21,patch=p)
    ghost=render_drum_event('snare_ghost',.05,SR,.34,seed=21,patch=p)
    assert _rms(ghost) < _rms(center)*.32
    assert _rms(_window(ghost,0,.020)) < _rms(_window(center,0,.020))*.32
    assert _rms(_window(ghost,.055,.14)) > 1e-3


def test_s27c_rimshot_is_simultaneous_head_plus_rim_not_eq_variant():
    p=materialize_preset(NEW,role='drums')
    center=render_drum_event('snare_center',.05,SR,.86,seed=29,patch=p)
    rim=render_drum_event('snare_rimshot',.05,SR,.86,seed=29,patch=p)
    assert _rms(_window(rim,0,.020)) > _rms(_window(center,0,.020))*1.01
    muted=copy.deepcopy(p)
    st=muted['drum_graph']['snare_mechanics']['states']['rimshot']
    st['rim_gain']=0.0
    st['wood_gain']=0.0
    no_rim=render_drum_event('snare_rimshot',.05,SR,.86,seed=29,patch=muted)
    assert _rms(_window(rim,0,.060)-_window(no_rim,0,.060)) > _rms(_window(no_rim,0,.060))*.18


def test_s27c_cross_stick_is_dry_woody_rim_shell_event():
    p=materialize_preset(NEW,role='drums')
    center=render_drum_event('snare_center',.05,SR,.80,seed=37,patch=p)
    cross=render_drum_event('snare_cross_stick',.05,SR,.80,seed=37,patch=p)
    assert _centroid(cross) < 1800
    assert _centroid(center) > _centroid(cross)*2.5
    assert _rms(_window(cross,.10,.12)) < _rms(_window(center,.10,.18))*.55


def test_s27c_strike_position_changes_membrane_response_causally():
    p=materialize_preset(NEW,role='drums')
    center=render_drum_event('snare_center',.05,SR,.82,seed=43,patch=p)
    moved=copy.deepcopy(p)
    moved['drum_graph']['snare_mechanics']['states']['center']['strike_position']=0.72
    edge=render_drum_event('snare_center',.05,SR,.82,seed=43,patch=moved)
    assert not np.array_equal(center,edge)
    assert _rms(_window(center,0,.09)-_window(edge,0,.09)) > 1e-3


def test_s27c_articulations_are_deterministic_and_seed_sensitive():
    p=materialize_preset(NEW,role='drums')
    for kind in ('snare_center','snare_ghost','snare_rimshot','snare_cross_stick'):
        a=render_drum_event(kind,.05,SR,.79,seed=61,patch=p)
        b=render_drum_event(kind,.05,SR,.79,seed=61,patch=p)
        c=render_drum_event(kind,.05,SR,.79,seed=62,patch=p)
        assert np.array_equal(a,b)
        assert not np.array_equal(a,c)


def test_s27c_engine_and_midi_surfaces_cover_snare_articulations():
    p=materialize_preset(NEW,role='drums')
    engine=engine_for_patch(p)
    engine.validate_ir_patch('drums',p)
    assert engine.tail_seconds(p) >= .24
    assert DRUM_NOTES['snare_center'] == 38
    assert DRUM_NOTES['snare_ghost'] == 38
    assert DRUM_NOTES['snare_rimshot'] == 38
    assert DRUM_NOTES['snare_cross_stick'] == 37
