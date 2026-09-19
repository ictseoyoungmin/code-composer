import json
from copy import deepcopy
from pathlib import Path

import pytest

from code_composer.performance.violin import (
    ViolinPerformanceError,
    fingering_candidates,
    plan_violin_track,
    realize_violin_performance,
)
from code_composer.presets import materialize_preset

ROOT = Path(__file__).resolve().parents[1]


def _events():
    return [
        {"start_beat": 0.0, "duration_beats": 1.0, "midi": 62, "velocity": .55, "performance": {"articulation": "legato"}},
        {"start_beat": 1.0, "duration_beats": 1.0, "midi": 64, "velocity": .60, "performance": {"articulation": "legato"}},
        {"start_beat": 2.0, "duration_beats": 1.0, "midi": 66, "velocity": .64, "performance": {"articulation": "legato"}},
        {"start_beat": 3.0, "duration_beats": 1.0, "midi": 67, "velocity": .62, "performance": {"articulation": "neutral"}},
    ]


def test_standard_range_has_candidate_fingering_everywhere():
    for midi in range(55, 106):
        assert fingering_candidates(midi), midi
    assert fingering_candidates(54) == []
    assert fingering_candidates(106) == []


def test_open_strings_are_explicit_zero_finger_candidates():
    for midi, name in [(55, "G"), (62, "D"), (69, "A"), (76, "E")]:
        opens = [c for c in fingering_candidates(midi) if c["finger"] == 0]
        assert any(c["string"] == name and c["position"] == 0 for c in opens)


def test_monophonic_planner_is_deterministic_and_comfortable():
    a = plan_violin_track(_events(), bpm=84)
    b = plan_violin_track(_events(), bpm=84)
    assert a == b
    assert a["playability"]["classification"] == "comfortable"
    assert len(a["events"]) == 4
    assert all(x["left_hand"]["finger"] in {0, 1, 2, 3, 4} for x in a["events"])


def test_legato_notes_share_bow_until_articulation_boundary():
    plan = plan_violin_track(_events(), bpm=84)
    ids = [x["bow"]["group_id"] for x in plan["events"]]
    assert ids[0] == ids[1] == ids[2]
    assert ids[3] != ids[2]
    assert plan["events"][0]["bow"]["direction"] == "down"
    assert plan["events"][3]["bow"]["direction"] == "up"


def test_planner_routes_supported_same_onset_to_double_stop_realization():
    events = [
        {"start_beat": 0.0, "duration_beats": 1.0, "midi": 62, "velocity": .58},
        {"start_beat": 0.0, "duration_beats": 1.0, "midi": 69, "velocity": .58},
    ]
    plan = plan_violin_track(events, bpm=84)
    assert len(plan["events"]) == 2
    assert {x["gesture_type"] for x in plan["events"]} == {"double_stop"}
    assert {tuple(x["double_stop"]["string_pair"]) for x in plan["events"]} == {("D", "A")}


def test_planner_rejects_out_of_range_note():
    with pytest.raises(ViolinPerformanceError, match="outside configured violin range"):
        plan_violin_track([{"start_beat": 0, "duration_beats": 1, "midi": 48, "velocity": .5}], bpm=84)


def test_strict_comfort_can_reject_extreme_fast_shift():
    events = [
        {"start_beat": 0.0, "duration_beats": .06, "midi": 55, "velocity": .7},
        {"start_beat": .07, "duration_beats": .06, "midi": 103, "velocity": .7},
    ]
    with pytest.raises(ViolinPerformanceError, match="exceeds comfortable threshold"):
        plan_violin_track(events, bpm=160)
    plan = plan_violin_track(events, bpm=160, config={"strict_comfort": False})
    assert plan["playability"]["classification"] in {"challenging", "impractical"}


def test_integration_attaches_left_hand_bow_and_engine_expression():
    ir = json.loads((ROOT / "tests/fixtures/high_level_ir.json").read_text())
    ir["instruments"]["lead"] = materialize_preset("bowed.violin.synthetic_warm", role="lead")
    out = realize_violin_performance(ir, "lead", config={"strict_comfort": False})
    assert out["violin_performance_resolved"] is True
    report = out["violin_performance_report"]
    assert report["track_id"] == "lead" and report["event_count"] > 0
    lead = next(t for t in out["tracks"] if t["id"] == "lead")
    event = lead["events"][0]
    vr = event["performance"]["violin_realization"]
    assert vr["left_hand"]["string"] in {"G", "D", "A", "E"}
    assert vr["bow"]["direction"] in {"down", "up"}
    expr = event["performance"]["instrument_expression"]
    assert 0.2 <= expr["bow_pressure"] <= .88
    assert 0.2 <= expr["bow_speed"] <= .9


def test_explicit_expression_is_preserved_not_overwritten():
    ir = json.loads((ROOT / "tests/fixtures/high_level_ir.json").read_text())
    ir["instruments"]["lead"] = materialize_preset("bowed.violin.synthetic_warm", role="lead")
    # Resolve first, then author an explicit performance expression on one event.
    from code_composer.composition.resolve import resolve_ir
    resolved = resolve_ir(ir)
    lead = next(t for t in resolved["tracks"] if t["id"] == "lead")
    lead["events"][0]["performance"] = {
        "instrument_expression": {"bow_pressure": .81, "vibrato_depth_cents": 31}
    }
    out = realize_violin_performance(resolved, "lead", config={"strict_comfort": False})
    lead2 = next(t for t in out["tracks"] if t["id"] == "lead")
    expr = lead2["events"][0]["performance"]["instrument_expression"]
    assert expr["bow_pressure"] == .81
    assert expr["vibrato_depth_cents"] == 31


def test_cli_emits_realized_ir(tmp_path, capsys):
    from code_composer.app.violin_cli import main
    ir = json.loads((ROOT / "tests/fixtures/high_level_ir.json").read_text())
    ir["instruments"]["lead"] = materialize_preset("bowed.violin.synthetic_warm", role="lead")
    inp = tmp_path / "in.json"; out = tmp_path / "out.json"
    inp.write_text(json.dumps(ir))
    assert main([str(inp), "lead", str(out), "--allow-challenging"]) == 0
    payload = json.loads(out.read_text())
    assert payload["violin_performance_report"]["event_count"] > 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["scope"]["monophonic_only"] is False
    assert printed["scope"]["double_stops"] == "synchronous_adjacent_strings"

def test_violin_report_matches_shipped_schema():
    import jsonschema
    ir = json.loads((ROOT / "tests/fixtures/high_level_ir.json").read_text())
    ir["instruments"]["lead"] = materialize_preset("bowed.violin.synthetic_warm", role="lead")
    out = realize_violin_performance(ir, "lead", config={"strict_comfort": False})
    schema = json.loads((ROOT / "skills/code-composer/kit/schemas/violin_performance.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(out["violin_performance_report"], schema)


def test_surface_exposes_violin_performance_capability():
    surface = json.loads((ROOT / "skills/code-composer/kit/surface.json").read_text())
    assert surface["capabilities"]["violin_performance"] == {
        "entrypoint": "code-composer-violin",
        "workflow": "workflows/violin-performance.md",
    }
