import numpy as np
from scipy.signal import resample_poly

from code_composer.audio.piano import render_piano_note


def _electric(mechanism):
    return {
        "kind":"piano",
        "piano_design":{
            "family":"electric",
            "categories":{
                "mechanism":mechanism,
                "pickup":"bright",
                "amp":"clean_combo",
                "modulation":"none",
                "perspective":"centered",
            },
            "controls":{
                "bell_gain":0.48,
                "bark_gain":0.20,
                "pickup_drive":1.25,
                "amp_drive":1.20,
                "output_gain":0.56,
            },
        },
    }


def _mono(x):
    return .5*(x[:,0]+x[:,1])


def test_low_output_rate_tracks_44k_reference_after_polyphase_downsample():
    """Low-rate electric rendering must not invent a different aliased timbre."""
    for mechanism in ("tine","reed","digital_fm"):
        low=render_piano_note(104,.55,22050,_electric(mechanism),velocity=.88)
        hi=render_piano_note(104,.55,44100,_electric(mechanism),velocity=.88)
        ref=resample_poly(hi,1,2,axis=0)
        n=min(len(low),len(ref))
        a=_mono(low[:n]); b=_mono(ref[:n])
        # Ignore edge guard / FIR tail and compare the sustained body.
        lo=int(.03*22050); hi_i=min(n,int(.45*22050))
        corr=float(np.corrcoef(a[lo:hi_i],b[lo:hi_i])[0,1])
        assert corr > .93, (mechanism,corr)


def test_electric_high_register_has_no_sample_clipping():
    for mechanism in ("tine","reed","digital_fm"):
        x=render_piano_note(108,.40,44100,_electric(mechanism),velocity=.95)
        assert np.max(np.abs(x)) < 1.0
        assert np.mean(np.abs(x)>=.999) == 0.0
