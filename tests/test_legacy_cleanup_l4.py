import hashlib
import json
from pathlib import Path
from _paths import KIT_ROOT, SOURCE_ROOT


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/maintenance/L4_DEAD_TEST_REFERENCE_CLEANUP.json"
CASES = ("A_lyrical_piano", "B_rhythm_centered", "C_sparse_chamber_electronic")
REMOVED_NAMES = ("after_repeat.wav", "analysis_after_repeat.json", "resolved_after_repeat.json", "before_vs_after.wav")


def _report():
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_l4_removed_exactly_the_l3_authorized_twelve_files():
    report = _report()
    assert report["status"] == "CLOSED"
    assert report["removed_count"] == 12
    assert report["removed_bytes"] == 37_197_041
    expected = {f"examples/v1.16/final_closure/{case}/{name}" for case in CASES for name in REMOVED_NAMES}
    assert {e["path"] for e in report["removed"]} == expected
    for rel in expected:
        assert not (ROOT / rel).exists()


def test_l4_retains_canonical_final_closure_evidence():
    manifest = json.loads((ROOT / "examples/v1.16/final_closure/final_closure_manifest.json").read_text())
    historical = json.loads((ROOT / "docs/maintenance/L3_HISTORICAL_FIXTURE_CLASSIFICATION.json").read_text())
    by_path = {e["path"]: e for e in historical["entries"]}
    for case, data in manifest["cases"].items():
        base = ROOT / "examples/v1.16/final_closure" / case
        for name in ("analysis_before.json", "analysis_after.json", "resolved_before.json", "resolved_after.json", "music_ir_before.json", "music_ir_after.json"):
            assert (base / name).exists()
        after_rel=f"examples/v1.16/final_closure/{case}/after.wav"
        before_rel=f"examples/v1.16/final_closure/{case}/before.wav"
        assert by_path[after_rel]["sha256"] == data["sha256"]
        assert by_path[before_rel]["sha256"]
        assert data["deterministic"] is True
        assert data["sha256"] == data["repeat_sha256"]


def test_l4_predelete_duplicate_and_comparison_proofs_are_complete():
    report = _report()
    assert set(report["comparison_derivation_proof"]) == set(CASES)
    for case, proof in report["comparison_derivation_proof"].items():
        assert proof["exact_predelete_proof"] is True
        assert proof["gap_frames"] == 30869
        assert proof["sample_rate"] == 44100
        assert abs(proof["gap_seconds"] - 0.6999773242630386) < 1e-12
    dup = [e for e in report["removed"] if e.get("candidate_reason") == "exact_duplicate_of_retained_evidence"]
    derived = [e for e in report["removed"] if e.get("candidate_reason") == "derived_listening_convenience_reconstructible_from_before_after"]
    assert len(dup) == 9
    assert len(derived) == 3


def test_l4_closure_remains_recorded_after_later_maintenance():
    status = json.loads((ROOT / "docs/history/status/V1.16_DESIGN_STATUS.json").read_text())
    assert status["status"] == "V1.16_FINAL_CLOSED"
    assert status["v1.16_final_closed"] is True
    cleanup = status["maintenance"]["legacy_cleanup"]
    assert cleanup["release_reopened"] is False
    assert "L4 Dead test / reference cleanup" in cleanup["closed"]
    assert cleanup["l4_removed_count"] == 12
    assert cleanup["l4_removed_bytes"] == 37_197_041
    report = _report()
    assert report["status"] == "CLOSED"
    assert report["next"] == "L5 Clean Install / Compatibility"


def test_l4_v116_runtime_baseline_is_preserved_when_future_features_are_added():
    report = _report()
    # The L4 aggregate is historical evidence for the v1.16 tree, not a rule that
    # future releases may never add runtime modules.  Protect every v1.16 runtime
    # file individually (except the package version declaration) while allowing
    # additive v1.17 export adapters.
    assert report["src_schema_aggregate_sha256"] == "bcee602c1f5d96246910acf1052496923fb4aafc52cf0a8becd84759f6318ea4"
    baseline=json.loads((ROOT/"docs/maintenance/V116_RUNTIME_BASELINE.json").read_text(encoding="utf-8"))
    assert baseline["status"] == "V1.16.0_CLOSED_RUNTIME_BASELINE"
    intentionally_unshipped_prefix="src/code_composer/reference/examples/"
    s0_packaging_only_change="src/code_composer/reference/__init__.py"
    future=json.loads((ROOT/"docs/maintenance/POST_V116_INTENTIONAL_SOURCE_CHANGES.json").read_text(encoding="utf-8"))
    declared=future.get("files",{})
    for rel, expected in baseline["files"].items():
        if rel.startswith(intentionally_unshipped_prefix) or rel == s0_packaging_only_change:
            continue
        path=(KIT_ROOT/rel) if (rel.startswith("src/") or rel.startswith("schemas/")) else (ROOT/rel)
        assert path.exists(), rel
        current=hashlib.sha256(path.read_bytes()).hexdigest()
        if rel in declared:
            assert declared[rel]["sha256"] == current, rel
            assert declared[rel].get("reason"), rel
        else:
            assert current == expected, rel
    # Intentional-change records may only name files that existed in the closed v1.16 baseline.
    assert set(declared) <= set(baseline["files"])
    assert not list((SOURCE_ROOT/"reference"/"examples").glob("*.json"))


def test_l4_current_navigation_does_not_present_removed_files_as_available_artifacts():
    current = [ROOT/"README.md", ROOT/"docs/STRUCTURE.md", ROOT/"docs/INDEX.md", ROOT/"examples/README.md", ROOT/"examples/v1.16/final_closure/README.md"]
    forbidden_phrases = ("retained through L3 only as explicit L4 review candidates", "are **L4 candidates only** and are not deleted in L3")
    text="\n".join(p.read_text(encoding="utf-8") for p in current)
    for phrase in forbidden_phrases:
        assert phrase not in text
    assert "L0-L5 legacy cleanup" in (ROOT/"CHANGELOG.md").read_text() or "L0-L5" in (ROOT/"CHANGELOG.md").read_text()


def test_l4_historical_l3_snapshot_is_preserved_not_rewritten_as_current_state():
    l3 = json.loads((ROOT/"docs/maintenance/L3_HISTORICAL_FIXTURE_CLASSIFICATION.json").read_text())
    assert l3["summary"]["l4_candidate_count"] == 12
    assert l3["summary"]["l4_candidate_bytes"] == 37_197_041
    assert _report()["l3_snapshot_preserved"] is True
