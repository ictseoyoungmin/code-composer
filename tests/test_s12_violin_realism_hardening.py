import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from code_composer.audio.engines import engine_for_patch
from code_composer.performance.violin import realize_violin_performance
from code_composer.presets import list_presets, materialize_preset

ROOT = Path(__file__).resolve().parents[1]


def _ir(events, preset_id="bowed.violin.modeled_realistic", *, disable_realism=False):
    ir = json.loads((ROOT / "tests/fixtures/high_level_ir.json").read_text())
    ir["transport"]["bpm"] = 72
    overrides = None
    if disable_realism:
        overrides = {"bowed_waveguide_graph": {"realism_hardening": {"enabled": False}}}
    ir["instruments"]["lead"] = materialize_preset(
        preset_id, role="lead", patch_overrides=overrides
    )
    ir["tracks"] = [{
        "id": "lead", "instrument": "lead", "gain": .18, "pan": 0.0,
        "source": {"type": "resolved"}, "events": deepcopy(events),
    }]
    ir["mix"] = {"tail_seconds": .4, "drive": 1.0, "ceiling": .98}
    return ir


def _render(realized, *, seconds=3.0, sr=8000):
    patch = realized["instruments"]["lead"]
    beat_s = 60.0 / float(realized["transport"]["bpm"])
    n = int(seconds * sr)
    return engine_for_patch(patch).render_track(
        realized["tracks"][0]["events"], n, sr, patch, beat_s, gain=.18, pan=0.0
    )


def test_s12_realistic_preset_is_separate_opt_in_surface():
    metas = {x["preset_id"]: x for x in list_presets(family="violin")}
    assert "bowed.violin.modeled_realistic" in metas
    p = materialize_preset("bowed.violin.modeled_realistic", role="lead")
    cfg = p["bowed_waveguide_graph"]["realism_hardening"]
    assert cfg["enabled"] is True
    assert 0 <= cfg["open_string_vibrato_scale"] < 1
    assert cfg["stopped_string_reflection_scale"] < 1


def test_disabling_s12_realism_is_byte_identical_to_s10_expression_track():
    events = [
        {"start_beat": 0.0, "duration_beats": .92, "midi": 71, "velocity": .62, "performance": {"articulation": "legato"}},
        {"start_beat": 1.0, "duration_beats": .92, "midi": 74, "velocity": .66, "performance": {"articulation": "legato"}},
        {"start_beat": 2.0, "duration_beats": .92, "midi": 78, "velocity": .68, "performance": {"articulation": "neutral"}},
    ]
    control = realize_violin_performance(_ir(events, "bowed.violin.modeled_expression"), "lead", config={"strict_comfort": False})
    disabled = realize_violin_performance(_ir(events, disable_realism=True), "lead", config={"strict_comfort": False})
    ce = control["tracks"][0]["events"]
    de = disabled["tracks"][0]["events"]
    assert ce == de
    a = _render(control, seconds=3.1)
    b = _render(disabled, seconds=3.1)
    assert a is not None and b is not None and np.array_equal(a, b)


def test_realistic_preset_marks_long_gap_bow_retake_and_reuses_direction():
    events = [
        {"start_beat": 0.0, "duration_beats": .35, "midi": 71, "velocity": .62, "performance": {"articulation": "neutral"}},
        {"start_beat": 1.0, "duration_beats": .35, "midi": 72, "velocity": .63, "performance": {"articulation": "neutral"}},
        {"start_beat": 2.0, "duration_beats": .35, "midi": 74, "velocity": .64, "performance": {"articulation": "neutral"}},
    ]
    realistic = realize_violin_performance(_ir(events), "lead", config={"strict_comfort": False})
    bows = [e["performance"]["violin_realization"]["bow"] for e in realistic["tracks"][0]["events"]]
    assert [b["direction"] for b in bows] == ["down", "down", "down"]
    assert [b["retake"] for b in bows] == [False, True, True]
    assert bows[1]["preceding_gap_beats"] > .18

    legacy = realize_violin_performance(_ir(events, "bowed.violin.modeled_expression"), "lead", config={"strict_comfort": False})
    legacy_bows = [e["performance"]["violin_realization"]["bow"] for e in legacy["tracks"][0]["events"]]
    assert [b["direction"] for b in legacy_bows] == ["down", "up", "down"]
    assert all("retake" not in b for b in legacy_bows)


