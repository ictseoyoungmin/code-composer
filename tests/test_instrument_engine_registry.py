from pathlib import Path
import numpy as np

from code_composer.audio.engines import (
    EngineCapabilities,
    InstrumentEngine,
    engine_for_patch,
    engine_name_for_patch,
    register_engine,
    registered_engines,
)
from code_composer.audio.instrument import synth_patch_note
from code_composer.audio.generic_synth import render_generic_note
from code_composer.audio.piano import render_piano_note


ROOT = Path(__file__).resolve().parents[1]


def _generic_patch():
    return {
        "kind": "synth",
        "graph": {
            "oscillators": [{"waveform": "sine", "gain": .6}],
            "envelope": {"attack": .01, "decay": .08, "sustain": .7, "release": .12},
            "output_gain": .7,
        },
    }


def _piano_patch():
    return {
        "kind": "piano",
        "piano_graph": {
            "strings": {"max_partials": 12},
            "damper": {"release_s": .18, "pedal_release_s": 1.2},
            "soundboard": {},
        },
    }


def test_builtin_registry_has_family_boundaries():
    assert registered_engines() == ("bowed_string", "bowed_waveguide", "generic", "percussion", "piano", "plucked_bass")
    assert engine_name_for_patch(_generic_patch()) == "generic"
    assert engine_name_for_patch(_piano_patch()) == "piano"
    assert engine_name_for_patch({"kind": "bowed_string", "engine": "bowed_string", "bowed_string_graph": {}}) == "bowed_string"


def test_generic_compatibility_facade_is_sample_identical():
    p = _generic_patch()
    direct = render_generic_note(64, .4, 22050, p, velocity=.63)
    routed = synth_patch_note(64, .4, 22050, p, velocity=.63)
    assert np.array_equal(direct, routed)



def test_generic_short_note_has_endpoint_safety_without_authored_declick():
    p = {
        "kind": "synth",
        "graph": {
            "oscillators": [{"waveform": "saw", "gain": .8}],
            "envelope": {"attack": .18, "decay": .28, "sustain": .78, "release": .55},
            "filter": {"type": "bandpass", "low_cutoff": 320, "high_cutoff": 5800},
            "output_gain": .8,
        },
    }
    out = render_generic_note(62, .36, 24000, p, velocity=.7)
    assert np.max(np.abs(out[0])) < 1e-12
    assert np.max(np.abs(out[-1])) < 1e-12
    assert np.all(np.isfinite(out))


def test_piano_compatibility_facade_is_sample_identical():
    p = _piano_patch()
    direct = render_piano_note(60, .4, 22050, p, velocity=.63)
    routed = synth_patch_note(60, .4, 22050, p, velocity=.63)
    assert np.array_equal(direct, routed)


def test_render_pipeline_has_no_family_specific_piano_branch():
    text = (ROOT / "skills/code-composer/kit/src/code_composer/render.py").read_text()
    assert "piano_graph" not in text
    assert "apply_piano_soundboard" not in text
    assert "piano_tail_seconds" not in text
    assert "engine_for_patch" in text


def test_registry_accepts_additive_engine_without_renderer_change():
    class DummyEngine(InstrumentEngine):
        name = "test_dummy_engine"
        def render_note(self, midi, duration_s, sr, patch, *, velocity=1.0, performance=None):
            return np.full((8, 2), float(velocity), dtype=np.float64)
        def capabilities(self):
            return EngineCapabilities(name=self.name)
    register_engine(DummyEngine(), replace=True)
    p = {"kind": "test", "engine": "test_dummy_engine"}
    assert engine_for_patch(p).name == "test_dummy_engine"
    out = synth_patch_note(60, .1, 8000, p, velocity=.25)
    assert out.shape == (8, 2)
    assert np.all(out == .25)
