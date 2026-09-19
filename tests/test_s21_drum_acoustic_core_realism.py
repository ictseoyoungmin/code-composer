import hashlib
import numpy as np
import pytest

from code_composer.drum_analysis import analyze_drum_hit
from code_composer.percussion import render_drum_event
from code_composer.presets import PresetError, list_presets, materialize_preset

SR=24000


def _old():
    return materialize_preset('drums.acoustic_kit_modeled', role='drums')


def _new():
    return materialize_preset('drums.acoustic_kit_modeled_realistic', role='drums')


def _hash(x):
    return hashlib.sha256(x.tobytes()).hexdigest()


def _mono(y):
    return y.mean(axis=1) if getattr(y, 'ndim', 1)==2 else y


def _spectral_density(y):
    x=_mono(y)
    p=np.abs(np.fft.rfft(x*np.hanning(len(x))))**2 + 1e-20
    f=np.fft.rfftfreq(len(x),1.0/SR)
    p=p[(f>=250)&(f<=11000)]
    q=p/float(np.sum(p))
    entropy=float(-np.sum(q*np.log(q))/np.log(len(q)))
    top12=float(np.sort(q)[-12:].sum())
    return entropy,top12


def test_s21_registers_separate_opt_in_realistic_acoustic_core_preset():
    ids={x['preset_id'] for x in list_presets(engine='percussion')}
    assert {'drums.acoustic_kit_modeled','drums.acoustic_kit_modeled_realistic'} <= ids
    patch=_new()
    assert patch['drum_graph']['acoustic_core_hardening']['enabled'] is True
    assert patch['preset_provenance']['preset_id']=='drums.acoustic_kit_modeled_realistic'


def test_s21_s20_preset_and_existing_default_hits_remain_byte_identical():
    patch=_old()
    assert 'acoustic_core_hardening' not in patch['drum_graph']
    expected={
        'kick':'380e698edfe82884757e23a81f8318a61d973968ba8c4c11e8a99d450a034df6',
        'snare':'aaf1e8e3e15d2e64d746a6d635716a0db3e71c122a25c86cc79ae8382686ecaf',
        'hat':'7b6b0613fdbc8af958d7a1c57f0faeb3c3693ec2ca0f5c1d7b168b23e06cd558',
    }
    for kind in ('kick','snare','hat'):
        y=render_drum_event(kind,.1,SR,.8,seed=17,patch=patch)
        assert _hash(y)==expected[kind]


def test_s21_acoustic_core_is_deterministic_but_materially_changes_dry_source():
    patch=_new()
    for kind,art in [('kick','default'),('snare','center'),('hat','closed'),('ride','bow'),('crash','crash'),('tom_mid','center')]:
        a=render_drum_event(kind,.08,SR,.82,seed=29,patch=patch,articulation=art)
        b=render_drum_event(kind,.08,SR,.82,seed=29,patch=patch,articulation=art)
        assert np.array_equal(a,b)
        assert float(np.max(np.abs(a))) < 1.0


def test_s21_dense_cymbal_core_reduces_sparse_peak_dominance():
    old,new=_old(),_new()
    for kind,art in [('hat','closed'),('ride','bow'),('ride','bell'),('crash','crash')]:
        a=render_drum_event(kind,.08,SR,.82,seed=17,patch=old,articulation=art)
        b=render_drum_event(kind,.08,SR,.82,seed=17,patch=new,articulation=art)
        ea,ta=_spectral_density(a); eb,tb=_spectral_density(b)
        assert eb > ea + .03
        assert tb < ta * .70


def test_s21_ride_bell_remains_brighter_and_shorter_than_bow():
    patch=_new()
    bow=analyze_drum_hit(render_drum_event('ride',.08,SR,.82,seed=19,patch=patch,articulation='bow'),SR)
    bell=analyze_drum_hit(render_drum_event('ride',.08,SR,.82,seed=19,patch=patch,articulation='bell'),SR)
    assert bell['centroid_hz'] > bow['centroid_hz'] + 350
    assert bell['decay_time_s'] < bow['decay_time_s']


def test_s21_snare_moves_energy_back_into_coupled_body_without_losing_wire_air():
    old,new=_old(),_new()
    a=analyze_drum_hit(render_drum_event('snare',.10,SR,.82,seed=17,patch=old,articulation='center'),SR)
    b=analyze_drum_hit(render_drum_event('snare',.10,SR,.82,seed=17,patch=new,articulation='center'),SR)
    assert b['body_ratio_120_500'] > a['body_ratio_120_500'] * 2.5
    assert b['air_ratio_7k_16k'] > .12
    assert b['centroid_hz'] < a['centroid_hz'] - 900


def test_s21_kick_preserves_low_end_while_adding_coupled_body_structure():
    old,new=_old(),_new()
    a=analyze_drum_hit(render_drum_event('kick',.10,SR,.82,seed=17,patch=old),SR)
    b=analyze_drum_hit(render_drum_event('kick',.10,SR,.82,seed=17,patch=new),SR)
    assert b['low_ratio_20_120'] > .98
    assert b['body_ratio_120_500'] > a['body_ratio_120_500'] * 1.8
    assert 40 < b['centroid_hz'] < 80


def test_s21_toms_keep_high_mid_floor_tuning_and_long_membrane_decay():
    patch=_new(); c={}
    for kind in ('tom_high','tom_mid','tom_floor'):
        hit=render_drum_event(kind,.10,SR,.82,seed=13,patch=patch,articulation='center')
        m=analyze_drum_hit(hit,SR); c[kind]=m['centroid_hz']
        assert m['body_ratio_120_500'] > (.90 if kind!='tom_floor' else .10)
        assert m['decay_time_s'] > .65
    assert c['tom_high'] > c['tom_mid'] > c['tom_floor']


def test_s21_open_hat_and_crash_keep_long_free_vibration_tails():
    patch=_new()
    open_hat=analyze_drum_hit(render_drum_event('hat',.06,SR,.76,seed=31,patch=patch,articulation='open'),SR)
    crash=analyze_drum_hit(render_drum_event('crash',.08,SR,.86,seed=23,patch=patch,articulation='crash'),SR)
    assert open_hat['decay_time_s'] > .9
    assert crash['decay_time_s'] > 1.8


def test_s21_acoustic_core_parameter_bounds_fail_loudly():
    with pytest.raises(PresetError):
        materialize_preset('drums.acoustic_kit_modeled_realistic', role='drums', patch_overrides={
            'drum_graph':{'acoustic_core_hardening':{'cymbal_mode_count':120}}
        })
    with pytest.raises(PresetError):
        materialize_preset('drums.acoustic_kit_modeled_realistic', role='drums', patch_overrides={
            'drum_graph':{'acoustic_core_hardening':{'kick_head_pair_split':.4}}
        })
