import json
from pathlib import Path

import pytest

from code_composer.performance.violin import ViolinPerformanceError, plan_violin_track, realize_violin_performance
from code_composer.performance.violin_double_stop import (
    ViolinDoubleStopError,
    double_stop_candidates,
)
from code_composer.presets import materialize_preset

ROOT = Path(__file__).resolve().parents[1]


def _event(start, midi, duration=1.0, articulation="neutral", velocity=.62):
    return {
        "start_beat": float(start),
        "duration_beats": float(duration),
        "midi": int(midi),
        "velocity": float(velocity),
        "performance": {"articulation": articulation},
    }


def test_open_fifth_uses_adjacent_d_a_strings():
    plan = plan_violin_track([_event(0, 62), _event(0, 69)], bpm=80)
    assert plan["playability"]["classification"] == "comfortable"
    assert len(plan["events"]) == 2
    assert {x["left_hand"]["finger"] for x in plan["events"]} == {0}
    assert {tuple(x["double_stop"]["string_pair"]) for x in plan["events"]} == {("D", "A")}
    assert {tuple(x["bow"]["contact_strings"]) for x in plan["events"]} == {("D", "A")}
    assert len({x["gesture_id"] for x in plan["events"]}) == 1


def test_stopped_fifth_can_use_one_flattened_finger():
    candidates = double_stop_candidates(64, 71)  # E4 + B4, same stop distance on D/A.
    assert any(c["double_stop"]["same_finger_fifth"] for c in candidates)
    fifth = next(c for c in candidates if c["double_stop"]["same_finger_fifth"])
    assert fifth["double_stop"]["string_pair"] == ["D", "A"]
    fingers = [n["left_hand"]["finger"] for n in fifth["notes"]]
    assert fingers[0] == fingers[1] and fingers[0] > 0


def test_nonadjacent_string_pair_is_rejected_in_s4_scope():
    with pytest.raises(ViolinDoubleStopError, match="no supported adjacent-string"):
        double_stop_candidates(55, 90)  # G3 is G-only; MIDI 90 is no longer reachable on D.


def test_duplicate_pitch_is_not_a_supported_double_stop():
    with pytest.raises(ViolinDoubleStopError, match="distinct"):
        double_stop_candidates(69, 69)


def test_triple_stop_is_explicitly_out_of_scope():
    events = [_event(0, 62), _event(0, 69), _event(0, 76)]
    with pytest.raises(ViolinPerformanceError, match="at most two"):
        plan_violin_track(events, bpm=80)


def test_double_stop_requires_equal_duration_and_shared_articulation():
    with pytest.raises(ViolinPerformanceError, match="equal duration"):
        plan_violin_track([_event(0, 62, 1.0), _event(0, 69, .5)], bpm=80)
    with pytest.raises(ViolinPerformanceError, match="share one articulation"):
        plan_violin_track([
            _event(0, 62, articulation="legato"),
            _event(0, 69, articulation="neutral"),
        ], bpm=80)


def test_overlapping_different_onsets_are_not_silently_treated_as_double_stops():
    events = [
        _event(0, 62, 2.0), _event(0, 69, 2.0),
        _event(1, 64, 1.0),
    ]
    with pytest.raises(ViolinPerformanceError, match="overlapping different onsets"):
        plan_violin_track(events, bpm=80)


def test_double_stop_path_is_deterministic_across_single_and_double_gestures():
    events = [
        _event(0, 62, articulation="legato"),
        _event(1, 64, articulation="legato"),
        _event(2, 64, articulation="neutral"),
        _event(2, 71, articulation="neutral"),
        _event(3, 69),
    ]
    a = plan_violin_track(events, bpm=84, config={"strict_comfort": False})
    b = plan_violin_track(events, bpm=84, config={"strict_comfort": False})
    assert a == b
    ds = [x for x in a["events"] if x.get("gesture_type") == "double_stop"]
    assert len(ds) == 2 and ds[0]["gesture_id"] == ds[1]["gesture_id"]
    assert a["playability"]["max_gesture_score"] >= 0


def test_strict_comfort_can_reject_a_double_stop_without_rewriting_it():
    events = [_event(0, 62), _event(0, 69)]
    with pytest.raises(ViolinPerformanceError, match="exceeds comfortable threshold"):
        plan_violin_track(events, bpm=80, config={
            "comfortable_transition_score": .1,
            "challenging_transition_score": 10.0,
        })
    plan = plan_violin_track(events, bpm=80, config={
        "strict_comfort": False,
        "comfortable_transition_score": .1,
        "challenging_transition_score": 10.0,
    })
    assert plan["playability"]["classification"] == "challenging"
    assert [x["midi"] for x in plan["events"]] == [62, 69]


def test_ir_integration_attaches_shared_gesture_evidence_to_both_notes():
    ir = json.loads((ROOT / "tests/fixtures/high_level_ir.json").read_text())
    ir["instruments"]["lead"] = materialize_preset("bowed.violin.synthetic_warm", role="lead")
    from code_composer.composition.resolve import resolve_ir
    ir = resolve_ir(ir)
    # Replace the lead with a minimal mechanical fixture; root tests are not agent-facing.
    lead = next(t for t in ir["tracks"] if t["id"] == "lead")
    lead["events"] = [_event(0, 62), _event(0, 69), _event(1, 64)]
    out = realize_violin_performance(ir, "lead", config={"strict_comfort": False})
    lead2 = next(t for t in out["tracks"] if t["id"] == "lead")
    first = sorted(lead2["events"][:2], key=lambda e: e["midi"])
    r0 = first[0]["performance"]["violin_realization"]
    r1 = first[1]["performance"]["violin_realization"]
    assert r0["gesture_type"] == r1["gesture_type"] == "double_stop"
    assert r0["gesture_id"] == r1["gesture_id"]
    assert r0["double_stop"]["partner_midi"] == first[1]["midi"]
    assert r1["double_stop"]["partner_midi"] == first[0]["midi"]
    assert r0["bow"]["contact_strings"] == r1["bow"]["contact_strings"]


def test_double_stop_report_still_validates_against_shipped_schema():
    import jsonschema
    ir = json.loads((ROOT / "tests/fixtures/high_level_ir.json").read_text())
    ir["instruments"]["lead"] = materialize_preset("bowed.violin.synthetic_warm", role="lead")
    from code_composer.composition.resolve import resolve_ir
    ir = resolve_ir(ir)
    lead = next(t for t in ir["tracks"] if t["id"] == "lead")
    lead["events"] = [_event(0, 62), _event(0, 69), _event(1, 64)]
    out = realize_violin_performance(ir, "lead", config={"strict_comfort": False})
    schema = json.loads((ROOT / "skills/code-composer/kit/schemas/violin_performance.schema.json").read_text())
    jsonschema.validate(out["violin_performance_report"], schema)
