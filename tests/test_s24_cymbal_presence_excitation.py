import hashlib
import numpy as np
import pytest
from code_composer.drum_analysis import analyze_drum_hit
from code_composer.percussion import render_drum_event
from code_composer.presets import PresetError, list_presets, materialize_preset

SR=24000

def _s23(): return materialize_preset('drums.acoustic_kit_modeled_expressive', role='drums')
def _s24(): return materialize_preset('drums.acoustic_kit_modeled_cymbal_presence', role='drums')
def _hash(y): return hashlib.sha256(y.tobytes()).hexdigest()
def _mono(y): return np.asarray(y).mean(axis=1)
def _band_ratio(y,lo,hi):
    x=_mono(y); w=np.hanning(len(x)); p=np.abs(np.fft.rfft(x*w))**2+1e-20
    f=np.fft.rfftfreq(len(x),1/SR); total=p[(f>=500)&(f<=11500)].sum()
    return float(p[(f>=lo)&(f<hi)].sum()/max(total,1e-20))
def _crest(y):
    x=np.abs(_mono(y)); return float(np.max(x)/(np.sqrt(np.mean(x*x))+1e-12))

def test_s24_registers_separate_opt_in_cymbal_presence_preset():
    ids={x['preset_id'] for x in list_presets(engine='percussion')}
    assert 'drums.acoustic_kit_modeled_cymbal_presence' in ids
    p=_s24(); assert p['drum_graph']['cymbal_presence_hardening']['enabled'] is True

def test_s24_s23_preset_remains_byte_identical_for_non_cymbals_and_stable_for_s23_cymbals():
    a,b=_s23(),_s24()
    for kind,art in [('kick',None),('snare','center'),('tom_mid','center')]:
        old=render_drum_event(kind,.10,SR,.82,seed=17,patch=a,articulation=art,strike_force=.74,strike_position=.42)
        new=render_drum_event(kind,.10,SR,.82,seed=17,patch=b,articulation=art,strike_force=.74,strike_position=.42)
        assert _hash(new)==_hash(old)
    a2=_s23()
    for kind,art in [('hat','open'),('ride','bow'),('crash','crash')]:
        assert _hash(render_drum_event(kind,.10,SR,.82,seed=17,patch=a2,articulation=art)) == _hash(render_drum_event(kind,.10,SR,.82,seed=17,patch=a,articulation=art))

def test_s24_cymbals_are_deterministic():
    p=_s24()
    for kind,art in [('hat','open'),('ride','bow'),('ride','bell'),('crash','crash')]:
        a=render_drum_event(kind,.10,SR,.82,seed=23,patch=p,articulation=art,strike_force=.78,strike_position=.66)
        b=render_drum_event(kind,.10,SR,.82,seed=23,patch=p,articulation=art,strike_force=.78,strike_position=.66)
        assert np.array_equal(a,b)

def test_s24_presence_moves_energy_from_hiss_to_metal_body():
    old,new=_s23(),_s24()
    for kind,art in [('hat','open'),('ride','bow'),('crash','crash')]:
        a=render_drum_event(kind,.10,SR,.82,seed=17,patch=old,articulation=art,strike_force=.82,strike_position=.58)
        b=render_drum_event(kind,.10,SR,.82,seed=17,patch=new,articulation=art,strike_force=.82,strike_position=.58)
        old_body=_band_ratio(a,1800,8000); new_body=_band_ratio(b,1800,8000)
        old_hiss=_band_ratio(a,9000,11500); new_hiss=_band_ratio(b,9000,11500)
        assert new_body > old_body*.90
        assert new_hiss < old_hiss*.40
        assert new_body/max(new_hiss,1e-9) > (old_body/max(old_hiss,1e-9))*2.0

def test_s24_cymbal_presence_is_stronger_without_runaway_peak():
    old,new=_s23(),_s24()
    for kind,art,min_ratio,max_ratio in [('hat','open',1.05,1.65),('ride','bow',1.12,1.85),('crash','crash',1.18,2.0)]:
        a=render_drum_event(kind,.10,SR,.82,seed=17,patch=old,articulation=art)
        b=render_drum_event(kind,.10,SR,.82,seed=17,patch=new,articulation=art)
        ra=float(np.sqrt(np.mean(a*a))); rb=float(np.sqrt(np.mean(b*b)))
        assert min_ratio < rb/ra < max_ratio
        assert float(np.max(np.abs(b))) < .98

def test_s24_attack_reads_as_metal_not_static_only():
    p=_s24()
    for kind,art in [('ride','bow'),('ride','bell'),('crash','crash')]:
        y=render_drum_event(kind,.10,SR,.88,seed=19,patch=p,articulation=art,strike_force=.88,strike_position=.55)
        m=analyze_drum_hit(y,SR)
        assert m['centroid_hz'] > 2400
        assert _band_ratio(y,1800,8000) > .42
        assert _crest(y) < 9.0

def test_s24_ride_bell_and_bow_identity_survives_presence_hardening():
    p=_s24()
    bow=analyze_drum_hit(render_drum_event('ride',.10,SR,.82,seed=19,patch=p,articulation='bow'),SR)
    bell=analyze_drum_hit(render_drum_event('ride',.10,SR,.82,seed=19,patch=p,articulation='bell'),SR)
    assert bell['centroid_hz'] > bow['centroid_hz'] + 180

def test_s24_hat_openness_identity_survives_presence_hardening():
    p=_s24()
    closed=analyze_drum_hit(render_drum_event('hat',.06,SR,.76,seed=31,patch=p,articulation='closed'),SR)
    openh=analyze_drum_hit(render_drum_event('hat',.06,SR,.76,seed=31,patch=p,articulation='open'),SR)
    assert openh['decay_time_s'] > closed['decay_time_s']*8

def test_s24_presence_parameter_bounds_fail_loudly():
    with pytest.raises(PresetError):
        materialize_preset('drums.acoustic_kit_modeled_cymbal_presence', role='drums', patch_overrides={'drum_graph':{'cymbal_presence_hardening':{'wash_modal_correlation':1.2}}})
    with pytest.raises(PresetError):
        materialize_preset('drums.acoustic_kit_modeled_cymbal_presence', role='drums', patch_overrides={'drum_graph':{'cymbal_presence_hardening':{'crash_output_gain_scale':3.6}}})

def test_s24_presence_requires_voicing_polish():
    with pytest.raises(PresetError):
        materialize_preset('drums.acoustic_kit_modeled_cymbal_presence', role='drums', patch_overrides={'drum_graph':{'voicing_polish':{'enabled':False},'cymbal_presence_hardening':{'enabled':True}}})
