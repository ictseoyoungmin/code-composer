import copy
import hashlib
import numpy as np

from code_composer.presets import get_preset, materialize_preset, list_presets
from code_composer.audio.percussion import render_drum_event
from code_composer.audio.engines import engine_for_patch
from code_composer.export.midi import DRUM_NOTES

SR=24000
OLD='drums.s19_core_powerful_room_authentic_strike_v2'
NEW='drums.s19_core_powerful_room_authentic_strike_v2_hihat'


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


def _flatness(x,a=.004,b=.12):
    y=_window(x,a,b)
    w=np.hanning(len(y))
    X=np.abs(np.fft.rfft(y*w))+1e-12
    f=np.fft.rfftfreq(len(y),1/SR)
    S=X[(f>=3000)&(f<=11000)]
    return float(np.exp(np.mean(np.log(S)))/np.mean(S))


def test_s27b_preset_registered_and_only_adds_explicit_hihat_mechanics():
    ids=[x['preset_id'] for x in list_presets(engine='percussion')]
    assert NEW in ids
    old=get_preset(OLD)['patch']['drum_graph']
    new=get_preset(NEW)['patch']['drum_graph']
    for key in ('kick','snare','hat','ride','crash','cymbal_extension','kit_integration'):
        assert new[key] == old[key]
    assert new['hi_hat_mechanics']['enabled'] is True
    assert new['hi_hat_mechanics']['model'] == 'two_plate_inelastic_v1'


def test_s27b_preserves_all_preexisting_drum_event_renderers_byte_exact():
    old=materialize_preset(OLD,role='drums')
    new=materialize_preset(NEW,role='drums')
    for kind,dur,vel,seed in (
        ('kick',.35,.91,17),('snare',.35,.87,19),('hat',.18,.72,23),
        ('ride',1.35,.82,29),('crash',1.65,.98,31),
    ):
        assert _sha(render_drum_event(kind,dur,SR,vel,seed=seed,patch=old)) == _sha(render_drum_event(kind,dur,SR,vel,seed=seed,patch=new))


def test_s27b_two_plate_closed_preserves_legacy_closed_hat_authority():
    old=materialize_preset(OLD,role='drums')
    new=materialize_preset(NEW,role='drums')
    legacy=render_drum_event('hat',.18,SR,.78,seed=17,patch=old)
    closed=render_drum_event('hat_closed',.05,SR,.78,seed=17,patch=new)
    # The new causal model may redistribute the decay, but it must not repeat
    # the S20-S24 failure mode where added physical detail weakened the approved
    # S19 closed-hat performance anchor.
    assert _rms(closed) >= _rms(legacy)*.80
    assert _rms(_window(closed,0,.020)) >= _rms(_window(legacy,0,.020))*.78
    assert _rms(_window(closed,0,.020)) <= _rms(_window(legacy,0,.020))*1.30
    assert _rms(_window(closed,.080,.140)) >= _rms(_window(legacy,.080,.140))*.08


def test_s27b_state_decay_hierarchy_tracks_pedal_separation():
    p=materialize_preset(NEW,role='drums')
    tight=render_drum_event('hat_tight_closed',.05,SR,.82,seed=17,patch=p)
    closed=render_drum_event('hat_closed',.05,SR,.82,seed=17,patch=p)
    half=render_drum_event('hat_half_open',.05,SR,.82,seed=17,patch=p)
    opened=render_drum_event('hat_open',.05,SR,.82,seed=17,patch=p)
    # Tight/closed contact dies quickly; looser states retain plate motion.
    assert _rms(_window(tight,.08,.09)) < _rms(_window(half,.08,.12))*.10
    assert _rms(_window(closed,.08,.12)) < _rms(_window(half,.08,.12))*.10
    # Fully open keeps an audible plate tail later than half-open chatter.
    assert _rms(_window(opened,.20,.40)) > _rms(_window(half,.20,.34))*1.8


def test_s27b_collision_layer_is_noise_like_and_causally_audible():
    p=materialize_preset(NEW,role='drums')
    x=render_drum_event('hat_half_open',.05,SR,.84,seed=41,patch=p)
    assert _flatness(x) > .70
    muted=copy.deepcopy(p)
    muted['drum_graph']['hi_hat_mechanics']['states']['half_open']['collision_gain']=0.0
    y=render_drum_event('hat_half_open',.05,SR,.84,seed=41,patch=muted)
    # Repeated edge interaction must contribute materially; the articulation is
    # not allowed to collapse to a longer single-cymbal envelope.
    delta=_rms(_window(x,.015,.16)-_window(y,.015,.16))
    assert delta > _rms(_window(y,.015,.16))*.18


def test_s27b_bottom_plate_is_not_a_cosmetic_duplicate():
    p=materialize_preset(NEW,role='drums')
    x=render_drum_event('hat_closed',.05,SR,.82,seed=47,patch=p)
    top_only=copy.deepcopy(p)
    st=top_only['drum_graph']['hi_hat_mechanics']['states']['closed']
    st['bottom_transfer']=0.0
    st['bottom_gain']=0.0
    y=render_drum_event('hat_closed',.05,SR,.82,seed=47,patch=top_only)
    assert not np.array_equal(x,y)
    assert _rms(_window(x,.005,.08)-_window(y,.005,.08)) > 1e-4


def test_s27b_pedal_chick_and_foot_splash_are_distinct_foot_articulations():
    p=materialize_preset(NEW,role='drums')
    chick=render_drum_event('hat_pedal',.05,SR,.84,seed=53,patch=p)
    splash=render_drum_event('hat_foot_splash',.05,SR,.84,seed=53,patch=p)
    assert _rms(_window(chick,0,.02)) > _rms(_window(chick,.07,.10))*25
    assert _rms(_window(splash,.10,.30)) > _rms(_window(chick,.07,.10))*8
    assert not np.array_equal(chick,splash)


def test_s27b_new_articulations_are_deterministic_and_seed_sensitive():
    p=materialize_preset(NEW,role='drums')
    for kind in ('hat_tight_closed','hat_closed','hat_half_open','hat_open','hat_pedal','hat_foot_splash'):
        a=render_drum_event(kind,.05,SR,.79,seed=61,patch=p)
        b=render_drum_event(kind,.05,SR,.79,seed=61,patch=p)
        c=render_drum_event(kind,.05,SR,.79,seed=62,patch=p)
        assert np.array_equal(a,b)
        assert not np.array_equal(a,c)


def test_s27b_engine_and_midi_surfaces_cover_standard_hihat_roles():
    p=materialize_preset(NEW,role='drums')
    engine=engine_for_patch(p)
    engine.validate_ir_patch('drums',p)
    assert engine.tail_seconds(p) >= .62
    assert DRUM_NOTES['hat_closed'] == 42
    assert DRUM_NOTES['hat_tight_closed'] == 42
    assert DRUM_NOTES['hat_half_open'] == 46
    assert DRUM_NOTES['hat_open'] == 46
    assert DRUM_NOTES['hat_pedal'] == 44
    assert DRUM_NOTES['hat_foot_splash'] == 44
