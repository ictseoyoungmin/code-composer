from copy import deepcopy

import pytest

from code_composer.audio.engines import (
    InstrumentEngineValidationError,
    validate_authoring_patch,
    validate_ir_patch,
)
from code_composer.phrase import PhraseConfig, compose_phrase


def _materials():
    return {"motifs": {"main": {
        "intervals": [0, 1, 2, 1],
        "rhythm": [1.5, 0.5, 1.0, 1.0],
    }}}


def _tonal():
    return {"root": "D", "scale": "natural_minor"}


def test_s32_neutral_phrase_gate_consumes_the_full_authored_rhythm_cell():
    out = compose_phrase(
        _materials(), _tonal(), 3201, "main",
        PhraseConfig(bars=2, beats_per_bar=4, density=1.0, gate=1.0),
        namespace="s32:neutral",
    )
    first = out["events"][0]
    assert first["start_beat"] == 0.0
    assert first["duration_beats"] == 1.5
    assert out["config"]["gate"] == 1.0


def test_s32_legacy_short_gate_remains_available_only_when_explicitly_authored():
    out = compose_phrase(
        _materials(), _tonal(), 3201, "main",
        PhraseConfig(bars=2, beats_per_bar=4, density=1.0, gate=0.82),
        namespace="s32:explicit-short",
    )
    assert out["events"][0]["duration_beats"] == pytest.approx(1.5 * 0.82)
    assert out["config"]["gate"] == 0.82


def test_s32_phrase_gate_rejects_out_of_contract_values():
    with pytest.raises(ValueError, match="PhraseConfig.gate"):
        PhraseConfig(gate=0.0)


def _safe_air_patch():
    return {"graph": {
        "oscillators": [
            {"waveform": "sine", "gain": 0.91},
            {"waveform": "triangle", "gain": 0.025, "octave": 1},
        ],
        "envelope": {"attack": 0.018, "decay": 0.09, "sustain": 0.72, "release": 0.12},
        "breath": {"gain": 0.008, "low_cutoff": 1700, "high_cutoff": 5600},
        "waveshaper": {"type": "softclip", "drive": 1.035},
        "output_gain": 0.62,
    }}


def _amber_static_patch():
    patch = deepcopy(_safe_air_patch())
    patch["graph"].update({
        "oscillators": [
            {"waveform": "saw", "gain": 0.38},
            {"waveform": "triangle", "gain": 0.42},
            {"waveform": "sine", "gain": 0.25, "octave": 1},
        ],
        "breath": {"gain": 0.04, "low_cutoff": 1600, "high_cutoff": 7200},
        "waveshaper": {"type": "softclip", "drive": 1.08},
        "output_gain": 1.4,
    })
    return patch


def test_s32_low_level_air_layer_remains_valid():
    patch = _safe_air_patch()
    validate_authoring_patch("lead", patch)
    validate_ir_patch("lead", patch)


def test_s32_fresh_worker_static_prone_graph_is_blocked_at_authoring_boundary():
    with pytest.raises(InstrumentEngineValidationError, match="broadband-static risk"):
        validate_authoring_patch("lead", _amber_static_patch())


def test_s32_pre_resolved_ir_cannot_bypass_static_guard():
    with pytest.raises(InstrumentEngineValidationError, match="broadband-static risk"):
        validate_ir_patch("lead", _amber_static_patch())
