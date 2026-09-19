import json
from pathlib import Path
import numpy as np
from code_composer.instrument import synth_patch_note
from code_composer.instrument_analysis import spectral_centroid, stereo_width, compare_patches

def run():
    root=Path(__file__).resolve().parents[1]
    ir=json.loads((root/"tests/fixtures/instrument_ir.json").read_text(encoding="utf-8"))
    sr=22050

    lead=ir["instruments"]["lead"]
    pad=ir["instruments"]["pad"]
    bass=ir["instruments"]["bass"]

    a=synth_patch_note(69,1.0,sr,lead,velocity=0.7)
    b=synth_patch_note(69,1.0,sr,lead,velocity=0.7)
    assert np.array_equal(a,b)

    p=synth_patch_note(69,1.0,sr,pad,velocity=0.7)
    bs=synth_patch_note(45,1.0,sr,bass,velocity=0.7)

    diff=compare_patches(a,p)
    assert diff["mean_abs_delta"] > 0.01
    assert diff["correlation"] < 0.98

    assert stereo_width(p) > stereo_width(bs)
    assert spectral_centroid(a,sr) > 200
    assert spectral_centroid(bs,sr) < spectral_centroid(a,sr)

    print("test_instrument: OK")
    print({
        "lead_centroid": round(spectral_centroid(a,sr),2),
        "pad_width": round(stereo_width(p),4),
        "bass_width": round(stereo_width(bs),4),
        "lead_pad_correlation": round(diff["correlation"],4),
        "lead_pad_delta": round(diff["mean_abs_delta"],4),
    })

if __name__=="__main__":
    run()


def test_regression():
    run()
