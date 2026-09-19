import numpy as np
from code_composer.percussion import render_drum_event
from code_composer.drum_analysis import analyze_drum_hit


def _hit(kind, duration, seed=17):
    return render_drum_event(kind,duration,44100,0.82,seed=seed)


def test_drum_hits_are_deterministic_and_role_separated():
    kick=_hit("kick",0.35)
    snare=_hit("snare",0.24)
    hat=_hit("hat",0.09)
    assert np.array_equal(kick,_hit("kick",0.35))
    assert np.array_equal(snare,_hit("snare",0.24))
    assert np.array_equal(hat,_hit("hat",0.09))

    k=analyze_drum_hit(kick,44100)
    s=analyze_drum_hit(snare,44100)
    h=analyze_drum_hit(hat,44100)

    assert k["low_ratio_20_120"] > 0.65
    assert k["centroid_hz"] < 350
    assert s["body_ratio_120_500"] > 0.05
    assert s["presence_ratio_1k_5k"] > 0.08
    assert h["air_ratio_7k_16k"] > 0.35
    assert h["centroid_hz"] > s["centroid_hz"] > k["centroid_hz"]


def test_drum_graph_patch_changes_kick_tone():
    base=_hit("kick",0.35)
    patch={"drum_graph":{"kick":{"pitch_end_hz":58.0,"click_gain":0.02,"body_decay_s":0.09}}}
    alt=render_drum_event("kick",0.35,44100,0.82,seed=17,patch=patch)
    assert not np.array_equal(base,alt)
    assert np.mean(np.abs(base-alt)) > 1e-4
