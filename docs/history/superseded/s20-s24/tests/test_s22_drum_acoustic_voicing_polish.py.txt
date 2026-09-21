import hashlib
import numpy as np
import pytest
from code_composer.drum_analysis import analyze_drum_hit
from code_composer.percussion import render_drum_event
from code_composer.presets import PresetError, list_presets, materialize_preset

SR=24000

def _s21(): return materialize_preset('drums.acoustic_kit_modeled_realistic', role='drums')
def _s22(): return materialize_preset('drums.acoustic_kit_modeled_polished', role='drums')
def _mono(y): return y.mean(axis=1)
def _top12(y):
    x=_mono(y); p=np.abs(np.fft.rfft(x*np.hanning(len(x))))**2+1e-20
    f=np.fft.rfftfreq(len(x),1/SR); q=p[(f>=250)&(f<=11000)]; q=q/q.sum()
    return float(np.sort(q)[-12:].sum())
def _hash(y): return hashlib.sha256(y.tobytes()).hexdigest()

def test_s22_registers_separate_opt_in_polished_preset():
    ids={x['preset_id'] for x in list_presets(engine='percussion')}
    assert {'drums.acoustic_kit_modeled_realistic','drums.acoustic_kit_modeled_polished'} <= ids
    p=_s22(); assert p['drum_graph']['voicing_polish']['enabled'] is True
    assert p['preset_provenance']['preset_id']=='drums.acoustic_kit_modeled_polished'

def test_s22_s21_preset_remains_without_polish_and_byte_stable():
    p=_s21(); assert 'voicing_polish' not in p['drum_graph']
    expected={}
    for kind,art in [('kick',None),('snare','center'),('ride','bow')]:
        y=render_drum_event(kind,.10,SR,.82,seed=17,patch=p,articulation=art)
        expected[(kind,art)]=_hash(y)
    # Re-materialization must be exactly stable and S22 must not mutate S21 data.
    p2=_s21()
    for (kind,art),h in expected.items():
        assert _hash(render_drum_event(kind,.10,SR,.82,seed=17,patch=p2,articulation=art))==h

def test_s22_is_deterministic_for_all_major_dry_sources():
    p=_s22()
    for kind,art in [('kick',None),('snare','center'),('hat','closed'),('hat','open'),('ride','bow'),('ride','bell'),('crash','crash'),('tom_mid','center')]:
        a=render_drum_event(kind,.10,SR,.82,seed=23,patch=p,articulation=art)
        b=render_drum_event(kind,.10,SR,.82,seed=23,patch=p,articulation=art)
        assert np.array_equal(a,b)
        assert float(np.max(np.abs(a))) < 1.0

def test_s22_cymbal_voicing_reduces_narrow_peak_dominance():
    a,b=_s21(),_s22()
    for kind,art in [('hat','open'),('ride','bow'),('ride','bell'),('crash','crash')]:
        old=render_drum_event(kind,.10,SR,.82,seed=17,patch=a,articulation=art)
        new=render_drum_event(kind,.10,SR,.82,seed=17,patch=b,articulation=art)
        assert _top12(new) < _top12(old)*.70

def test_s22_snare_keeps_body_and_air_without_s21_brittleness():
    old=analyze_drum_hit(render_drum_event('snare',.10,SR,.82,seed=17,patch=_s21(),articulation='center'),SR)
    new=analyze_drum_hit(render_drum_event('snare',.10,SR,.82,seed=17,patch=_s22(),articulation='center'),SR)
    assert new['body_ratio_120_500'] > .50
    assert new['air_ratio_7k_16k'] > .12
    assert 2200 < new['centroid_hz'] < 3200
    assert new['centroid_hz'] < old['centroid_hz']-400

def test_s22_kick_preserves_sub_weight_while_softening_contact():
    old=analyze_drum_hit(render_drum_event('kick',.10,SR,.82,seed=17,patch=_s21()),SR)
    new=analyze_drum_hit(render_drum_event('kick',.10,SR,.82,seed=17,patch=_s22()),SR)
    assert new['low_ratio_20_120'] > .98
    assert abs(new['centroid_hz']-old['centroid_hz']) < 4
    assert new['body_ratio_120_500'] >= old['body_ratio_120_500']*.95

def test_s22_toms_keep_tuning_order_and_long_body():
    p=_s22(); cent=[]
    for kind in ('tom_high','tom_mid','tom_floor'):
        m=analyze_drum_hit(render_drum_event(kind,.10,SR,.82,seed=13,patch=p,articulation='center'),SR)
        cent.append(m['centroid_hz']); assert m['decay_time_s'] > .65
    assert cent[0] > cent[1] > cent[2]

def test_s22_cymbal_articulation_identity_survives_polish():
    p=_s22()
    bow=analyze_drum_hit(render_drum_event('ride',.08,SR,.82,seed=19,patch=p,articulation='bow'),SR)
    bell=analyze_drum_hit(render_drum_event('ride',.08,SR,.82,seed=19,patch=p,articulation='bell'),SR)
    closed=analyze_drum_hit(render_drum_event('hat',.06,SR,.76,seed=31,patch=p,articulation='closed'),SR)
    openh=analyze_drum_hit(render_drum_event('hat',.06,SR,.76,seed=31,patch=p,articulation='open'),SR)
    assert bell['centroid_hz'] > bow['centroid_hz'] + 250
    assert openh['decay_time_s'] > closed['decay_time_s']*8

def test_s22_polish_parameter_bounds_fail_loudly():
    with pytest.raises(PresetError):
        materialize_preset('drums.acoustic_kit_modeled_polished', role='drums', patch_overrides={'drum_graph':{'voicing_polish':{'cymbal_initial_gain':1.4}}})
    with pytest.raises(PresetError):
        materialize_preset('drums.acoustic_kit_modeled_polished', role='drums', patch_overrides={'drum_graph':{'voicing_polish':{'snare_wire_lowpass_hz':1000}}})

def test_s22_polish_requires_acoustic_core():
    with pytest.raises(PresetError):
        materialize_preset('drums.acoustic_kit_modeled_polished', role='drums', patch_overrides={'drum_graph':{'acoustic_core_hardening':{'enabled':False},'voicing_polish':{'enabled':True}}})
