import hashlib
import json
import wave
from pathlib import Path

from code_composer.agent.expressive_score_plan import (
    expressive_score_plan_from_dict,
    validate_expressive_score_plan,
)
from code_composer.composition.performance import performance_context_from_ir


ROOT=Path(__file__).resolve().parents[1]
DOG=ROOT/"examples/v1.16/final_closure"


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_final_closure_manifest_passes_all_three_categories():
    manifest=_json(DOG/"final_closure_manifest.json")
    assert manifest["status"]=="PASS"
    assert set(manifest["cases"])=={
        "A_lyrical_piano",
        "B_rhythm_centered",
        "C_sparse_chamber_electronic",
    }

    for case,data in manifest["cases"].items():
        assert data["sample_rate"]>=44100
        assert data["clipped_sample_ratio"]==0.0
        assert data["deterministic"] is True
        assert data["sha256"]==data["repeat_sha256"]
        assert data["legacy_high_medium_after"]==[]
        assert all(data["stage_gates"].values())
        assert data["transition_count"]>=2
        assert data["active_transition_count"]>=2
        assert data["motif_statement_count"]>=4
        assert data["realized_motif_phrase_count"]>=4
        assert data["performance_phrase_count"]>=4
        assert data["register_role_count"]>=2
        assert data["orchestration_section_count"]>=4
        cmp=data["revision_comparison"]
        assert cmp["target_improved"] is True
        assert cmp["regression_free"] is True
        assert cmp["introduced_high_medium_count"]==0
        assert cmp["after_issue_count"]==0
        assert cmp["improved"] is True


def test_final_plans_are_valid_and_distinct_from_before_revisions():
    for case in sorted(p for p in DOG.iterdir() if p.is_dir()):
        base=_json(case/"base_ir.json")
        ctx=performance_context_from_ir(base)
        before=_json(case/"plan_before.json")
        after=_json(case/"plan_after.json")

        assert before != after
        validate_expressive_score_plan(expressive_score_plan_from_dict(before),ctx)
        validate_expressive_score_plan(expressive_score_plan_from_dict(after),ctx)


def test_externalized_after_wav_evidence_matches_manifest_hashes_and_sample_rate():
    manifest=_json(DOG/"final_closure_manifest.json")
    migration=_json(ROOT/"docs/maintenance/GITHUB_SOURCE_FIRST_MIGRATION.json")
    by_path={e["path"]:e for e in migration["externalized_historical_audio"]}
    for case_name,data in manifest["cases"].items():
        rel=f"examples/v1.16/final_closure/{case_name}/after.wav"
        assert by_path[rel]["sha256"]==data["sha256"]
        assert by_path[rel]["bytes"]>0
        assert data["sample_rate"]>=44100


def test_each_resolved_after_contains_real_e1_through_e5_provenance():
    for case in sorted(p for p in DOG.iterdir() if p.is_dir()):
        resolved=_json(case/"resolved_after.json")
        assert resolved["performance_resolved"] is True
        assert resolved["motif_development_resolved"] is True
        assert resolved["register_voicing_resolved"] is True
        assert resolved["orchestration_budget_resolved"] is True
        assert resolved["musical_transitions_resolved"] is True

        assert resolved["performance_report"]["phrase_count"]>=4
        assert resolved["motif_development_report"]["realized_phrase_count"]>=4
        assert resolved["register_voicing_report"]["role_count"]>=2
        assert resolved["orchestration_budget_report"]["section_count"]>=4
        assert resolved["musical_transition_report"]["transition_count"]>=2


def test_final_after_expressive_qa_is_clean_and_before_has_actionable_evidence():
    for case in sorted(p for p in DOG.iterdir() if p.is_dir()):
        before=_json(case/"analysis_before.json")
        after=_json(case/"analysis_after.json")
        assert before["expressive_qa"]["issue_count"]>0
        assert after["expressive_qa"]["issue_count"]==0
        assert [
            i for i in after.get("issues",[])
            if i.get("severity") in {"high","medium"}
        ]==[]


def test_sparse_case_only_retains_documented_low_severity_spectral_evidence():
    after=_json(DOG/"C_sparse_chamber_electronic/analysis_after.json")
    low=[i for i in after["issues"] if i.get("severity")=="low"]
    assert [i["code"] for i in low]==["BRIGHTNESS_EXCESS"]
    note=_json(DOG/"C_sparse_chamber_electronic/agent_revision.json")
    assert "non_blocking_note" in note
