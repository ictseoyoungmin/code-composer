import json
import sys
from pathlib import Path

from ..core.song import song_summary
from ..execution import execution_plan_fingerprint, lower_song_to_execution_plan
from ..execution.artistic_render import render_song_score_to_files
from ..execution.performance_revision import apply_revision_plan
from ..execution.revision_compare import render_revision_comparison_to_dir
from ..song_validation import validate_song_for_runtime


def _validate(path: Path) -> dict:
    song = json.loads(path.read_text(encoding="utf-8"))
    validate_song_for_runtime(song)
    out = song_summary(song)
    out["path"] = str(path)
    out["valid"] = True
    return out


def _lower(song_path: Path, plan_path: Path) -> dict:
    song = json.loads(song_path.read_text(encoding="utf-8"))
    plan = lower_song_to_execution_plan(song)
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "source_song": str(song_path),
        "execution_plan": str(plan_path),
        "source_fingerprint": plan["source_song"]["fingerprint"],
        "plan_fingerprint": execution_plan_fingerprint(plan),
        "sections": len(plan["sections"]),
        "instruments": len(plan["instruments"]),
        "tracks": len(plan["tracks"]),
        "part_instances": len(plan["part_instances"]),
    }


def _render(song_path: Path, score_path: Path, wav_path: Path, resolved_path=None, analysis_path=None) -> dict:
    song = json.loads(song_path.read_text(encoding="utf-8"))
    score = json.loads(score_path.read_text(encoding="utf-8"))
    result = render_song_score_to_files(
        song,
        score,
        wav_path,
        resolved_path=resolved_path,
        analysis_path=analysis_path,
    )
    report = result.get("violin_performance_report") or {}
    return {
        "source_song": str(song_path),
        "performance_score": str(score_path),
        "wav": str(wav_path),
        "sample_rate": int(result["sr"]),
        "execution_plan_fingerprint": result["execution_plan_fingerprint"],
        "performance_score_fingerprint": result["performance_score_fingerprint"],
        "violin_playability": (report.get("playability") or {}).get("classification"),
        "violin_max_transition_score": (report.get("playability") or {}).get("max_transition_score"),
    }


def _revise(score_path: Path, plan_path: Path, out_score_path: Path, record_path: Path) -> dict:
    score = json.loads(score_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    revised, record = apply_revision_plan(score, plan)
    out_score_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.parent.mkdir(parents=True, exist_ok=True)
    out_score_path.write_text(
        json.dumps(revised, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    record_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "source_score": str(score_path),
        "revision_plan": str(plan_path),
        "revised_score": str(out_score_path),
        "revision_record": str(record_path),
        "source_score_fingerprint": record["source_score_fingerprint"],
        "revision_plan_fingerprint": record["revision_plan_fingerprint"],
        "after_score_fingerprint": record["after_score_fingerprint"],
        "changed_event_ids": record["changed_event_ids"],
        "changed_mix_tracks": record["changed_mix_tracks"],
    }


def _compare_revision(song_path: Path, score_path: Path, plan_path: Path, output_dir: Path) -> dict:
    song = json.loads(song_path.read_text(encoding="utf-8"))
    score = json.loads(score_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    result = render_revision_comparison_to_dir(song, score, plan, output_dir)
    comparison = result["comparison"]
    return {
        "output_dir": str(output_dir),
        "source_score_fingerprint": comparison["source_score_fingerprint"],
        "revision_plan_fingerprint": comparison["revision_plan_fingerprint"],
        "after_score_fingerprint": comparison["after_score_fingerprint"],
        "before_wav_sha256": comparison["before"]["wav_sha256"],
        "after_wav_sha256": comparison["after"]["wav_sha256"],
        "same_sample_rate": comparison["same_sample_rate"],
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) == 2 and argv[0] == "validate":
        out = _validate(Path(argv[1]))
    elif len(argv) == 3 and argv[0] == "lower":
        out = _lower(Path(argv[1]), Path(argv[2]))
    elif 4 <= len(argv) <= 6 and argv[0] == "render":
        resolved = Path(argv[4]) if len(argv) >= 5 else None
        analysis = Path(argv[5]) if len(argv) >= 6 else None
        out = _render(Path(argv[1]), Path(argv[2]), Path(argv[3]), resolved, analysis)
    elif len(argv) == 5 and argv[0] == "revise":
        out = _revise(Path(argv[1]), Path(argv[2]), Path(argv[3]), Path(argv[4]))
    elif len(argv) == 5 and argv[0] == "compare-revision":
        out = _compare_revision(Path(argv[1]), Path(argv[2]), Path(argv[3]), Path(argv[4]))
    else:
        raise SystemExit(
            "usage: code-composer-song validate <song.json>\n"
            "   or: code-composer-song lower <song.json> <execution-plan.json>\n"
            "   or: code-composer-song render <song.json> <performance-score.json> <out.wav> [resolved.json] [analysis.json]\n"
            "   or: code-composer-song revise <performance-score.json> <revision-plan.json> <revised-score.json> <revision-record.json>\n"
            "   or: code-composer-song compare-revision <song.json> <performance-score.json> <revision-plan.json> <output-dir>"
        )

    print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
