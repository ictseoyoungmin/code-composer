#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from code_composer.execution import (
    performance_score_fingerprint,
    render_revision_comparison_to_dir,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/cr03/lantern_current"
DOGFOOD = ROOT / "examples/cr04/lantern_current_coda"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _track(score, track_id):
    return next(t for t in score["tracks"] if t["id"] == track_id)


def _events(score, track_id):
    return {e["id"]: e for e in _track(score, track_id)["events"]}


def _window_rms(audio, sr, start_s, end_s):
    a = max(0, int(round(start_s * sr)))
    b = min(len(audio), int(round(end_s * sr)))
    if b <= a:
        return 0.0
    x = np.asarray(audio[a:b], dtype=np.float64)
    return float(np.sqrt(np.mean(x * x)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    song = json.loads((SOURCE / "song.json").read_text(encoding="utf-8"))
    score = json.loads((SOURCE / "performance_score.json").read_text(encoding="utf-8"))
    plan = json.loads((DOGFOOD / "revision_plan.json").read_text(encoding="utf-8"))

    result = render_revision_comparison_to_dir(song, score, plan, out)
    after = result["after_score"]
    record = result["revision_record"]
    comparison = result["comparison"]

    before_violin = _track(score, "violin-line")
    after_violin = _track(after, "violin-line")
    if before_violin != after_violin:
        raise SystemExit("CR04 targeted revision changed the preserved violin track")

    before_piano = _events(score, "piano-foundation")
    after_piano = _events(after, "piano-foundation")
    for eid, event in before_piano.items():
        if "-bass" in eid or eid.startswith("pedal-"):
            if after_piano.get(eid) != event:
                raise SystemExit(f"CR04 targeted revision changed preserved piano event {eid}")

    expected_changed = {
        "p-b11-u1", "p-b11-u2", "p-b11-u3",
        "p-b12-u1", "p-b12-u2", "p-b12-u3",
    }
    if set(record["changed_event_ids"]) != expected_changed:
        raise SystemExit(f"unexpected changed event set: {record['changed_event_ids']}")
    if record["changed_mix_tracks"] != ["piano-foundation"]:
        raise SystemExit("unexpected changed mix tracks")

    for label, render in (("before", result["before_render"]), ("after", result["after_render"])):
        audio = np.asarray(render["audio"], dtype=np.float64)
        if not np.isfinite(audio).all():
            raise SystemExit(f"{label} render contains non-finite samples")
        if float(np.mean(np.abs(audio) >= 1.0)) != 0.0:
            raise SystemExit(f"{label} render clips")

    bpm = float(song["transport"]["bpm"])
    beat_s = 60.0 / bpm
    coda_start_s = 30.0 * beat_s
    coda_end_s = 36.0 * beat_s
    before_audio = np.asarray(result["before_render"]["audio"], dtype=np.float64)
    after_audio = np.asarray(result["after_render"]["audio"], dtype=np.float64)
    sr = int(result["before_render"]["sr"])

    evidence = {
        "schema": "code-composer-cr04-revision-evidence/v1",
        "title": "Lantern Current — Coda Breath Revision",
        "source_score_fingerprint": performance_score_fingerprint(score),
        "revision_plan_fingerprint": comparison["revision_plan_fingerprint"],
        "after_score_fingerprint": comparison["after_score_fingerprint"],
        "changed_event_ids": record["changed_event_ids"],
        "changed_mix_tracks": record["changed_mix_tracks"],
        "preserved": {
            "violin_track_exact": True,
            "piano_bass_exact": True,
            "piano_pedal_controls_exact": True,
            "source_song_fingerprint": record["source_song_fingerprint"],
        },
        "before": {
            "wav_sha256": comparison["before"]["wav_sha256"],
            "metrics": comparison["before"]["metrics"],
            "coda_rms": _window_rms(before_audio, sr, coda_start_s, coda_end_s),
        },
        "after": {
            "wav_sha256": comparison["after"]["wav_sha256"],
            "metrics": comparison["after"]["metrics"],
            "coda_rms": _window_rms(after_audio, sr, coda_start_s, coda_end_s),
        },
        "closure_policy": {
            "metric_deltas_are_evidence_not_aesthetic_scores": True,
            "perceptual_listening_required": True,
        },
    }
    (out / "evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    shutil.copy2(SOURCE / "song.json", out / "song.json")
    shutil.copy2(SOURCE / "performance_score.json", out / "source_performance_score.json")
    shutil.copy2(DOGFOOD / "README.md", out / "README.md")

    files = sorted(p for p in out.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt")
    (out / "SHA256SUMS.txt").write_text(
        "".join(f"{_sha256(p)}  {p.name}\n" for p in files),
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
