import numpy as np

from code_composer.audio.piano import render_piano_note
from code_composer.audio.piano_design import resolve_piano_design
from code_composer.presets import materialize_preset

SR=24000

def _patch(name):
    return resolve_piano_design(materialize_preset(name, role='piano'))

def _late_mod_depth(x, start_s=.75, end_s=2.1, frame_s=.035):
    mono=np.mean(np.asarray(x,dtype=np.float64),axis=1)
    a=int(start_s*SR); b=min(len(mono),int(end_s*SR)); n=max(32,int(frame_s*SR))
    vals=[]
    for i in range(a,max(a,b-n),n//2):
        w=mono[i:i+n]
        if len(w)<n: break
        vals.append(float(np.sqrt(np.mean(w*w))))
    vals=np.asarray(vals,dtype=np.float64)
    return float((np.percentile(vals,90)-np.percentile(vals,10))/(np.mean(vals)+1e-12))

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
