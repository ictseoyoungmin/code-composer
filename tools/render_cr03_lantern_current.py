#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from code_composer.execution.artistic_render import render_song_score_to_files
from code_composer.execution.performance_score import performance_score_fingerprint
from code_composer.core.song import song_fingerprint


ROOT = Path(__file__).resolve().parents[1]
DOGFOOD = ROOT / "examples/cr03/lantern_current"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _spectral_ratio(audio: np.ndarray, sr: int, lo: float, hi: float) -> float:
    mono = np.mean(np.asarray(audio, dtype=np.float64), axis=1)
    if not len(mono):
        return 0.0
    win = np.hanning(len(mono))
    spec = np.fft.rfft(mono * win)
    power = np.abs(spec) ** 2
    freq = np.fft.rfftfreq(len(mono), 1.0 / sr)
    denom = float(np.sum(power[(freq >= 20.0) & (freq <= min(10000.0, sr * 0.49))]))
    if denom <= 1e-30:
        return 0.0
    return float(np.sum(power[(freq >= lo) & (freq <= hi)]) / denom)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    song_path = DOGFOOD / "song.json"
    score_path = DOGFOOD / "performance_score.json"
    song = json.loads(song_path.read_text(encoding="utf-8"))
    score = json.loads(score_path.read_text(encoding="utf-8"))

    if score["source_song"]["fingerprint"] != song_fingerprint(song):
        raise SystemExit("dogfood Performance Score does not match Song fingerprint")

    wav = out / "lantern_current.wav"
    plan_path = out / "execution_plan.json"
    render_ir_path = out / "render_ir.json"
    resolved_path = out / "resolved.json"
    analysis_path = out / "analysis.json"

    result = render_song_score_to_files(
        song,
        score,
        wav,
        plan_path=plan_path,
        render_ir_path=render_ir_path,
        resolved_path=resolved_path,
        analysis_path=analysis_path,
    )

    shutil.copy2(song_path, out / "song.json")
    shutil.copy2(score_path, out / "performance_score.json")
    shutil.copy2(DOGFOOD / "README.md", out / "README.md")

    audio = np.asarray(result["audio"], dtype=np.float64)
    sr = int(result["sr"])
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    clipped_ratio = float(np.mean(np.abs(audio) >= 1.0)) if len(audio) else 0.0

    violin_track = next(t for t in score["tracks"] if t["id"] == "violin-line")
    violin_notes = [e for e in violin_track["events"] if e["type"] == "note"]
    total_note_beats = sum(float(e["duration_beats"]) for e in violin_notes)
    high_beats = sum(float(e["duration_beats"]) for e in violin_notes if int(e["midi"]) >= 76)

    gaps = []
    for a, b in zip(violin_notes, violin_notes[1:]):
        gap = float(b["start_beat"]) - (float(a["start_beat"]) + float(a["duration_beats"]))
        if gap > 1e-9:
            gaps.append(round(gap, 6))

    report = result.get("violin_performance_report") or {}
    playability = report.get("playability") or {}

    evidence = {
        "schema": "code-composer-cr03-dogfood-evidence/v1",
        "title": score["meta"]["title"],
        "source_song_fingerprint": song_fingerprint(song),
        "execution_plan_fingerprint": result["execution_plan_fingerprint"],
        "performance_score_fingerprint": performance_score_fingerprint(score),
        "sample_rate": sr,
        "duration_seconds": round(len(audio) / sr, 6),
        "peak": peak,
        "clipped_sample_ratio": clipped_ratio,
        "high_band_ratio_4_10khz": _spectral_ratio(audio, sr, 4000.0, min(10000.0, sr * 0.49)),
        "violin": {
            "note_count": len(violin_notes),
            "midi_min": min(int(e["midi"]) for e in violin_notes),
            "midi_max": max(int(e["midi"]) for e in violin_notes),
            "high_register_fraction_midi_76_plus": high_beats / total_note_beats,
            "explicit_phrase_gaps_beats": gaps,
            "playability": playability,
            "all_notes_mechanically_realized": report.get("event_count") == len(violin_notes),
        },
        "piano": {
            "note_count": sum(1 for e in next(t for t in score["tracks"] if t["id"] == "piano-foundation")["events"] if e["type"] == "note"),
            "sustain_control_count": sum(1 for e in next(t for t in score["tracks"] if t["id"] == "piano-foundation")["events"] if e["type"] == "sustain_pedal"),
        },
        "analysis_metrics": result["metrics"],
        "closure_policy": {
            "engineering_metrics_are_evidence_not_aesthetic_scores": True,
            "perceptual_listening_required": True,
        },
    }

    if sr != 24000:
        raise SystemExit(f"expected 24 kHz dogfood, got {sr}")
    if not np.isfinite(audio).all():
        raise SystemExit("render contains non-finite samples")
    if clipped_ratio != 0.0:
        raise SystemExit(f"render clips: ratio={clipped_ratio}")
    if playability.get("classification") != "comfortable":
        raise SystemExit(f"violin playability is not comfortable: {playability}")
    if report.get("event_count") != len(violin_notes):
        raise SystemExit("not every violin note received physical realization")

    evidence_path = out / "evidence.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    files = sorted(p for p in out.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt")
    sums = out / "SHA256SUMS.txt"
    sums.write_text(
        "".join(f"{_sha256(p)}  {p.name}\n" for p in files),
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
