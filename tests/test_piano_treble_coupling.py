"""Treble piano ringing: passive unison loss and source-bounded reinforcement."""
from copy import deepcopy

import numpy as np
import pytest
from scipy.linalg import expm
from scipy.signal import butter, sosfilt

from code_composer.audio import piano


def _patch():
    return {'kind': 'piano', 'piano_graph': {
        'strings': {'base_decay_s': 4.2, 'detune_cents': .65,
                    'unison_decoherence': {'start_midi': 61, 'decay_spread': .20}},
        'damper': {'release_s': .2, 'pedal_release_s': 1.65},
        'output_gain': .62,
    }}


def _rms(x):
    return np.sqrt(np.mean(np.asarray(x)**2))


@pytest.mark.parametrize('detune', [0., .2, 1.1, 5.])
@pytest.mark.parametrize('coupling', [0., .5, 3.])
def test_coupled_modes_are_passive_and_match_matrix_exponential(detune, coupling):
    t=np.linspace(0, 3, 301)
    f=np.array([1000-detune, 1000., 1000+detune])
    phase=np.array([.2, .73, 1.26]); tau=np.array([2.1, 2.7, 3.2]); level=np.array([.9, 1., 1.1])
    actual=piano._coupled_unison_state(t, f, phase, tau, level, coupling)
    initial=level*np.exp(1j*phase)
    matrix=np.diag(-1/tau+2j*np.pi*(f-f.mean()))-coupling*np.ones((3,3))/3
    for i in (0, 1, 50, 150, 300):
        np.testing.assert_allclose(actual[:,i], expm(matrix*t[i])@initial, atol=2e-12, rtol=2e-11)
    energy=np.sum(np.abs(actual)**2, axis=0)
    assert np.max(np.diff(energy)) <= 1e-12
    np.testing.assert_allclose(actual[:,0], initial, atol=2e-14)


def test_ill_conditioned_mode_fallback_solves_same_equation(monkeypatch):
    t=np.linspace(0, .02, 17)
    f=np.array([999.8, 1000., 1000.2]); phase=np.array([.1,.4,.7])
    tau=np.array([2.,2.,2.]); level=np.ones(3)
    expected=piano._coupled_unison_state(t,f,phase,tau,level,3.)
    monkeypatch.setattr(np.linalg,'cond',lambda _: np.inf)
    actual=piano._coupled_unison_state(t,f,phase,tau,level,3.)
    np.testing.assert_allclose(actual,expected,rtol=1e-12,atol=1e-13)


@pytest.mark.parametrize('midi', [72,76,84,88])
@pytest.mark.parametrize('sr', [24000,48000])
def test_treble_tail_reduced_without_flattening_the_attack(midi,sr,monkeypatch):
    patch=_patch(); perf={'pedal':True, 'piano_strike_seed':193}
    corrected=piano.render_piano_note(midi,2.5,sr,patch,.75,perf)
    # An ablation of coupling alone, not a second hand-written renderer.
    with monkeypatch.context() as old:
        old.setattr(piano,'_treble_coupling_rate',lambda *_:0.)
        uncoupled=piano.render_piano_note(midi,2.5,sr,patch,.75,perf)
    n=int(.05*sr)
    attack_change=20*np.log10(_rms(corrected[:n])/_rms(uncoupled[:n]))
    assert -1.1 < attack_change < .1
    assert np.corrcoef(corrected[:n].ravel(),uncoupled[:n].ravel())[0,1] > .995
    sos=butter(4,2500, 'highpass',fs=sr,output='sos')
    a=sosfilt(sos,uncoupled,axis=0); b=sosfilt(sos,corrected,axis=0)
    tail=slice(sr,int(2.5*sr))
    # Relative to each attack: this cannot pass by merely turning the track down.
    reduction=20*np.log10((_rms(b[tail])/_rms(corrected[:n]))/(_rms(a[tail])/_rms(uncoupled[:n])))
    assert reduction < -5.
    assert np.isfinite(corrected).all()
    assert len(corrected)==len(uncoupled)


@pytest.mark.parametrize('midi',[36,55,60])
def test_lower_register_does_not_enter_coupled_model(midi,monkeypatch):
    def forbidden(*_):
        raise AssertionError('low strings must stay on the existing path')
    monkeypatch.setattr(piano,'_coupled_unison_state',forbidden)
    x=piano.render_piano_note(midi,.5,24000,_patch(),.75,{'pedal':False})
    assert np.isfinite(x).all()


@pytest.mark.parametrize('pedal',[False,True])
def test_pedal_release_authority_and_determinism_preserved(pedal):
    patch=_patch(); perf={'pedal':pedal,'pedal_controlled':True}
    frozen=deepcopy((patch,perf)); sr=24000
    a=piano.render_piano_note(84,1.,sr,patch,.75,perf)
    b=piano.render_piano_note(84,1.,sr,patch,.75,perf)
    np.testing.assert_array_equal(a,b)
    assert (patch,perf)==frozen
    assert np.max(np.abs(a[-240:])) < np.max(np.abs(a))*1e-4


def test_high_resonance_uses_struck_partial_frequency_and_faster_loss():
    sr=24000; n=sr*3; midi=84; hz=440*2**((midi-69)/12)
    cfg={'gain':.025,'pedal_gain':.075,'decay_s':3.15,'ratios':[4.], 'weights':[1.]}
    model={'count':3,'inharmonicity':.000216,'decay_s':3.3,'partial_decay_power':.64}
    actual=piano._resonance_layer(hz,n,sr,midi,.75,True,cfg,string_model=model)
    f=hz*4*np.sqrt(1+model['inharmonicity']*16)
    tau=min(3.15,3.3/4**.64); loss=piano._treble_coupling_rate(midi,f,3)
    t=np.arange(n)/sr
    expected=np.sin(2*np.pi*f*t+.31*midi)*np.exp(-t/tau-loss*t)*.1*.85
    np.testing.assert_allclose(actual,expected,atol=1e-15,rtol=1e-13)
    legacy=piano._resonance_layer(hz,n,sr,midi,.75,True,cfg)
    assert _rms(actual[sr:]) < _rms(legacy[sr:])*.03


def test_reinforcement_still_obeys_noteoff_envelope():
    sr=24000; n=sr; off=np.ones(n); off[sr//2:]=0
    model={'count':3,'inharmonicity':.0002,'decay_s':3.,'partial_decay_power':.6}
    x=piano._resonance_layer(1046.5,n,sr,84,.75,True,{},noteoff_env=off,string_model=model)
    np.testing.assert_array_equal(x[sr//2:],np.zeros(n-sr//2))
