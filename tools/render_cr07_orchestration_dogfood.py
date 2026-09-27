#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from code_composer.core.song import song_fingerprint
from code_composer.execution.artistic_render import render_song_score_to_files
from code_composer.execution.performance_score import performance_score_fingerprint


ROOT = Path(__file__).resolve().parents[1]
DOGFOOD = ROOT / "examples/cr07"
CASES = ("copper_lines", "glass_courtyard", "blue_relay")
LEGACY_ROLE_WORDS = {"lead", "harmony", "bass", "drums", "pad", "fx"}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    evidence = {
        "schema": "code-composer-cr07-broader-orchestration-dogfood/v1",
        "cases": [],
        "contract": {
            "track_functions_are_authored": True,
            "unknown_families_require_explicit_preset_lock": True,
            "generic_fallback_added": False,
            "aesthetic_score": False,
            "perceptual_listening_required": True,
        },
    }

    known_default_families = {"piano", "violin", "bass", "drums"}

    for slug in CASES:
        source = DOGFOOD / slug
        song_path = source / "song.json"
        score_path = source / "performance_score.json"
        song = _load(song_path)
        score = _load(score_path)
        fp = song_fingerprint(song)
        if score["source_song"]["fingerprint"] != fp:
            raise SystemExit(f"{slug}: Performance Score fingerprint does not bind Song")

        functions = {t["id"]: t["function"] for t in song["tracks"]}
        if any(value in LEGACY_ROLE_WORDS for value in functions.values()):
            raise SystemExit(f"{slug}: fixed legacy role function leaked into CR07 fixture")

        for instrument in song["instruments"]:
            if instrument["family"] not in known_default_families:
                lock = instrument.get("render_lock") or {}
                if not lock.get("preset"):
                    raise SystemExit(
                        f"{slug}: unknown family {instrument['family']} lacks explicit preset lock"
                    )

        case_out = out / slug
        case_out.mkdir(parents=True, exist_ok=True)
        result = render_song_score_to_files(
            song,
            score,
            case_out / f"{slug}.wav",
            plan_path=case_out / "execution_plan.json",
            render_ir_path=case_out / "realized_ir.json",
            resolved_path=case_out / "resolved_ir.json",
            analysis_path=case_out / "audio_analysis.json",
        )

        plan_functions = {t["id"]: t["function"] for t in result["plan"]["tracks"]}
        if plan_functions != functions:
            raise SystemExit(f"{slug}: track functions changed during lowering")

        song_track_ids = [t["id"] for t in song["tracks"]]
        score_track_ids = [t["id"] for t in score["tracks"]]
        ir_track_ids = [t["id"] for t in result["render_ir"]["tracks"]]
        if song_track_ids != score_track_ids or song_track_ids != ir_track_ids:
            raise SystemExit(
                f"{slug}: exact track order/identity not preserved "
                f"song={song_track_ids} score={score_track_ids} ir={ir_track_ids}"
            )

        audio = np.asarray(result["audio"], dtype=np.float64)
        sr = int(result["sr"])
        peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
        clipped = float(np.mean(np.abs(audio) >= 1.0)) if len(audio) else 0.0
        if sr != 24000:
            raise SystemExit(f"{slug}: expected 24 kHz, got {sr}")
        if not np.isfinite(audio).all():
            raise SystemExit(f"{slug}: non-finite render")
        if clipped != 0.0:
            raise SystemExit(f"{slug}: clipping ratio {clipped}")

        shutil.copy2(song_path, case_out / "song.json")
        shutil.copy2(score_path, case_out / "performance_score.json")

        evidence["cases"].append({
            "slug": slug,
            "title": song["meta"]["title"],
            "song_fingerprint": fp,
            "performance_score_fingerprint": performance_score_fingerprint(score),
            "execution_plan_fingerprint": result["execution_plan_fingerprint"],
            "track_functions": functions,
            "track_ids_preserved": True,
            "sample_rate": sr,
            "duration_seconds": round(len(audio) / sr, 6),
            "peak": peak,
            "clipped_sample_ratio": clipped,
        })

    if len({c["song_fingerprint"] for c in evidence["cases"]}) != len(CASES):
        raise SystemExit("CR07 cases are not independent Song states")

    (out / "evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(DOGFOOD / "README.md", out / "README.md")

    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    (out / "SHA256SUMS.txt").write_text(
        "".join(f"{_sha256(p)}  {p.relative_to(out).as_posix()}\n" for p in files),
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
