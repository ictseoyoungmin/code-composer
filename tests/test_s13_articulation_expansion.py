from copy import deepcopy
import numpy as np

from code_composer.presets import materialize_preset, list_presets
from code_composer.performance.violin import plan_violin_track
from code_composer.audio.engines.bowed_waveguide import (
    render_bowed_waveguide_note,
    render_bowed_waveguide_track,
)


def _patch(pid='bowed.violin.modeled_articulated'):
    return materialize_preset(pid, role='lead')


def _ev(start, midi, art, dur=.5, vel=.68):
    return {
        'start_beat': float(start), 'duration_beats': float(dur),
        'midi': int(midi), 'velocity': float(vel),
        'performance': {'articulation': art},
    }


def test_s13_factory_surface_adds_articulated_violin_only():
    ids=[x['preset_id'] for x in list_presets(family='violin')]
    assert 'bowed.violin.modeled_articulated' in ids
    assert len(ids)==8
    patch=_patch()
    assert patch['bowed_waveguide_graph']['articulation_expansion']['enabled'] is True


def test_s13_planner_annotates_pizzicato_spiccato_and_harmonic():
    events=[
        _ev(0, 69, 'pizzicato'),
        _ev(1, 74, 'spiccato'),
        _ev(2, 81, 'harmonic'),
        _ev(3, 83, 'harmonic'),
    ]
    plan=plan_violin_track(events,bpm=96)
    techniques=[x.get('technique') for x in plan['events']]
    assert techniques[0]['mode']=='pizzicato' and techniques[0]['bow_contact'] is False
    assert techniques[1]['mode']=='spiccato' and techniques[1]['bow_contact']=='intermittent'
    assert techniques[2]['mode']=='harmonic' and techniques[2]['harmonic_type']=='natural'
    assert techniques[2]['partial'] >= 2
    assert techniques[3]['mode']=='harmonic'
    assert techniques[3]['harmonic_type'] in {'natural','artificial_fourth','modeled_sounding_pitch'}


def test_s13_pizzicato_is_deterministic_and_freely_decays():
    p=_patch(); sr=12000
    perf={'articulation':'pizzicato'}
    a=render_bowed_waveguide_note(69,.32,sr,p,velocity=.7,performance=perf)
    b=render_bowed_waveguide_note(69,.32,sr,p,velocity=.7,performance=perf)
    assert np.array_equal(a,b)
    assert len(a) >= int(.9*sr)
    early=float(np.sqrt(np.mean(a[int(.03*sr):int(.12*sr),0]**2)))
    late=float(np.sqrt(np.mean(a[int(.72*sr):int(.92*sr),0]**2)))
    assert early > late * 1.5
    assert np.max(np.abs(a)) <= 1.0


def test_s13_harmonic_is_deterministic_and_spectrally_distinct():
    p=_patch(); sr=12000
    base=render_bowed_waveguide_note(81,.38,sr,p,velocity=.62,performance={'articulation':'tenuto'})[:,0]
    h1=render_bowed_waveguide_note(81,.38,sr,p,velocity=.62,performance={'articulation':'harmonic'})[:,0]
    h2=render_bowed_waveguide_note(81,.38,sr,p,velocity=.62,performance={'articulation':'harmonic'})[:,0]
    assert np.array_equal(h1,h2)
    n=min(len(base),len(h1)); base=base[:n]; h1=h1[:n]
    assert not np.array_equal(base,h1)
    freqs=np.fft.rfftfreq(n,1/sr)
    def centroid(x):
        mag=np.abs(np.fft.rfft(x))+1e-12
        return float((freqs*mag).sum()/mag.sum())
    assert centroid(h1) > centroid(base) * 1.03


def test_s13_spiccato_detaches_and_differs_from_staccato():
    p=_patch(); sr=12000
    sp=render_bowed_waveguide_note(74,.42,sr,p,velocity=.72,performance={'articulation':'spiccato'})[:,0]
    st=render_bowed_waveguide_note(74,.42,sr,p,velocity=.72,performance={'articulation':'staccato'})[:,0]
    n=min(len(sp),len(st)); sp=sp[:n]; st=st[:n]
    assert not np.array_equal(sp,st)
    # Spiccato should retain free string energy after the brief contact window.
    tail=slice(int(.12*sr), min(n,int(.35*sr)))
    assert float(np.sqrt(np.mean(sp[tail]**2))) > 1e-6


def test_s13_disabled_is_byte_identical_to_s12_realistic_for_arco():
    p12=_patch('bowed.violin.modeled_realistic')
    p13=_patch(); p13=deepcopy(p13)
    p13['bowed_waveguide_graph']['articulation_expansion']['enabled']=False
    perf={'articulation':'tenuto','instrument_expression':{'vibrato_depth_cents':17.0}}
    a=render_bowed_waveguide_note(71,.28,10000,p12,velocity=.66,performance=perf)
    b=render_bowed_waveguide_note(71,.28,10000,p13,velocity=.66,performance=perf)
    assert np.array_equal(a,b)


def test_s13_mixed_track_renders_without_clipping():
    p=_patch(); sr=10000; beat_s=.5
    events=[_ev(0,69,'tenuto',.75),_ev(1,71,'pizzicato',.45),_ev(2,74,'spiccato',.35),_ev(3,81,'harmonic',.7)]
    # Attach physical realization needed by the continuous arco segment.
    plan=plan_violin_track(events,bpm=120)
    by={(x['start_beat'],x['midi']):x for x in plan['events']}
    realized=[]
    for ev in events:
        x=deepcopy(ev); item=by[(x['start_beat'],x['midi'])]
        x['performance']['violin_realization']={
            'left_hand':deepcopy(item['left_hand']),
            'transition':deepcopy(item['transition']),
            'bow':deepcopy(item['bow']),
        }
        if 'technique' in item:
            x['performance']['violin_realization']['technique']=deepcopy(item['technique'])
        realized.append(x)
    y=render_bowed_waveguide_track(realized,int(3.0*sr),sr,p,beat_s,gain=.8,pan=0)
    assert y is not None and y.shape==(int(3.0*sr),2)
    assert np.isfinite(y).all()
    assert float(np.max(np.abs(y))) <= 1.0
