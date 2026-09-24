"""CR04 matched before/after revision rendering."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .artistic_render import render_song_score_to_files
from .performance_revision import apply_revision_plan


REVISION_COMPARISON_FORMAT = "code-composer-revision-comparison/v1"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def render_revision_comparison_to_dir(song: dict, score: dict, plan: dict, output_dir):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    after_score, record = apply_revision_plan(score, plan)

    before_score_path = out / "before_score.json"
    after_score_path = out / "after_score.json"
    plan_path = out / "revision_plan.json"
    record_path = out / "revision_record.json"

    before_score_path.write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    after_score_path.write_text(json.dumps(after_score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    before = render_song_score_to_files(
        song, score, out / "before.wav",
        resolved_path=out / "before_resolved.json",
        analysis_path=out / "before_analysis.json",
    )
    after = render_song_score_to_files(
        song, after_score, out / "after.wav",
        resolved_path=out / "after_resolved.json",
        analysis_path=out / "after_analysis.json",
    )

    if int(before["sr"]) != int(after["sr"]):
        raise ValueError("matched A/B render sample rates differ")

    comparison = {
        "format": REVISION_COMPARISON_FORMAT,
        "source_song_fingerprint": record["source_song_fingerprint"],
        "source_score_fingerprint": record["source_score_fingerprint"],
        "revision_plan_fingerprint": record["revision_plan_fingerprint"],
        "after_score_fingerprint": record["after_score_fingerprint"],
        "same_sample_rate": int(before["sr"]) == int(after["sr"]),
        "before": {
            "wav": "before.wav",
            "wav_sha256": _sha256(out / "before.wav"),
            "metrics": before["metrics"],
        },
        "after": {
            "wav": "after.wav",
            "wav_sha256": _sha256(out / "after.wav"),
            "metrics": after["metrics"],
        },
        "metric_deltas": {
            key: float(after["metrics"][key]) - float(before["metrics"][key])
            for key in sorted(set(before["metrics"]) & set(after["metrics"]))
            if isinstance(before["metrics"][key], (int, float))
            and isinstance(after["metrics"][key], (int, float))
        },
        "closure_policy": {
            "metrics_are_evidence_not_aesthetic_scores": True,
            "perceptual_listening_required": True,
        },
    }
    (out / "revision_comparison.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "after_score": after_score,
        "revision_record": record,
        "comparison": comparison,
        "before_render": before,
        "after_render": after,
    }


__all__ = ["REVISION_COMPARISON_FORMAT", "render_revision_comparison_to_dir"]
