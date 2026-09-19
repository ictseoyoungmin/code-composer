import json
from pathlib import Path

import numpy as np

from code_composer.audio.engines import engine_for_patch
from code_composer.performance.violin import realize_violin_performance
from code_composer.presets import materialize_preset, list_presets
from code_composer.render import render

ROOT = Path(__file__).resolve().parents[1]


def _ir():
    ir = json.loads((ROOT / "tests/fixtures/high_level_ir.json").read_text())
    ir["transport"]["bpm"] = 80
    ir["instruments"]["lead"] = materialize_preset("bowed.violin.modeled_continuous", role="lead")
    ir["tracks"] = [{
        "id": "lead",
        "instrument": "lead",
        "gain": 0.18,
        "pan": 0.0,
        "source": {"type": "resolved"},
        "events": [
            {"start_beat": 0.0, "duration_beats": 1.0, "midi": 62, "velocity": .62, "performance": {"articulation": "legato"}},
            {"start_beat": 1.0, "duration_beats": 1.0, "midi": 64, "velocity": .64, "performance": {"articulation": "legato"}},
            {"start_beat": 2.0, "duration_beats": 1.0, "midi": 66, "velocity": .63, "performance": {"articulation": "neutral"}},
            {"start_beat": 3.0, "duration_beats": 1.0, "midi": 67, "velocity": .61, "performance": {"articulation": "legato"}},
        ],
    }]
    ir["mix"] = {"tail_seconds": 0.35, "drive": 1.0, "ceiling": 0.98}
    return ir


def test_continuous_preset_is_factory_sound_capability_only():
    metas = {x["preset_id"]: x for x in list_presets(family="violin")}
    meta = metas["bowed.violin.modeled_continuous"]
    assert meta["engine"] == "bowed_waveguide"
    assert meta["musical_content"] is False
    patch = materialize_preset("bowed.violin.modeled_continuous", role="lead")
    assert patch["bowed_waveguide_graph"]["continuous"]["enabled"] is True


def test_violin_realizer_accepts_modeled_waveguide_and_preserves_bow_plan():
    out = realize_violin_performance(_ir(), "lead", config={"strict_comfort": False})
    lead = out["tracks"][0]
    ids = [e["performance"]["violin_realization"]["bow"]["group_id"] for e in lead["events"]]
    directions = [e["performance"]["violin_realization"]["bow"]["direction"] for e in lead["events"]]
    assert ids[0] == ids[1]
    assert ids[2] != ids[1]
    assert directions[0] == directions[1] == "down"
    assert directions[2] == "up"


def test_stateful_track_renderer_is_deterministic_and_differs_from_note_reset(tmp_path):
    realized = realize_violin_performance(_ir(), "lead", config={"strict_comfort": False})
    patch = realized["instruments"]["lead"]
    events = realized["tracks"][0]["events"]
    engine = engine_for_patch(patch)
    sr = 22050
    beat_s = 60.0 / realized["transport"]["bpm"]
    n = int((4.5 * beat_s + .4) * sr)
    a = engine.render_track(events, n, sr, patch, beat_s, gain=.18, pan=0.0)
    b = engine.render_track(events, n, sr, patch, beat_s, gain=.18, pan=0.0)
    assert a is not None and np.array_equal(a, b)
    boundary = int(1.0 * beat_s * sr)
    window = int(.018 * sr)
    # Same-bow legato should retain non-trivial energy through the note boundary.
    around = a[boundary-window:boundary+window, 0]
    assert float(np.sqrt(np.mean(around * around))) > 1e-4

    reset_patch = materialize_preset("bowed.violin.modeled_open", role="lead")
    reset = np.zeros_like(a)
    for ev in events:
        start = int(ev["start_beat"] * beat_s * sr)
        y = engine_for_patch(reset_patch).render_note(
            ev["midi"], ev["duration_beats"] * beat_s, sr, reset_patch,
            velocity=float(ev.get("velocity", .8)) * .18,
            performance=ev.get("performance"),
        )
        end = min(len(reset), start + len(y))
        reset[start:end] += y[:end-start]
    assert not np.array_equal(a, reset)


def test_track_renderer_falls_back_for_double_stop():
    ir = _ir()
    ir["tracks"][0]["events"] = [
        {"start_beat": 0.0, "duration_beats": 1.0, "midi": 62, "velocity": .6},
        {"start_beat": 0.0, "duration_beats": 1.0, "midi": 69, "velocity": .6},
    ]
    realized = realize_violin_performance(ir, "lead", config={"strict_comfort": False})
    patch = realized["instruments"]["lead"]
    engine = engine_for_patch(patch)
    assert engine.render_track(realized["tracks"][0]["events"], 44100, 22050, patch, .75) is None
