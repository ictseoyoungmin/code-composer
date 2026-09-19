import numpy as np
from code_composer.instrument import synth_patch_note
from code_composer.timbre_analysis import onset_click_score, high_band_ratio, spectral_flatness, harmonic_concentration
from code_composer.theory import midi_to_hz


def run():
    sr=44100
    old={"graph":{
        "oscillators":[
            {"waveform":"sine","gain":0.68},
            {"waveform":"triangle","gain":0.22,"octave":1},
            {"waveform":"sine","gain":0.10,"octave":2},
        ],
        "unison":{"voices":2,"detune_cents":4,"stereo_width":0.22},
        "envelope":{"attack":0.004,"decay":0.10,"sustain":0.42,"release":0.13},
        "filter":{"type":"highpass","cutoff":420},
        "lfo":{"rate_hz":5.0,"pitch_cents":2.2,"amp_depth":0.0},
        "waveshaper":{"type":"softclip","drive":1.10},
        "output_gain":0.56,
    }}
    new={"graph":{
        "oscillators":[
            {"waveform":"sine","gain":0.91},
            {"waveform":"sine","gain":0.065,"octave":1},
            {"waveform":"triangle","gain":0.025,"octave":1},
        ],
        "unison":{"voices":1,"detune_cents":0,"stereo_width":0.0},
        "pitch_envelope":{"start_cents":-7.0,"end_cents":0.0,"time_s":0.042},
        "envelope":{"attack":0.018,"decay":0.09,"sustain":0.72,"release":0.12},
        "breath":{"gain":0.008,"low_cutoff":1700,"high_cutoff":5600,"attack":0.050,"release":0.070,"seed":73},
        "attack_partial":{"gain":0.016,"harmonic":2.0,"attack_s":0.006,"decay_s":0.038},
        "filter":{"type":"bandpass","low_cutoff":260,"high_cutoff":6200},
        "lfo":{"rate_hz":5.4,"pitch_cents":1.2,"amp_depth":0.0},
        "waveshaper":{"type":"softclip","drive":1.035},
        "declick":{"ms":4.0},
        "output_gain":0.62,
    }}

    a=synth_patch_note(76,0.65,sr,old,velocity=0.72)
    b=synth_patch_note(76,0.65,sr,new,velocity=0.72)
    c=synth_patch_note(76,0.65,sr,new,velocity=0.72)
    assert np.array_equal(b,c)

    old_click=onset_click_score(a,sr)
    new_click=onset_click_score(b,sr)
    old_hi=high_band_ratio(a,sr)
    new_hi=high_band_ratio(b,sr)
    new_flat=spectral_flatness(b)
    conc=harmonic_concentration(b,sr,midi_to_hz(76),harmonics=4,bandwidth_hz=40)

    assert new_click < old_click
    assert new_hi < 0.08
    assert new_flat < 0.05
    assert conc > 0.65

    print("test_whistle_timbre: OK")
    print({
        "old_click":round(old_click,5),
        "new_click":round(new_click,5),
        "old_high_ratio":round(old_hi,6),
        "new_high_ratio":round(new_hi,6),
        "new_flatness":round(new_flat,6),
        "new_harmonic_concentration":round(conc,4),
    })

if __name__=="__main__":
    run()


def test_regression():
    run()
