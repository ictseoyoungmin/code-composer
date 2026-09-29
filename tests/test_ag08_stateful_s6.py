import math

import numpy as np
import pytest

from code_composer.audio.acoustic_guitar.body import radiate_acoustic_guitar_body
from code_composer.audio.acoustic_guitar.stability import (
    body_pole_certificate,
    passive_transition_certificate,
)
from code_composer.audio.acoustic_guitar.stateful import (
    _shared_body_loading_curve,
    _string_contact_loading_curve,
    render_stateful_acoustic_guitar_track,
)
from code_composer.audio.acoustic_guitar.string import render_steel_string_bridge_drive
from code_composer.presets import materialize_preset


S5 = "acoustic_guitar.steel_stateful_performance"
SR = 24000


def _rms(x):
    x = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(x * x))) if x.size else 0.0


def test_s6_internal_passive_certificate_passes_for_s5_preset():
    patch = materialize_preset(S5)
    cert = passive_transition_certificate(SR, patch)

    assert cert["passive_internal_state_transforms"] is True
    assert cert["body"]["all_strictly_inside_unit_circle"] is True
    assert 0.0 < cert["body"]["max_pole_radius"] < 1.0

    shared = cert["shared_body_loading"]
    assert shared["max_multiplier"] <= 1.0 + 1e-12
    assert 0.0 < shared["min_multiplier"] <= 1.0
    assert shared["nonincreasing"] is True

    contact = cert["string_contact_loading"]
    assert contact["max_multiplier"] <= 1.0 + 1e-12
    assert 0.0 < contact["min_multiplier"] <= 1.0
    assert contact["nonincreasing"] is True

    transfer = cert["sympathetic_bridge_energy"]
    assert transfer["configured_budget"] == pytest.approx(0.036)
    assert transfer["source_keep_squared_plus_budget"] == pytest.approx(1.0)
    assert cert["same_string"]["all_decay_scales_positive"] is True


def test_s6_no_input_stateful_renderer_is_exact_silence():
    patch = materialize_preset(S5)
    out = render_stateful_acoustic_guitar_track(
        [],
        12 * SR,
        SR,
        patch,
        60.0 / 96.0,
    )
    assert out is not None
    assert out.shape == (12 * SR, 2)
    assert np.array_equal(out, np.zeros_like(out))


def test_s6_body_poles_are_strictly_stable_and_impulse_energy_is_finite():
    patch = materialize_preset(S5)
    graph = patch["acoustic_guitar_graph"]
    cert = body_pole_certificate(SR, graph)
    assert cert["all_strictly_inside_unit_circle"] is True

    bridge = np.zeros(12 * SR, dtype=np.float64)
    bridge[0] = 1.0
    body = radiate_acoustic_guitar_body(bridge, SR, graph)

    assert np.all(np.isfinite(body))
    energy = float(np.sum(body * body))
    assert 0.0 < energy < math.inf
    early = _rms(body[: int(0.25 * SR)])
    late = _rms(body[-SR:])
    assert early > 0.0
    assert late < early * 1e-4


def test_s6_string_free_decay_has_finite_energy_and_loses_late_energy():
    patch = materialize_preset(S5)
    graph = patch["acoustic_guitar_graph"]

    bridge = render_steel_string_bridge_drive(
        40,
        12 * SR,
        SR,
        graph,
        velocity=0.72,
    )
    assert np.all(np.isfinite(bridge))
    energy = float(np.sum(bridge * bridge))
    assert 0.0 < energy < math.inf

    first = _rms(bridge[: 2 * SR])
    middle = _rms(bridge[4 * SR : 6 * SR])
    late = _rms(bridge[10 * SR : 12 * SR])
    assert first > middle > late >= 0.0
    assert late < first * 0.08


@pytest.mark.parametrize("memory", [0.0, 0.32, 0.46, 0.52, 0.82, 0.98])
@pytest.mark.parametrize("residual", [0.0, 0.02, 0.08, 0.20])
def test_s6_loading_curves_cannot_amplify_existing_state(memory, residual):
    shared = _shared_body_loading_curve(memory, residual, SR, 4096)
    assert shared[0] == pytest.approx(1.0)
    assert np.max(shared) <= 1.0 + 1e-12
    assert np.min(shared) > 0.0
    assert np.all(np.diff(shared) <= 1e-12)

    for action in ("muted_strum", "dead_strum", "string_slap"):
        curve = _string_contact_loading_curve(
            memory, action, 1.0, residual, SR, 4096
        )
        assert curve[0] == pytest.approx(1.0)
        assert np.max(curve) <= 1.0 + 1e-12
        assert np.min(curve) > 0.0
        assert np.all(np.diff(curve) <= 1e-12)
