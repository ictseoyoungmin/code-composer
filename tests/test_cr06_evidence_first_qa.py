import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator

from code_composer.execution import (
    QaValidationError,
    apply_revision_plan,
    build_qa_report,
    compare_qa_reports,
    compile_performance_score_to_render_ir,
    execution_plan_fingerprint,
    lower_song_to_execution_plan,
    performance_score_fingerprint,
    qa_target_fingerprint,
    realize_instrument_mechanics,
    validate_qa_request,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/cr03/lantern_current"
REVISION = ROOT / "examples/cr04/lantern_current_coda"
DOGFOOD = ROOT / "examples/cr06/lantern_current_qa"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _song():
    return _load(SOURCE / "song.json")


def _base_score():
    return _load(SOURCE / "performance_score.json")


def _score():
    revised, _ = apply_revision_plan(
        _base_score(),
        _load(REVISION / "revision_plan.json"),
    )
    return revised


def _request():
    return _load(DOGFOOD / "qa_request.json")


def _fake_render(score):
    plan = lower_song_to_execution_plan(_song())
    ir = compile_performance_score_to_render_ir(plan, score)
    realized = realize_instrument_mechanics(ir, plan)
    return {
        "audio": np.full((8192, 2), 0.01, dtype=np.float64),
        "sr": 24000,
        "plan": plan,
        "render_ir": realized,
        "execution_plan_fingerprint": execution_plan_fingerprint(plan),
        "performance_score_fingerprint": performance_score_fingerprint(score),
        "violin_performance_report": realized.get("violin_performance_report"),
    }


def _report(tmp_path, *, request=None, mutate=None):
    score = _score()
    result = _fake_render(score)
    if mutate:
        mutate(result)
    wav = tmp_path / "qa.wav"
    wav.write_bytes(b"qa-test")
    return build_qa_report(score, request or _request(), result, wav)


def test_cr06_request_binds_exact_accepted_cr04_score():
    score = _score()
    req = _request()
    validate_qa_request(req)
    assert req["source_score"]["fingerprint"] == performance_score_fingerprint(score)
    assert qa_target_fingerprint(req) != req["source_score"]["fingerprint"]


@pytest.mark.parametrize("name", [
    "qa_request.schema.json",
    "qa_report.schema.json",
    "qa_comparison.schema.json",
])
def test_cr06_schema_copies_match(name):
    source = ROOT / "skills/code-composer/kit/schemas" / name
    packaged = ROOT / "skills/code-composer/kit/src/code_composer/reference/schemas" / name
    assert source.read_bytes() == packaged.read_bytes()
    Draft202012Validator.check_schema(json.loads(source.read_text(encoding="utf-8")))


def test_cr06_valid_subject_has_integrity_pass_and_no_aesthetic_authority(tmp_path):
    report = _report(tmp_path)
    assert report["integrity"]["status"] == "PASS"
    assert report["integrity"]["failure_count"] == 0
    assert report["semantics"]["aesthetic_score"] is False
    assert report["semantics"]["automatic_musical_acceptance"] is False
    assert report["semantics"]["automatic_revision"] is False
    assert set(report["musical_evidence"]) == {
        "dynamics", "spectrum", "register", "phrase_continuity",
        "repetition", "voice_leading", "tension_release", "masking",
    }

    schema = json.loads(
        (ROOT / "skills/code-composer/kit/schemas/qa_report.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(report)


def test_cr06_nonfinite_audio_is_hard_failure(tmp_path):
    def mutate(result):
        result["audio"][0, 0] = np.nan
    report = _report(tmp_path, mutate=mutate)
    assert report["integrity"]["status"] == "FAIL"
    assert "audio_finite" in report["integrity"]["failed_checks"]


def test_cr06_clipping_policy_violation_is_hard_failure(tmp_path):
    def mutate(result):
        result["audio"][0, 0] = 1.2
    report = _report(tmp_path, mutate=mutate)
    assert report["integrity"]["status"] == "FAIL"
    assert "clipping_policy" in report["integrity"]["failed_checks"]


def test_cr06_provenance_corruption_is_hard_failure(tmp_path):
    def mutate(result):
        result["execution_plan_fingerprint"] = "0" * 64
    report = _report(tmp_path, mutate=mutate)
    assert report["integrity"]["status"] == "FAIL"
    assert "provenance_chain" in report["integrity"]["failed_checks"]


def test_cr06_authored_note_divergence_is_hard_failure(tmp_path):
    def mutate(result):
        violin = next(t for t in result["render_ir"]["tracks"] if t["id"] == "violin-line")
        note = next(e for e in violin["events"] if "midi" in e)
        note["midi"] += 1
    report = _report(tmp_path, mutate=mutate)
    assert report["integrity"]["status"] == "FAIL"
    assert "exact_note_authority" in report["integrity"]["failed_checks"]


def test_cr06_impossible_mechanical_state_is_hard_failure(tmp_path):
    def mutate(result):
        result["violin_performance_report"]["playability"]["classification"] = "impractical"
    report = _report(tmp_path, mutate=mutate)
    assert report["integrity"]["status"] == "FAIL"
    assert "mechanical_realization" in report["integrity"]["failed_checks"]


def test_cr06_wrong_source_request_is_rejected_before_claiming_evidence(tmp_path):
    req = _request()
    req["source_score"]["fingerprint"] = "0" * 64
    score = _score()
    result = _fake_render(score)
    wav = tmp_path / "qa.wav"
    wav.write_bytes(b"qa-test")
    with pytest.raises(QaValidationError, match="source score fingerprint"):
        build_qa_report(score, req, result, wav)


def test_cr06_same_target_comparison_has_no_aesthetic_verdict(tmp_path):
    report = _report(tmp_path)
    cmp = compare_qa_reports(report, deepcopy(report))
    assert cmp["target_mutation"]["detected"] is False
    assert cmp["target_mutation"]["same_target_comparison"] is True
    assert cmp["semantics"]["improvement_verdict"] is False
    assert cmp["semantics"]["aesthetic_ranking"] is False


def test_cr06_changing_only_evidence_target_is_recorded_as_target_mutation(tmp_path):
    before = _report(tmp_path)
    req = _request()
    req["evidence"]["parameters"]["high_register_midi"] = 72
    after = _report(tmp_path, request=req)
    cmp = compare_qa_reports(before, after)
    assert cmp["target_mutation"]["detected"] is True
    assert cmp["target_mutation"]["same_target_comparison"] is False
    assert cmp["target_mutation"]["changed_fields"] == [
        "evidence.parameters.high_register_midi"
    ]
    assert cmp["semantics"]["target_mutation_cannot_be_presented_as_improvement"] is True

    schema = json.loads(
        (ROOT / "skills/code-composer/kit/schemas/qa_comparison.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(cmp)


def test_cr06_changing_hard_policy_is_also_target_mutation(tmp_path):
    before = _report(tmp_path)
    req = _request()
    req["hard_policy"]["max_clipped_sample_ratio"] = 0.01
    after = _report(tmp_path, request=req)
    cmp = compare_qa_reports(before, after)
    assert cmp["target_mutation"]["detected"] is True
    assert cmp["target_mutation"]["changed_fields"] == [
        "hard_policy.max_clipped_sample_ratio"
    ]


def test_cr06_qa_source_contains_no_automatic_revision_authority():
    source = (
        ROOT / "skills/code-composer/kit/src/code_composer/execution/qa.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "apply_revision_plan",
        "propose_from_issue",
        "apply_proposal",
        "try_proposal",
        "PatchOp",
        "good_music_score",
        "quality_score",
    )
    assert all(token not in source for token in forbidden)



def test_cr06_reordering_same_evidence_focus_is_not_target_mutation(tmp_path):
    before = _report(tmp_path)
    req = _request()
    req["evidence"]["focus"] = list(reversed(req["evidence"]["focus"]))
    after = _report(tmp_path, request=req)
    cmp = compare_qa_reports(before, after)
    assert cmp["target_mutation"]["detected"] is False
    assert cmp["target_mutation"]["changed_fields"] == []
    assert before["request"]["target_fingerprint"] == after["request"]["target_fingerprint"]
