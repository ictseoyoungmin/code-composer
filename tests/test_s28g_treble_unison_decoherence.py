import numpy as np
import pytest
from scipy.signal import butter, detrend, sosfilt

from code_composer.audio import piano
from code_composer.audio.piano import render_piano_note
from code_composer.audio.piano_design import resolve_piano_design
from code_composer.presets import materialize_preset

SR=24000

def _patch(name):
    return resolve_piano_design(materialize_preset(name, role='piano'))

def _late_mod_depth(x, start_s=.75, end_s=2.1, frame_s=.035):
    """Amplitude modulation in dB, excluding the exponential decay trend.

    Raw RMS percentile spread confounds smooth natural decay with beating.
    A pure exponential is linear in log amplitude; remove that slope before
    comparing residual modulation. This is not a loudness or tail-energy metric.
    """
    mono=np.mean(np.asarray(x,dtype=np.float64),axis=1)
    a=int(start_s*SR); b=min(len(mono),int(end_s*SR)); n=max(32,int(frame_s*SR))
    vals=[]
    for i in range(a,max(a,b-n),n//2):
        w=mono[i:i+n]
        if len(w)<n: break
        vals.append(float(np.sqrt(np.mean(w*w))))
    vals=np.asarray(vals,dtype=np.float64)
    if len(vals)<3:
        raise ValueError('modulation measurement requires at least three RMS frames')
    residual=detrend(20.0*np.log10(np.maximum(vals,1e-12)),type='linear')
    return float(np.percentile(residual,90)-np.percentile(residual,10))

@pytest.mark.parametrize('decay_s',[.3,.6,1.5,3.0])
def test_modulation_metric_rejects_smooth_decay_but_detects_beating(decay_s):
    t=np.arange(int(2.2*SR),dtype=np.float64)/SR
    smooth=np.sin(2*np.pi*1000*t)*np.exp(-t/decay_s)
    modulated=smooth*(1.0+.25*np.sin(2*np.pi*4*t))
    assert _late_mod_depth(np.column_stack([smooth,smooth])) < 1e-8
    assert _late_mod_depth(np.column_stack([modulated,modulated])) > 3.0

def test_s28g_candidate_preserves_three_string_count_and_mean_detune_controls():
    a=_patch('piano.concert_grand_natural')
    b=_patch('piano.concert_grand_natural_unison_subtle')
    sa=a['piano_graph']['strings']; sb=b['piano_graph']['strings']
    assert sa['high_strings']==sb['high_strings']==3
    assert sa['detune_cents']==sb['detune_cents']
    assert sb['unison_decoherence']['partial_mistune_cents']>0
    assert sb['unison_decoherence']['decay_spread']>0

def test_s28g_baseline_natural_preset_remains_byte_exact_when_feature_is_disabled():
    a=_patch('piano.concert_grand_natural')
    b=_patch('piano.concert_grand_natural')
    perf={'piano_strike_seed':2820,'piano_strike_ordinal':1}
    x=render_piano_note(76,2.2,SR,a,velocity=.75,performance=perf)
    y=render_piano_note(76,2.2,SR,b,velocity=.75,performance=perf)
    assert np.array_equal(x,y)

def test_s28g_same_seed_is_deterministic():
    p=_patch('piano.concert_grand_natural_unison_subtle')
    perf={'piano_strike_seed':2820,'piano_strike_ordinal':1}
    x=render_piano_note(76,2.2,SR,p,velocity=.75,performance=perf)
    y=render_piano_note(76,2.2,SR,p,velocity=.75,performance=perf)
    assert np.array_equal(x,y)

def test_s28g_treble_modulation_reduces_without_collapsing_attack_character():
    a=_patch('piano.concert_grand_natural')
    b=_patch('piano.concert_grand_natural_unison_subtle')
    perf={'piano_strike_seed':2820,'piano_strike_ordinal':1}
    x=render_piano_note(76,2.2,SR,a,velocity=.75,performance=perf)
    y=render_piano_note(76,2.2,SR,b,velocity=.75,performance=perf)
    ma=_late_mod_depth(x); mb=_late_mod_depth(y)
    assert mb < ma
    assert mb > ma*.70  # subtle: do not flatten the unison into a clean synthetic tone
    n=int(.25*SR)
    xm=np.mean(x[:n],axis=1); ym=np.mean(y[:n],axis=1)
    corr=float(np.corrcoef(xm,ym)[0,1])
    assert corr>.985

def test_s28g_low_single_string_register_is_unchanged():
    a=_patch('piano.concert_grand_natural')
    b=_patch('piano.concert_grand_natural_unison_subtle')
    perf={'piano_strike_seed':2820,'piano_strike_ordinal':1}
    x=render_piano_note(36,2.2,SR,a,velocity=.75,performance=perf)
    y=render_piano_note(36,2.2,SR,b,velocity=.75,performance=perf)
    assert np.array_equal(x,y)

@pytest.mark.parametrize('preset',[
    'piano.concert_grand_natural','piano.concert_grand_natural_unison_subtle',
])
@pytest.mark.parametrize('midi',[76,84,88])
def test_factory_treble_tail_reduction_relative_to_attack(preset,midi,monkeypatch):
    patch=_patch(preset)
    perf={'pedal':True,'piano_strike_seed':2820,'piano_strike_ordinal':1}
    corrected=render_piano_note(midi,2.5,SR,patch,velocity=.75,performance=perf)
    with monkeypatch.context() as old:
        old.setattr(piano,'_treble_coupling_rate',lambda *_:0.0)
        uncoupled=render_piano_note(midi,2.5,SR,patch,velocity=.75,performance=perf)
    def rms(x):
        return float(np.sqrt(np.mean(np.asarray(x)**2)))
    attack=slice(0,int(.05*SR)); tail=slice(SR,int(2.5*SR))
    attack_change=20*np.log10(rms(corrected[attack])/rms(uncoupled[attack]))
    assert -1.1 < attack_change < .1
    assert np.corrcoef(corrected[attack].ravel(),uncoupled[attack].ravel())[0,1] > .99
    sos=butter(4,2500,'highpass',fs=SR,output='sos')
    a=sosfilt(sos,uncoupled,axis=0); b=sosfilt(sos,corrected,axis=0)
    reduction=20*np.log10((rms(b[tail])/rms(corrected[attack]))/(rms(a[tail])/rms(uncoupled[attack])))
    assert reduction < -5.0  # Cannot pass by simply lowering the entire track.
