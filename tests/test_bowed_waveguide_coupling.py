import json
from pathlib import Path

import numpy as np

from code_composer.audio.engines import engine_for_patch
from code_composer.performance.violin import realize_violin_performance
from code_composer.presets import list_presets, materialize_preset

ROOT = Path(__file__).resolve().parents[1]


def _ir(preset_id="bowed.violin.modeled_coupled"):
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


def test_coupled_preset_is_separate_sound_capability():
    metas = {x["preset_id"]: x for x in list_presets(family="violin")}
    meta = metas["bowed.violin.modeled_coupled"]
    assert meta["musical_content"] is False
    assert meta["engine"] == "bowed_waveguide"
    patch = materialize_preset("bowed.violin.modeled_coupled", role="lead")
    crossing = patch["bowed_waveguide_graph"]["continuous"]["string_crossing"]
    assert crossing["enabled"] is True
    assert crossing["adjacent_only"] is True


def test_planner_produces_adjacent_g_d_a_crossings_for_protocol_phrase():
    realized = realize_violin_performance(_ir(), "lead", config={"strict_comfort": False})
    strings = [e["performance"]["violin_realization"]["left_hand"]["string"] for e in realized["tracks"][0]["events"]]
    assert strings == ["G", "D", "A", "A"]


def test_coupled_track_is_deterministic_and_differs_from_s6_reset_on_crossing():
    coupled_ir = realize_violin_performance(_ir(), "lead", config={"strict_comfort": False})
    reset_ir = realize_violin_performance(_ir("bowed.violin.modeled_continuous"), "lead", config={"strict_comfort": False})
    sr = 22050
    beat_s = 60.0 / 72.0
    n = int((4.0 * beat_s + .5) * sr)
    ce = engine_for_patch(coupled_ir["instruments"]["lead"])
    se = engine_for_patch(reset_ir["instruments"]["lead"])
    ca = ce.render_track(coupled_ir["tracks"][0]["events"], n, sr, coupled_ir["instruments"]["lead"], beat_s, gain=.18, pan=0.0)
    cb = ce.render_track(coupled_ir["tracks"][0]["events"], n, sr, coupled_ir["instruments"]["lead"], beat_s, gain=.18, pan=0.0)
    sa = se.render_track(reset_ir["tracks"][0]["events"], n, sr, reset_ir["instruments"]["lead"], beat_s, gain=.18, pan=0.0)
    assert ca is not None and sa is not None and np.array_equal(ca, cb)
    assert not np.array_equal(ca, sa)
    # Crossing boundaries retain finite energy without a digital zero/reset seam.
    for beat in (1.0, 2.0):
        boundary = int(beat * beat_s * sr)
        win = max(8, int(.010 * sr))
        x = ca[boundary-win:boundary+win, 0]
        assert float(np.sqrt(np.mean(x*x))) > 1e-4


def test_coupled_preset_extends_engine_tail_for_residual_string_decay():
    p = materialize_preset("bowed.violin.modeled_coupled", role="lead")
    base = materialize_preset("bowed.violin.modeled_continuous", role="lead")
    assert engine_for_patch(p).tail_seconds(p) >= .18
    assert engine_for_patch(base).tail_seconds(base) == base["bowed_waveguide_graph"]["envelope"]["release_s"]


def test_invalid_crossing_parameters_are_rejected():
    p = materialize_preset("bowed.violin.modeled_coupled", role="lead")
    p["bowed_waveguide_graph"]["continuous"]["string_crossing"]["residual_bridge_mix"] = 1.5
    try:
        engine_for_patch(p).validate_authoring_patch("lead", p)
    except Exception:
        return
    raise AssertionError("invalid crossing coupling must be rejected")


def test_residual_bridge_mix_is_an_audible_causal_control():
    realized = realize_violin_performance(_ir(), "lead", config={"strict_comfort": False})
    wet_patch = realized["instruments"]["lead"]
    dry_patch = materialize_preset(
        "bowed.violin.modeled_coupled",
        role="lead",
        patch_overrides={"bowed_waveguide_graph": {"continuous": {"string_crossing": {"residual_bridge_mix": 0.0}}}},
    )
    sr = 22050
    beat_s = 60.0 / 72.0
    n = int((4.0 * beat_s + .5) * sr)
    events = realized["tracks"][0]["events"]
    wet = engine_for_patch(wet_patch).render_track(events, n, sr, wet_patch, beat_s, gain=.18, pan=0.0)
    dry = engine_for_patch(dry_patch).render_track(events, n, sr, dry_patch, beat_s, gain=.18, pan=0.0)
    assert wet is not None and dry is not None and not np.array_equal(wet, dry)
    boundary = int(1.0 * beat_s * sr)
    region = wet[boundary:boundary+int(.12*sr), 0] - dry[boundary:boundary+int(.12*sr), 0]
    assert float(np.sqrt(np.mean(region*region))) > 1e-7
