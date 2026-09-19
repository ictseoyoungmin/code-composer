import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_l5_closes_legacy_cleanup_without_reopening_v116():
    status = json.loads((ROOT / "V1.16_DESIGN_STATUS.json").read_text(encoding="utf-8"))
    assert status["status"] == "V1.16_FINAL_CLOSED"
    assert status["v1.16_final_closed"] is True
    maintenance = status["maintenance"]["legacy_cleanup"]
    assert maintenance["status"] == "L5_CLEAN_INSTALL_COMPATIBILITY_CLOSED"
    assert maintenance["release_reopened"] is False
    assert maintenance["l5_clean_install_compatibility"] is True
    assert len(maintenance["closed"]) == 6


def test_l1_retained_and_l2_removed_flat_surfaces_match_source_tree():
    audit = json.loads(
        (ROOT / "docs/maintenance/L1_PUBLIC_IMPORT_COMPATIBILITY_AUDIT.json").read_text(encoding="utf-8")
    )
    retained = [row["module"] for row in audit["flat_surface_decisions"] if row["decision"] != "REMOVE_IN_L2"]
    removed = [row["module"] for row in audit["flat_surface_decisions"] if row["decision"] == "REMOVE_IN_L2"]
    assert len(retained) == 34
    assert len(removed) == 4
    for module in retained:
        assert importlib.util.find_spec(module) is not None, module
    for module in removed:
        assert importlib.util.find_spec(module) is None, module


def test_nested_superseded_mutation_targets_stay_removed():
    audit = json.loads(
        (ROOT / "docs/maintenance/L1_PUBLIC_IMPORT_COMPATIBILITY_AUDIT.json").read_text(encoding="utf-8")
    )
    targets = [row["module"] for row in audit["legacy_semantic_targets"]]
    assert len(targets) == 4
    for module in targets:
        assert importlib.util.find_spec(module) is None, module


def test_clean_install_gate_is_documented_as_source_tree_independent():
    build = (ROOT / "docs/BUILD.md").read_text(encoding="utf-8")
    assert "outside the repository" in build
    assert 'importlib.metadata.version("code-composer")' in build
    assert "wheel-shipped reference assets" in build
    assert "explicitly removed legacy mutation surfaces" in build
    assert "established baseline" in build


def test_l5_machine_evidence_records_installed_distribution_proofs():
    evidence = json.loads(
        (ROOT / "docs/maintenance/L5_CLEAN_INSTALL_COMPATIBILITY.json").read_text(encoding="utf-8")
    )
    assert evidence["status"] == "CLOSED"
    assert evidence["release_baseline"] == "v1.16.0 CLOSED"
    assert evidence["release_reopened"] is False
    clean = evidence["clean_install"]
    assert clean["version_attr"] == clean["metadata_version"] == "1.16.0"
    assert clean["source_tree_on_import_path"] is False
    assert clean["retained_public_imports"]["passed"] == 34
    assert clean["removed_flat_imports"]["absent"] == 4
    assert clean["removed_nested_targets"]["absent"] == 4
    assert clean["console_entrypoints"]["code-composer"] == "PASS"
    assert clean["console_entrypoints"]["code-composer-compose"] == "PASS"
    assert clean["legacy_wav"]["byte_identical"] is True
    assert clean["legacy_wav"]["sha256"] == "589ac3efdc466a1a7c191caa0e614a63b1a28e4dea566b08164df3730f4490e0"
