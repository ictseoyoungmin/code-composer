import math
import json
from pathlib import Path

import numpy as np
import pytest

from code_composer.audio.engines import engine_for_patch, registered_engines
from code_composer.audio.engines.bowed_waveguide import render_bowed_waveguide_note
from code_composer.presets import materialize_preset, list_presets

ROOT=Path(__file__).resolve().parents[1]


def patch():
    return materialize_preset('bowed.violin.modeled_open',role='lead')


def dominant_frequency(x, sr, target):
    x=np.asarray(x,dtype=float)
    x=x*np.hanning(len(x))
    spec=np.abs(np.fft.rfft(x))
    freqs=np.fft.rfftfreq(len(x),1/sr)
    mask=(freqs>target*.75)&(freqs<target*1.25)
    return float(freqs[mask][np.argmax(spec[mask])])


def test_waveguide_engine_is_registered_and_deterministic():
    p=patch()
    assert 'bowed_waveguide' in registered_engines()
    assert engine_for_patch(p).name=='bowed_waveguide'
    a=render_bowed_waveguide_note(69,1.0,22050,p,velocity=.72,performance={'articulation':'tenuto'})
    b=render_bowed_waveguide_note(69,1.0,22050,p,velocity=.72,performance={'articulation':'tenuto'})
    assert np.array_equal(a,b)
    assert a.ndim==2 and a.shape[1]==2
    assert np.max(np.abs(a))>.01


def test_modeled_preset_is_new_and_synthetic_preset_remains_unchanged_surface():
    metas={x['preset_id']:x for x in list_presets(family='violin')}
    assert set(metas)=={'bowed.violin.modeled_admittance','bowed.violin.modeled_articulated','bowed.violin.modeled_continuous','bowed.violin.modeled_coupled','bowed.violin.modeled_expression','bowed.violin.modeled_open','bowed.violin.modeled_realistic','bowed.violin.synthetic_warm'}
    assert metas['bowed.violin.modeled_open']['engine']=='bowed_waveguide'
    old=materialize_preset('bowed.violin.synthetic_warm',role='lead')
    assert old['engine']=='bowed_string'
    assert old['kind']=='bowed_string'


def test_modeled_a4_tracks_pitch_and_sustains_energy():
    sr=22050; y=render_bowed_waveguide_note(69,2.2,sr,patch(),velocity=.72,performance={'articulation':'tenuto'})[:,0]
    steady=y[int(.55*sr):int(1.75*sr)]
    hz=dominant_frequency(steady,sr,440.0)
    cents=1200*math.log2(hz/440.0)
    assert abs(cents)<12
    early=y[int(.35*sr):int(.65*sr)]
    late=y[int(1.45*sr):int(1.75*sr)]
    er=float(np.sqrt(np.mean(early*early))+1e-12)
    lr=float(np.sqrt(np.mean(late*late))+1e-12)
    assert .60 < lr/er < 1.45


def test_bow_controls_drive_causal_waveguide_result():
    p=patch()
    low=render_bowed_waveguide_note(69,.9,22050,p,velocity=.7,performance={'instrument_expression':{'bow_pressure':.25,'bow_speed':.38}})
    high=render_bowed_waveguide_note(69,.9,22050,p,velocity=.7,performance={'instrument_expression':{'bow_pressure':.82,'bow_speed':.76}})
    n=min(len(low),len(high))
    assert not np.array_equal(low[:n],high[:n])
    corr=float(np.corrcoef(low[:n,0],high[:n,0])[0,1])
    assert corr < .995


def test_modeled_preset_exposes_capability_not_musical_content():
    cat=json.loads((ROOT/'skills/code-composer/kit/presets/CATALOG.json').read_text())
    meta=next(x for x in cat['presets'] if x['preset_id']=='bowed.violin.modeled_open')
    assert 'patch' not in meta
    assert meta['musical_content'] is False
    assert meta['expression_capabilities']['bow_pressure'] is True
    assert all(k not in json.dumps(meta).lower() for k in ['"notes"','"chords"','"progression"'])


def test_invalid_waveguide_geometry_is_rejected():
    p=patch(); p['bowed_waveguide_graph']['bow']['position']=.9
    with pytest.raises(Exception):
        engine_for_patch(p).validate_authoring_patch('lead',p)
