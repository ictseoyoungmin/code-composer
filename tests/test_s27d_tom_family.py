import copy
import hashlib
import numpy as np

from code_composer.presets import get_preset, materialize_preset, list_presets
from code_composer.audio.percussion import render_drum_event
from code_composer.audio.engines import engine_for_patch
from code_composer.export.midi import DRUM_NOTES

SR=24000
OLD='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare'
NEW='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms'


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


def _centroid(x,a=0,b=.12):
    y=_window(x,a,b)
    X=np.abs(np.fft.rfft(y*np.hanning(len(y))))+1e-12
    f=np.fft.rfftfreq(len(y),1/SR)
    return float(np.sum(f*X)/np.sum(X))


def _dominant_low_hz(x,a=.01,b=.25):
    y=_window(x,a,b)
    X=np.abs(np.fft.rfft(y*np.hanning(len(y))))
    f=np.fft.rfftfreq(len(y),1/SR)
    mask=(f>=55)&(f<=420)
    return float(f[mask][np.argmax(X[mask])])


def test_s27d_preset_registered_and_only_adds_tom_mechanics():
    ids=[x['preset_id'] for x in list_presets(engine='percussion')]
    assert NEW in ids
    old=get_preset(OLD)['patch']['drum_graph']
    new=get_preset(NEW)['patch']['drum_graph']
    for key in ('kick','snare','hat','ride','crash','cymbal_extension','kit_integration','hi_hat_mechanics','snare_mechanics'):
        assert new[key] == old[key]
    assert new['tom_mechanics']['enabled'] is True
    assert new['tom_mechanics']['model'] == 'coupled_two_head_shell_v1'


def test_s27d_preserves_all_preexisting_event_renderers_byte_exact():
    old=materialize_preset(OLD,role='drums')
    new=materialize_preset(NEW,role='drums')
    for kind,dur,vel,seed in (
        ('kick',.35,.91,17),('snare',.35,.87,19),('hat',.18,.72,23),
        ('hat_closed',.05,.78,25),('snare_center',.05,.84,27),
        ('ride',1.35,.82,29),('crash',1.65,.98,31),
    ):
        assert _sha(render_drum_event(kind,dur,SR,vel,seed=seed,patch=old)) == _sha(render_drum_event(kind,dur,SR,vel,seed=seed,patch=new))


def test_s27d_high_mid_floor_have_ordered_body_pitch_and_decay():
    p=materialize_preset(NEW,role='drums')
    hi=render_drum_event('tom_high',.05,SR,.84,seed=17,patch=p)
    mid=render_drum_event('tom_mid',.05,SR,.84,seed=17,patch=p)
    floor=render_drum_event('tom_floor',.05,SR,.84,seed=17,patch=p)
    f_hi,f_mid,f_floor=map(_dominant_low_hz,(hi,mid,floor))
    assert f_hi > f_mid > f_floor
    assert _rms(_window(floor,.28,.50)) > _rms(_window(mid,.28,.50))*1.20
    assert _rms(_window(mid,.22,.38)) > _rms(_window(hi,.22,.38))*1.15


def test_s27d_family_is_not_pitch_shifted_copy_only():
    p=materialize_preset(NEW,role='drums')
    hi=render_drum_event('tom_high',.05,SR,.82,seed=31,patch=p)
    floor=render_drum_event('tom_floor',.05,SR,.82,seed=31,patch=p)
    # Size changes body/tail and spectral centroid, not merely fundamental pitch.
    assert _centroid(hi) > _centroid(floor)*1.18
    assert _rms(_window(floor,.18,.42)) > _rms(_window(hi,.18,.42))*1.45
    muted=copy.deepcopy(p)
    muted['drum_graph']['tom_mechanics']['families']['floor']['cavity_gain']=0.0
    muted['drum_graph']['tom_mechanics']['families']['floor']['shell_gain']=0.0
    bare=render_drum_event('tom_floor',.05,SR,.82,seed=31,patch=muted)
    assert _rms(_window(floor,.02,.30)-_window(bare,.02,.30)) > _rms(_window(bare,.02,.30))*.06


def test_s27d_edge_hit_changes_excitation_not_just_gain():
    p=materialize_preset(NEW,role='drums')
    center=render_drum_event('tom_mid',.05,SR,.82,seed=43,patch=p)
    edge=render_drum_event('tom_mid_edge',.05,SR,.82,seed=43,patch=p)
    assert _centroid(edge) > _centroid(center)*1.10
    assert _dominant_low_hz(edge) >= _dominant_low_hz(center)*.90
    # Difference remains after RMS normalization, proving a timbre/shape change.
    a=_window(center,0,.22); b=_window(edge,0,.22)
    b=b*(_rms(a)/max(_rms(b),1e-12))
    assert _rms(a-b) > _rms(a)*.30


def test_s27d_toms_are_deterministic_seed_sensitive_and_bounded():
    p=materialize_preset(NEW,role='drums')
    for kind in ('tom_high','tom_mid','tom_floor','tom_high_edge','tom_mid_edge','tom_floor_edge'):
        a=render_drum_event(kind,.05,SR,.79,seed=61,patch=p)
        b=render_drum_event(kind,.05,SR,.79,seed=61,patch=p)
        c=render_drum_event(kind,.05,SR,.79,seed=62,patch=p)
        assert np.array_equal(a,b)
        assert not np.array_equal(a,c)
        assert np.max(np.abs(a)) < 1.0


def test_s27d_engine_and_midi_surfaces_cover_tom_family():
    p=materialize_preset(NEW,role='drums')
    engine=engine_for_patch(p)
    engine.validate_ir_patch('drums',p)
    assert engine.tail_seconds(p) >= .74
    assert DRUM_NOTES['tom_high'] == 50
    assert DRUM_NOTES['tom_mid'] == 47
    assert DRUM_NOTES['tom_floor'] == 43
    assert DRUM_NOTES['tom_high_edge'] == 50
    assert DRUM_NOTES['tom_mid_edge'] == 47
    assert DRUM_NOTES['tom_floor_edge'] == 43