def test_open_string_vibrato_is_suppressed_only_in_s12_realism_path():
    events = [{
        "start_beat": 0.0, "duration_beats": 1.8, "midi": 69, "velocity": .68,
        "performance": {"articulation": "tenuto", "instrument_expression": {"vibrato_depth_cents": 34.0, "vibrato_onset_s": .02}},
    }]
    wet = realize_violin_performance(_ir(events), "lead", config={"strict_comfort": False})
    dry = realize_violin_performance(_ir(events, disable_realism=True), "lead", config={"strict_comfort": False})
    assert wet["tracks"][0]["events"][0]["performance"]["violin_realization"]["left_hand"]["finger"] == 0
    a = _render(wet, seconds=2.0)
    b = _render(dry, seconds=2.0)
    assert a is not None and b is not None and not np.array_equal(a, b)
    diff = a[:, 0] - b[:, 0]
    assert float(np.sqrt(np.mean(diff * diff))) > 1e-5


def test_position_shift_metadata_creates_finite_glide_and_contact_transient():
    events = [
        {"start_beat": 0.0, "duration_beats": .92, "midi": 71, "velocity": .64, "performance": {"articulation": "legato"}},
        {"start_beat": 1.0, "duration_beats": .92, "midi": 74, "velocity": .66, "performance": {"articulation": "legato"}},
    ]
    wet = realize_violin_performance(_ir(events), "lead", config={"strict_comfort": False})
    dry = realize_violin_performance(_ir(events, disable_realism=True), "lead", config={"strict_comfort": False})
    # Force an explicit same-string three-position shift as renderer protocol evidence.
    for r in (wet, dry):
        second = r["tracks"][0]["events"][1]["performance"]["violin_realization"]
        assert second["left_hand"]["string"] == "A"
        second["left_hand"]["position"] = 4
        second["transition"]["position_shift"] = 3
        second["transition"]["string_crossing"] = 0
    a = _render(wet, seconds=2.2)
    b = _render(dry, seconds=2.2)
    assert a is not None and b is not None and not np.array_equal(a, b)
    boundary = int((60.0 / 72.0) * 8000)
    region = a[boundary:boundary + int(.06 * 8000), 0] - b[boundary:boundary + int(.06 * 8000), 0]
    assert float(np.sqrt(np.mean(region * region))) > 1e-6


def test_stopped_string_crossing_and_finger_damping_change_causal_render():
    events = [
        {"start_beat": 0.0, "duration_beats": .95, "midi": 71, "velocity": .66, "performance": {"articulation": "legato"}},
        {"start_beat": 1.0, "duration_beats": .95, "midi": 78, "velocity": .68, "performance": {"articulation": "legato"}},
    ]
    wet = realize_violin_performance(_ir(events), "lead", config={"strict_comfort": False})
    dry = realize_violin_performance(_ir(events, disable_realism=True), "lead", config={"strict_comfort": False})
    ev = wet["tracks"][0]["events"]
    assert [x["performance"]["violin_realization"]["left_hand"]["string"] for x in ev] == ["A", "E"]
    assert all(x["performance"]["violin_realization"]["left_hand"]["finger"] != 0 for x in ev)
    a = _render(wet, seconds=2.2)
    b = _render(dry, seconds=2.2)
    assert a is not None and b is not None and np.isfinite(a).all() and np.isfinite(b).all()
    boundary = int((60.0 / 72.0) * 8000)
    region = a[boundary - 100:boundary + 500, 0] - b[boundary - 100:boundary + 500, 0]
    assert float(np.sqrt(np.mean(region * region))) > 1e-6


def test_invalid_s12_realism_parameters_are_rejected():
    p = materialize_preset("bowed.violin.modeled_realistic", role="lead")
    p["bowed_waveguide_graph"]["realism_hardening"]["open_string_vibrato_scale"] = 1.5
    with pytest.raises(Exception):
        engine_for_patch(p).validate_authoring_patch("lead", p)
