import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from code_composer.audio.engines import engine_for_patch
from code_composer.performance.violin import realize_violin_performance
from code_composer.presets import list_presets, materialize_preset

ROOT = Path(__file__).resolve().parents[1]


def _ir(preset_id="bowed.violin.modeled_expression"):
    ir = json.loads((ROOT / "tests/fixtures/high_level_ir.json").read_text())
    ir["transport"]["bpm"] = 72
    ir["instruments"]["lead"] = materialize_preset(preset_id, role="lead")
    ir["tracks"] = [{
        "id": "lead",
        "instrument": "lead",
        "gain": 0.18,
        "pan": 0.0,
        "source": {"type": "resolved"},
        "events": [
            {"start_beat": 0.0, "duration_beats": 1.0, "midi": 55, "velocity": .61, "performance": {"articulation": "legato"}},
            {"start_beat": 1.0, "duration_beats": 1.0, "midi": 62, "velocity": .63, "performance": {"articulation": "legato"}},
            {"start_beat": 2.0, "duration_beats": 1.0, "midi": 69, "velocity": .62, "performance": {"articulation": "legato"}},
            {"start_beat": 3.0, "duration_beats": 1.0, "midi": 76, "velocity": .60, "performance": {"articulation": "neutral"}},
        ],
    }]
    return ir


def _realized(preset_id="bowed.violin.modeled_expression"):
    return realize_violin_performance(_ir(preset_id), "lead", config={"strict_comfort": False})


def _track_render(realized, patch=None):
    patch = patch or realized["instruments"]["lead"]
    sr = 22050
    beat_s = 60.0 / 72.0
    n = int((4.0 * beat_s + .5) * sr)
    return engine_for_patch(patch).render_track(
        realized["tracks"][0]["events"], n, sr, patch, beat_s, gain=.18, pan=0.0
    )


def test_expression_preset_is_separate_opt_in_factory_capability():
    metas = {x["preset_id"]: x for x in list_presets(family="violin")}
    meta = metas["bowed.violin.modeled_expression"]
    assert meta["engine"] == "bowed_waveguide"
    assert meta["musical_content"] is False
    assert "patch" not in meta
    patch = materialize_preset("bowed.violin.modeled_expression", role="lead")
    cfg = patch["bowed_waveguide_graph"]["expression_hardening"]
    assert cfg["enabled"] is True
    assert 0 < cfg["pressure_drift"] < .12
    assert 0 < cfg["vibrato_excitation_coupling"] < .15


def test_expression_track_is_deterministic_finite_and_changes_s9_timbre_path():
    realized = _realized()
    a = _track_render(realized)
    b = _track_render(realized)
    assert a is not None and np.array_equal(a, b)
    assert np.isfinite(a).all()
    assert float(np.max(np.abs(a))) <= 1.0

    baseline = _track_render(_realized("bowed.violin.modeled_admittance"))
    assert baseline is not None and not np.array_equal(a, baseline)
    corr = float(np.corrcoef(a[:, 0], baseline[:, 0])[0, 1])
    diff_rms = float(np.sqrt(np.mean((a[:, 0] - baseline[:, 0]) ** 2)))
    assert corr < .98
    assert diff_rms > 1e-4


def test_disabling_s10_hardening_is_byte_identical_to_s9_admittance_track():
    expr = _realized()
    off = deepcopy(expr["instruments"]["lead"])
    off["bowed_waveguide_graph"]["expression_hardening"]["enabled"] = False
    baseline = _track_render(_realized("bowed.violin.modeled_admittance"))
    disabled = _track_render(expr, off)
    assert baseline is not None and disabled is not None
    assert np.array_equal(baseline, disabled)


def test_disabling_s10_hardening_is_byte_identical_to_s9_admittance_note():
    base = materialize_preset("bowed.violin.modeled_admittance", role="lead")
    expr = materialize_preset("bowed.violin.modeled_expression", role="lead")
    off = deepcopy(expr)
    off["bowed_waveguide_graph"]["expression_hardening"]["enabled"] = False
    perf = {
        "articulation": "tenuto",
        "instrument_expression": {
            "bow_pressure": .63,
            "bow_speed": .57,
            "vibrato_depth_cents": 18,
        },
    }
    a = engine_for_patch(base).render_note(69, .8, 22050, base, velocity=.72, performance=perf)
    b = engine_for_patch(off).render_note(69, .8, 22050, off, velocity=.72, performance=perf)
    assert np.array_equal(a, b)


def test_attack_and_vibrato_hardening_controls_are_audible_independently():
    realized = _realized()
    full = _track_render(realized)

    no_transient = deepcopy(realized["instruments"]["lead"])
    cfg = no_transient["bowed_waveguide_graph"]["expression_hardening"]
    cfg.update({
        "attack_time_variation": 0.0,
        "attack_pressure_overshoot": 0.0,
        "attack_noise_boost": 0.0,
        "bow_change_pressure_dip": 0.0,
        "bow_change_noise_boost": 0.0,
    })
    dry_transient = _track_render(realized, no_transient)
    assert not np.array_equal(full, dry_transient)
    attack_region = int(.12 * 22050)
    assert float(np.sqrt(np.mean((full[:attack_region, 0] - dry_transient[:attack_region, 0]) ** 2))) > 1e-7

    no_vib_coupling = deepcopy(realized["instruments"]["lead"])
    cfg = no_vib_coupling["bowed_waveguide_graph"]["expression_hardening"]
    cfg["vibrato_excitation_coupling"] = 0.0
    cfg["vibrato_pressure_coupling"] = 0.0
    no_vib_coupling["bowed_waveguide_graph"]["vibrato"]["amplitude_coupling"] = 0.0
    dry_vibrato = _track_render(realized, no_vib_coupling)
    assert not np.array_equal(full, dry_vibrato)


def test_invalid_expression_hardening_configuration_is_rejected():
    patch = materialize_preset("bowed.violin.modeled_expression", role="lead")
    patch["bowed_waveguide_graph"]["expression_hardening"]["pressure_drift"] = .5
    with pytest.raises(Exception):
        engine_for_patch(patch).validate_authoring_patch("lead", patch)
