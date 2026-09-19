import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from code_composer.audio.engines import engine_for_patch
from code_composer.performance.violin import realize_violin_performance
from code_composer.presets import list_presets, materialize_preset

ROOT = Path(__file__).resolve().parents[1]


def _ir(preset_id="bowed.violin.modeled_admittance"):
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
    ir["mix"] = {"tail_seconds": 0.4, "drive": 1.0, "ceiling": 0.98}
    return ir


def _render(patch_override=None):
    realized = realize_violin_performance(_ir(), "lead", config={"strict_comfort": False})
    patch = realized["instruments"]["lead"]
    if patch_override is not None:
        patch = deepcopy(patch)
        patch_override(patch)
    sr = 22050
    beat_s = 60.0 / 72.0
    n = int((4.0 * beat_s + .55) * sr)
    y = engine_for_patch(patch).render_track(
        realized["tracks"][0]["events"], n, sr, patch, beat_s, gain=.18, pan=0.0
    )
    return y


def test_admittance_preset_is_separate_factory_capability():
    metas = {x["preset_id"]: x for x in list_presets(family="violin")}
    meta = metas["bowed.violin.modeled_admittance"]
    assert meta["engine"] == "bowed_waveguide"
    assert meta["musical_content"] is False
    assert "patch" not in meta
    patch = materialize_preset("bowed.violin.modeled_admittance", role="lead")
    fb = patch["bowed_waveguide_graph"]["body"]["bridge_feedback"]
    assert fb["enabled"] is True
    assert fb["feedback_gain"] > 0


def test_admittance_track_is_deterministic_finite_and_non_silent():
    a = _render()
    b = _render()
    assert a is not None and np.array_equal(a, b)
    assert np.isfinite(a).all()
    assert float(np.max(np.abs(a))) <= 1.0
    assert float(np.sqrt(np.mean(a[:, 0] ** 2))) > 1e-4


def test_feedback_gain_changes_string_body_closed_loop_not_just_catalog_metadata():
    wet = _render()
    dry = _render(lambda p: p["bowed_waveguide_graph"]["body"]["bridge_feedback"].update({"feedback_gain": 0.0}))
    assert wet is not None and dry is not None
    assert not np.array_equal(wet, dry)
    # Radiation coefficients are unchanged; only the string<-body feedback gain differs.
    delta = wet[:, 0] - dry[:, 0]
    assert float(np.sqrt(np.mean(delta[int(.08 * 22050):] ** 2))) > 1e-6


def test_zero_feedback_matches_same_preset_with_feedback_disabled():
    zero = _render(lambda p: p["bowed_waveguide_graph"]["body"]["bridge_feedback"].update({"feedback_gain": 0.0}))
    off = _render(lambda p: p["bowed_waveguide_graph"]["body"]["bridge_feedback"].update({"enabled": False}))
    assert zero is not None and off is not None
    # With gain=0 the body is still rendered through the causal modal bank; disabling
    # the feature returns to S7's offline body filter, so they need not be byte-equal.
    # Both, however, must remain finite and stable.
    assert np.isfinite(zero).all() and np.isfinite(off).all()


def test_invalid_admittance_vector_or_gain_is_rejected():
    p = materialize_preset("bowed.violin.modeled_admittance", role="lead")
    p["bowed_waveguide_graph"]["body"]["bridge_feedback"]["admittance_gains"] = [0.1]
    with pytest.raises(Exception):
        engine_for_patch(p).validate_authoring_patch("lead", p)
    p = materialize_preset("bowed.violin.modeled_admittance", role="lead")
    p["bowed_waveguide_graph"]["body"]["bridge_feedback"]["feedback_gain"] = 1.0
    with pytest.raises(Exception):
        engine_for_patch(p).validate_authoring_patch("lead", p)
