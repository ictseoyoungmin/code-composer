from copy import deepcopy
from pathlib import Path
import json

import numpy as np
import pytest
from scipy.signal import butter, sosfilt

from code_composer.audio import piano
from code_composer.audio.piano_design import resolve_piano_design
from code_composer.execution import preview
from code_composer.presets import materialize_preset


def _patch(name="natural"):
    p = resolve_piano_design(materialize_preset(f"piano.concert_grand_{name}", role="piano"))
    p["piano_graph"]["output_gain"] = .19  # avoid the legacy per-note peak cap
    return p


def _rms(x, sr, lo, hi):
    seg = x[int(sr*lo):int(sr*hi)]
    return np.sqrt(np.mean(seg**2))


def _relative_band(y, sr, band, lo, hi):
    z = sosfilt(butter(5, band, fs=sr, btype="bandpass", output="sos"), y, axis=0)
    return 20*np.log10(_rms(z, sr, lo, hi)/_rms(y, sr, 0, .05))


@pytest.mark.parametrize("sr", [24000, 48000])
@pytest.mark.parametrize("pedal", [False, True])
def test_balanced_reduces_e5_late_ring_without_losing_the_attack_or_body(sr, pedal):
    perf = {"pedal": pedal, "pedal_controlled": True, "piano_strike_seed": 7035}
    a,b = [piano.render_piano_note(76, .7, sr, _patch(name), .86, perf)
           for name in ("natural","balanced")]
    assert a.shape == b.shape and np.isfinite(b).all()
    attack = 20*np.log10(_rms(b,sr,0,.05)/_rms(a,sr,0,.05))
    assert abs(attack) < .35
    f0 = (550,800)
    body = _relative_band(b,sr,f0,.14,.28)-_relative_band(a,sr,f0,.14,.28)
    assert abs(body) < .5
    band = (2100,6500)
    assert _relative_band(b,sr,band,.35,.55) < _relative_band(a,sr,band,.35,.55) - 9
    assert _relative_band(b,sr,band,0,.05) > _relative_band(a,sr,band,0,.05) - 1.


@pytest.mark.parametrize("midi", [48, 60, 76, 84])
def test_zero_is_inert_and_lower_notes_are_not_revoiced(midi):
    a,b = _patch(),_patch("balanced")
    if midi>60:
        b["piano_graph"]["strings"]["treble_radiation_rate"]=0.
    x,y = [piano.render_piano_note(midi,.35,24000,patch,.62) for patch in (a,b)]
    np.testing.assert_array_equal(x,y)


def test_reinforcement_uses_struck_frequency_and_cannot_outlast_source():
    sr = 24000
    t = np.arange(sr)/sr
    base = 660.
    stiffness, rate = .0002, 10.
    clock = t+.055*np.expm1(-t/.055)
    cfg = {"gain": .1, "ratios": [4.], "weights": [1.], "decay_s": 4.}
    y = piano._resonance_layer(base, sr, sr, 76, 1., True, cfg,
                               treble_source=(stiffness, 3., .5, rate, clock))
    freq = 4*base*np.sqrt(1+16*stiffness)
    expected = .175*np.sin(2*np.pi*freq*t+.31*76)*np.exp(
        -t/1.5-piano._upper_partial_loss(rate,freq)*clock
    )
    np.testing.assert_allclose(y,expected,atol=1e-14,rtol=1e-12)


def test_legacy_release_does_not_discard_per_string_decay():
    a = _patch()
    b = deepcopy(a)
    b["piano_graph"]["strings"]["unison_decoherence"]["decay_spread"] = .20
    perf={"pedal": True, "pedal_controlled": False}
    x,y = [piano.render_piano_note(84,.4,24000,p,.65,perf) for p in (a,b)]
    assert np.max(np.abs(x[:9600]-y[:9600])) > 1e-4
    assert np.max(np.abs(x[9600:]-y[9600:])) > 1e-4


def test_new_control_schema_matches_runtime_and_cache_is_invalidated():
    from code_composer.audio.piano_design import ACOUSTIC_CONTROL_SPECS
    root = Path(__file__).resolve().parents[1] / "skills/code-composer/kit"
    for path in ("schemas/piano_design.schema.json","src/code_composer/reference/schemas/piano_design.schema.json"):
        schema = json.loads((root/path).read_text())
        acoustic = schema["oneOf"][0]
        spec = acoustic["properties"]["controls"]["properties"]["treble_radiation_rate"]
        assert (spec["minimum"],spec["maximum"]) == ACOUSTIC_CONTROL_SPECS["treble_radiation_rate"][1:3]
    assert preview.STEM_CACHE_RENDERER_EPOCH != "cr05-renderer-epoch-1"
