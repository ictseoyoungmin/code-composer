#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from code_composer.execution import apply_revision_plan, render_song_score_preview


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/cr03/lantern_current"
REVISION = ROOT / "examples/cr04/lantern_current_coda"
DOGFOOD = ROOT / "examples/cr05/lantern_current_preview"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _track_cache(report: dict) -> dict:
    return {x["track"]: x for x in report["cache"]["tracks"]}


def _run(song, score, request, wav, cache, report):
    return render_song_score_preview(
        song,
        score,
        request,
        wav,
        cache,
        report_path=report,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--cache")
    args = ap.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    cache = Path(args.cache) if args.cache else out.parent / "cr05-preview-cache"
    if cache.exists():
        shutil.rmtree(cache)
    cache.mkdir(parents=True, exist_ok=True)

    song = _load(SOURCE / "song.json")
    score = _load(SOURCE / "performance_score.json")
    revision_plan = _load(REVISION / "revision_plan.json")
    revised, revision_record = apply_revision_plan(score, revision_plan)
    original_request = _load(DOGFOOD / "original_request.json")
    revised_request = _load(DOGFOOD / "revised_request.json")

    if revised_request["source_score"]["fingerprint"] != revision_record["after_score_fingerprint"]:
        raise SystemExit("revised preview request fingerprint is stale")

    cold = _run(
        song, score, original_request,
        out / "original_cold.wav", cache, out / "original_cold_report.json",
    )
    warm = _run(
        song, score, original_request,
        out / "original_warm.wav", cache, out / "original_warm_report.json",
    )
    changed = _run(
        song, revised, revised_request,
        out / "revised_coda.wav", cache, out / "revised_coda_report.json",
    )

    cold_r = cold["report"]
    warm_r = warm["report"]
    changed_r = changed["report"]

    if (cold_r["cache"]["hits"], cold_r["cache"]["misses"]) != (0, 2):
        raise SystemExit(f"cold cache expectation failed: {cold_r['cache']}")
    if (warm_r["cache"]["hits"], warm_r["cache"]["misses"]) != (2, 0):
        raise SystemExit(f"warm cache expectation failed: {warm_r['cache']}")
    if cold_r["wav_sha256"] != warm_r["wav_sha256"]:
        raise SystemExit("identical warm preview is not byte deterministic")

    changed_tracks = _track_cache(changed_r)
    if changed_r["cache"]["hits"] != 1 or changed_r["cache"]["misses"] != 1:
        raise SystemExit(f"revision cache expectation failed: {changed_r['cache']}")
    if changed_tracks["violin-line"]["cache_hit"] is not True:
        raise SystemExit("unchanged violin stem was not reused")
    if changed_tracks["piano-foundation"]["cache_hit"] is not False:
        raise SystemExit("changed piano stem was incorrectly reused")
    if (
        _track_cache(cold_r)["violin-line"]["cache_key"]
        != changed_tracks["violin-line"]["cache_key"]
    ):
        raise SystemExit("violin cache identity changed under piano-only revision")
    if (
        _track_cache(cold_r)["piano-foundation"]["cache_key"]
        == changed_tracks["piano-foundation"]["cache_key"]
    ):
        raise SystemExit("piano cache identity did not change under piano revision")

    for label, result in (("cold", cold), ("warm", warm), ("revised", changed)):
        audio = np.asarray(result["audio"], dtype=np.float64)
        if not np.isfinite(audio).all():
            raise SystemExit(f"{label} preview contains non-finite samples")
        if result["report"]["preview_metrics"]["clipped_sample_ratio"] != 0.0:
            raise SystemExit(f"{label} preview clips")
        if abs(result["report"]["preview_metrics"]["duration_seconds"] - 10.0) > 1e-9:
            raise SystemExit(f"{label} preview duration is not 10 seconds")

    evidence = {
        "schema": "code-composer-cr05-preview-evidence/v1",
        "title": "Lantern Current — Bars 9-12 Incremental Preview",
        "renderer_epoch": cold_r["renderer_epoch"],
        "range": cold_r["range"],
        "sample_rate": cold_r["sample_rate"],
        "selected_tracks": cold_r["selected_tracks"],
        "original_score_fingerprint": cold_r["source_score_fingerprint"],
        "revised_score_fingerprint": changed_r["source_score_fingerprint"],
        "revision_plan_fingerprint": revision_record["revision_plan_fingerprint"],
        "cold": {
            "cache_hits": cold_r["cache"]["hits"],
            "cache_misses": cold_r["cache"]["misses"],
            "wav_sha256": cold_r["wav_sha256"],
            "metrics": cold_r["preview_metrics"],
        },
        "warm": {
            "cache_hits": warm_r["cache"]["hits"],
            "cache_misses": warm_r["cache"]["misses"],
            "wav_sha256": warm_r["wav_sha256"],
            "byte_identical_to_cold": warm_r["wav_sha256"] == cold_r["wav_sha256"],
        },
        "piano_only_revision": {
            "cache_hits": changed_r["cache"]["hits"],
            "cache_misses": changed_r["cache"]["misses"],
            "violin_cache_hit": changed_tracks["violin-line"]["cache_hit"],
            "piano_cache_hit": changed_tracks["piano-foundation"]["cache_hit"],
            "violin_cache_key_preserved": (
                _track_cache(cold_r)["violin-line"]["cache_key"]
                == changed_tracks["violin-line"]["cache_key"]
            ),
            "piano_cache_key_changed": (
                _track_cache(cold_r)["piano-foundation"]["cache_key"]
                != changed_tracks["piano-foundation"]["cache_key"]
            ),
            "wav_sha256": changed_r["wav_sha256"],
            "metrics": changed_r["preview_metrics"],
        },
        "authority": {
            "preview_is_final_render_authority": False,
            "stateful_stems_render_from_piece_start": True,
            "slice_happens_after_full_timeline_mix": True,
        },
    }
    (out / "evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "revised_score.json").write_text(
        json.dumps(revised, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "revision_record.json").write_text(
        json.dumps(revision_record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for src, name in (
        (SOURCE / "song.json", "song.json"),
        (SOURCE / "performance_score.json", "original_score.json"),
        (DOGFOOD / "original_request.json", "original_request.json"),
        (DOGFOOD / "revised_request.json", "revised_request.json"),
    ):
        shutil.copy2(src, out / name)

    files = sorted(p for p in out.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt")
    (out / "SHA256SUMS.txt").write_text(
        "".join(f"{_sha256(p)}  {p.name}\n" for p in files),
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
