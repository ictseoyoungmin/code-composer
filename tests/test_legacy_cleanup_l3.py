import hashlib
import json
from pathlib import Path
from _paths import SCHEMA_ROOT, PACKAGED_SCHEMA_ROOT, SOURCE_ROOT


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "docs/maintenance/L3_HISTORICAL_FIXTURE_CLASSIFICATION.json"
CASES = ("A_lyrical_piano", "B_rhythm_centered", "C_sparse_chamber_electronic")


def _inventory():
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


def test_l3_snapshot_remains_closed_historical_evidence():
    data = _inventory()
    assert data["status"] == "L3_HISTORICAL_FIXTURE_CLASSIFICATION_CLOSED"
    assert data["release_reopened"] is False
    assert data["next"] == "L4 Dead Test / Reference Cleanup"
    assert data["summary"]["l4_candidate_count"] == 12
    assert data["summary"]["l4_candidate_bytes"] == 37_197_041


def test_l3_snapshot_records_exact_authorized_candidate_boundary():
    candidates = [e for e in _inventory()["entries"] if e["classification"] == "L4_CANDIDATE"]
    expected = set()
    for case in CASES:
        base = f"examples/v1.16/final_closure/{case}"
        for name in ("after_repeat.wav", "analysis_after_repeat.json", "resolved_after_repeat.json", "before_vs_after.wav"):
            expected.add(f"{base}/{name}")
    assert {e["path"] for e in candidates} == expected
    assert sum(e["bytes"] for e in candidates) == 37_197_041


def test_l3_duplicate_claims_still_match_retained_peer_hashes_after_l4():
    entries = _inventory()["entries"]
    by_path = {e["path"]: e for e in entries}
    candidates = [e for e in entries if e["classification"] == "L4_CANDIDATE"]
    repeats = [e for e in candidates if e.get("candidate_reason") == "exact_duplicate_of_retained_evidence"]
    assert len(repeats) == 9
    for e in repeats:
        peer = by_path[e["retained_peer"]]
        assert peer["sha256"] == e["sha256"]
        assert e["duplicate_sha256_match"] is True


def test_l3_comparison_claims_preserve_retained_before_after_evidence():
    entries = _inventory()["entries"]
    by_path = {e["path"]: e for e in entries}
    candidates = [e for e in entries if e["classification"] == "L4_CANDIDATE"]
    comparisons = [e for e in candidates if e.get("candidate_reason") == "derived_listening_convenience_reconstructible_from_before_after"]
    assert len(comparisons) == 3
    for e in comparisons:
        peers=e["retained_peers"]
        assert len(peers)==2
        assert all(by_path[p]["classification"] == "HISTORICAL_EVIDENCE" for p in peers)
        assert all(by_path[p]["sha256"] for p in peers)


def test_s0_preserves_schema_mirrors_but_intentionally_retires_packaged_musical_example_mirrors():
    for name in ("composition_brief.schema.json","expressive_score_plan.schema.json","performance_ir.schema.json","piano_design.schema.json"):
        assert (SCHEMA_ROOT/name).read_bytes() == (PACKAGED_SCHEMA_ROOT/name).read_bytes()
    assert not list((SOURCE_ROOT/"reference"/"examples").glob("*.json"))
    # L3 remains historical evidence and is not rewritten to pretend this later S0 policy existed then.
    assert _inventory()["status"] == "L3_HISTORICAL_FIXTURE_CLASSIFICATION_CLOSED"
