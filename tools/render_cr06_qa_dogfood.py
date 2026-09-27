#!/usr/bin/env python3
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

from code_composer.execution import (
    apply_revision_plan,
    build_qa_report,
    compare_qa_reports,
    run_song_score_qa_to_dir,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/cr03/lantern_current"
REVISION = ROOT / "examples/cr04/lantern_current_coda"
DOGFOOD = ROOT / "examples/cr06/lantern_current_qa"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _probe_report(score, request, render_result, wav, mutate):
    probe = deepcopy(render_result)
    # NumPy arrays are copied explicitly; deepcopy is safe but keep the intent obvious.
    probe["audio"] = np.asarray(render_result["audio"], dtype=np.float64).copy()
    mutate(probe)
    return build_qa_report(score, request, probe, wav)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    song = _load(SOURCE / "song.json")
    base_score = _load(SOURCE / "performance_score.json")
    revision_plan = _load(REVISION / "revision_plan.json")
    score, revision_record = apply_revision_plan(base_score, revision_plan)
    request = _load(DOGFOOD / "qa_request.json")

    result = run_song_score_qa_to_dir(song, score, request, out / "accepted")
    report = result["report"]
    render_result = result["render_result"]
    wav = result["wav_path"]

    if report["integrity"]["status"] != "PASS":
        raise SystemExit(f"accepted Lantern Current failed integrity: {report['integrity']}")
    if report["semantics"]["aesthetic_score"] is not False:
        raise SystemExit("QA unexpectedly exposed an aesthetic score")
    if report["semantics"]["automatic_musical_acceptance"] is not False:
        raise SystemExit("QA unexpectedly exposed automatic musical acceptance")
    if report["semantics"]["automatic_revision"] is not False:
        raise SystemExit("QA unexpectedly exposed automatic revision")

    # Hard-gate probes: same valid subject, controlled objective corruption.
    clipped = _probe_report(
        score, request, render_result, wav,
        lambda x: x["audio"].__setitem__((0, 0), 1.2),
    )
    provenance = _probe_report(
        score, request, render_result, wav,
        lambda x: x.__setitem__("execution_plan_fingerprint", "0" * 64),
    )
    note_divergence = _probe_report(
        score, request, render_result, wav,
        lambda x: next(
            e for t in x["render_ir"]["tracks"] if t["id"] == "violin-line"
            for e in t["events"] if "midi" in e
        ).__setitem__("midi", 65),
    )

    expected = {
        "clipping_policy": clipped,
        "provenance_chain": provenance,
        "exact_note_authority": note_divergence,
    }
    probe_summary = {}
    for check_id, probe in expected.items():
        if probe["integrity"]["status"] != "FAIL" or check_id not in probe["integrity"]["failed_checks"]:
            raise SystemExit(f"hard-gate probe did not fail {check_id}: {probe['integrity']}")
        probe_summary[check_id] = {
            "status": probe["integrity"]["status"],
            "failed_checks": probe["integrity"]["failed_checks"],
        }

    # Anti-self-certification: identical music/render, changed evidence target only.
    mutated_request = deepcopy(request)
    mutated_request["evidence"]["parameters"]["high_register_midi"] = 72
    mutated_report = build_qa_report(score, mutated_request, render_result, wav)
    comparison = compare_qa_reports(report, mutated_report)
    if comparison["target_mutation"]["detected"] is not True:
        raise SystemExit("QA target mutation was not detected")
    if comparison["target_mutation"]["changed_fields"] != [
        "evidence.parameters.high_register_midi"
    ]:
        raise SystemExit(f"unexpected target mutation fields: {comparison['target_mutation']}")
    if comparison["semantics"]["improvement_verdict"] is not False:
        raise SystemExit("target mutation produced an improvement verdict")
    if comparison["before"]["score_fingerprint"] != comparison["after"]["score_fingerprint"]:
        raise SystemExit("target mutation dogfood changed the musical score")
    if comparison["before"]["hard_gate_status"] != comparison["after"]["hard_gate_status"]:
        raise SystemExit("target mutation dogfood changed hard integrity")

    (out / "target_mutated_request.json").write_text(
        json.dumps(mutated_request, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "target_mutated_report.json").write_text(
        json.dumps(mutated_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "qa_comparison.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "hard_gate_probes.json").write_text(
        json.dumps(probe_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "revision_record.json").write_text(
        json.dumps(revision_record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(SOURCE / "song.json", out / "song.json")
    shutil.copy2(DOGFOOD / "README.md", out / "README.md")

    evidence = {
        "schema": "code-composer-cr06-evidence-first-qa-dogfood/v1",
        "subject": "Lantern Current accepted CR04 revision",
        "accepted": {
            "hard_gate_status": report["integrity"]["status"],
            "failure_count": report["integrity"]["failure_count"],
            "score_fingerprint": report["source"]["performance_score_fingerprint"],
            "execution_plan_fingerprint": report["source"]["execution_plan_fingerprint"],
            "wav_sha256": report["source"]["wav_sha256"],
            "musical_evidence_fingerprint": report["musical_evidence_fingerprint"],
            "evidence_keys": sorted(report["musical_evidence"]),
        },
        "hard_gate_probes": probe_summary,
        "target_mutation": comparison["target_mutation"],
        "comparison_semantics": comparison["semantics"],
        "authority": {
            "hard_gate_may_block_integrity_failure": True,
            "musical_evidence_is_descriptive_only": True,
            "aesthetic_score": False,
            "automatic_musical_acceptance": False,
            "automatic_revision": False,
        },
    }
    (out / "evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    (out / "SHA256SUMS.txt").write_text(
        "".join(f"{_sha256(p)}  {p.relative_to(out).as_posix()}\n" for p in files),
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
