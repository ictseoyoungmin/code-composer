import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from code_composer.execution import (
    PerformanceRevisionError,
    apply_revision_plan,
    performance_score_fingerprint,
    revision_plan_fingerprint,
    validate_revision_plan,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/cr03/lantern_current"
DOGFOOD = ROOT / "examples/cr04/lantern_current_coda"


def _score():
    return json.loads((SOURCE / "performance_score.json").read_text(encoding="utf-8"))


def _plan():
    return json.loads((DOGFOOD / "revision_plan.json").read_text(encoding="utf-8"))


def _track(score, track_id):
    return next(t for t in score["tracks"] if t["id"] == track_id)


def _events_by_id(score, track_id):
    return {e["id"]: e for e in _track(score, track_id)["events"]}


def test_cr04_plan_binds_exact_lantern_score():
    score = _score()
    plan = _plan()
    validate_revision_plan(plan)
    assert plan["source_score"]["fingerprint"] == performance_score_fingerprint(score)
    assert len(revision_plan_fingerprint(plan)) == 64


def test_cr04_revision_plan_schema_copies_match_and_accept_dogfood():
    source = ROOT / "skills/code-composer/kit/schemas/revision_plan.schema.json"
    packaged = ROOT / "skills/code-composer/kit/src/code_composer/reference/schemas/revision_plan.schema.json"
    assert source.read_bytes() == packaged.read_bytes()
    schema = json.loads(source.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_plan())


def test_cr04_targeted_revision_preserves_locked_musical_scopes():
    before = _score()
    after, record = apply_revision_plan(before, _plan())

    assert _track(after, "violin-line") == _track(before, "violin-line")

    before_piano = _events_by_id(before, "piano-foundation")
    after_piano = _events_by_id(after, "piano-foundation")

    bass_ids = sorted(eid for eid in before_piano if "-bass" in eid)
    pedal_ids = sorted(eid for eid in before_piano if eid.startswith("pedal-"))
    for eid in bass_ids + pedal_ids:
        assert after_piano[eid] == before_piano[eid]

    assert "p-b11-u2" not in after_piano
    assert "p-b12-u2" not in after_piano

    scaled = ["p-b11-u1", "p-b11-u3", "p-b12-u1", "p-b12-u3"]
    for eid in scaled:
        assert after_piano[eid]["midi"] == before_piano[eid]["midi"]
        assert after_piano[eid]["start_beat"] == before_piano[eid]["start_beat"]
        assert after_piano[eid]["duration_beats"] == before_piano[eid]["duration_beats"]
        assert after_piano[eid]["velocity"] == pytest.approx(before_piano[eid]["velocity"] * 0.78)

    before_mix = next(x for x in before["render"]["mix"]["tracks"] if x["track"] == "piano-foundation")
    after_mix = next(x for x in after["render"]["mix"]["tracks"] if x["track"] == "piano-foundation")
    assert before_mix["gain"] == pytest.approx(0.50)
    assert after_mix["gain"] == pytest.approx(0.46)

    assert record["changed_event_ids"] == sorted([
        "p-b11-u1", "p-b11-u2", "p-b11-u3",
        "p-b12-u1", "p-b12-u2", "p-b12-u3",
    ])
    assert record["changed_mix_tracks"] == ["piano-foundation"]


def test_cr04_wrong_source_score_is_hard_error():
    plan = _plan()
    plan["source_score"]["fingerprint"] = "0" * 64
    with pytest.raises(PerformanceRevisionError, match="source score fingerprint mismatch"):
        apply_revision_plan(_score(), plan)


def test_cr04_revision_record_has_complete_fingerprint_chain():
    score = _score()
    plan = _plan()
    after, record = apply_revision_plan(score, plan)

    assert record["format"] == "code-composer-revision-record/v1"
    assert record["source_score_fingerprint"] == performance_score_fingerprint(score)
    assert record["revision_plan_fingerprint"] == revision_plan_fingerprint(plan)
    assert record["after_score_fingerprint"] == performance_score_fingerprint(after)
    assert record["source_song_fingerprint"] == score["source_song"]["fingerprint"]
    assert record["source_score_fingerprint"] != record["after_score_fingerprint"]


def test_cr04_revision_record_schema_accepts_generated_record():
    record_schema = ROOT / "skills/code-composer/kit/schemas/revision_record.schema.json"
    packaged = ROOT / "skills/code-composer/kit/src/code_composer/reference/schemas/revision_record.schema.json"
    assert record_schema.read_bytes() == packaged.read_bytes()
    schema = json.loads(record_schema.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    _, record = apply_revision_plan(_score(), _plan())
    Draft202012Validator(schema).validate(record)


def test_cr04_velocity_event_selector_rejects_unknown_or_out_of_range_ids():
    plan = _plan()
    vel = next(op for op in plan["ops"] if op["op"] == "scale_velocity")
    vel["event_ids"] = ["p-b11-u1", "not-an-event"]
    with pytest.raises(PerformanceRevisionError, match="unknown/out-of-range"):
        apply_revision_plan(_score(), plan)


def test_cr04_thinning_cannot_delete_pedal_control():
    plan = _plan()
    thin = next(op for op in plan["ops"] if op["op"] == "thin_accompaniment")
    thin["event_ids"] = ["pedal-b11"]
    with pytest.raises(PerformanceRevisionError, match="note events only"):
        apply_revision_plan(_score(), plan)


def test_cr04_register_shift_is_explicit_and_deterministic():
    plan = {
        "format": "code-composer-revision-plan/v1",
        "source_score": {
            "format": "code-composer-performance-score/v1",
            "fingerprint": performance_score_fingerprint(_score()),
        },
        "meta": {"id": "octave-test", "summary": "Move a violin phrase down one octave."},
        "critique": {
            "observations": ["The selected phrase should sit lower."],
            "preserve": ["All non-selected events."],
            "acceptance": ["Only selected beat-range pitches change by exactly one octave."],
        },
        "ops": [{
            "op": "shift_register",
            "track": "violin-line",
            "start_beat": 6.0,
            "end_beat": 9.0,
            "octaves": -1,
        }],
    }
    before = _score()
    after, record = apply_revision_plan(before, plan)
    b = _events_by_id(before, "violin-line")
    a = _events_by_id(after, "violin-line")
    for eid in ("v01", "v02", "v03"):
        assert a[eid]["midi"] == b[eid]["midi"] - 12
    assert a["v04"] == b["v04"]
    assert record["changed_event_ids"] == ["v01", "v02", "v03"]


def test_cr04_revision_surface_does_not_reintroduce_issue_to_patch_automation():
    source = (
        ROOT / "skills/code-composer/kit/src/code_composer/execution/performance_revision.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "propose_from_issue",
        "apply_proposal",
        "try_proposal",
        "PatchOp",
        "Proposal",
        "analyze_expressive_qa",
    )
    assert all(token not in source for token in forbidden)
