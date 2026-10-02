#!/usr/bin/env python3
"""AG09 D3 public-domain groove-mute variant for Oh! Susanna."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import numpy as np

from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files
from code_composer.execution.performance_score import performance_score_fingerprint

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "tools" / "render_ag09_d3_public_domain_reference.py"
SPEC = importlib.util.spec_from_file_location("ag09_d3_pd_base", BASE_PATH)
BASE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BASE)

SR = BASE.SR
BPM = BASE.BPM
PRESET = BASE.PRESET

# One regular offbeat choke in every bar, plus the final offbeat at phrase ends.
REGULAR_MUTE_INDEX = 1
PHRASE_END_BARS = {3, 7, 11, 15}  # zero-based bars 4/8/12/16
PHRASE_END_MUTE_INDEX = 3


def build_groove_rhythm_events():
    events = []
    for bar in range(16):
        base = bar * 2.0
        for stroke_idx, offset in enumerate((0.0, 0.5, 1.0, 1.5)):
            direction = "down" if stroke_idx % 2 == 0 else "up"
            strong = stroke_idx in {0, 2}
            chord = BASE.chord_at(bar, offset)
            muted = (
                stroke_idx == REGULAR_MUTE_INDEX
                or (bar in PHRASE_END_BARS and stroke_idx == PHRASE_END_MUTE_INDEX)
            )
            stroke_id = f"m-b{bar+1:02d}s{stroke_idx}"
            cfg = BASE.strum_config(stroke_id, direction, strong, True)
            for ni, (midi, string, fret) in enumerate(BASE.VOICINGS[chord]):
                perf = {
                    "string": string,
                    "fret": fret,
                    "right_hand": {
                        "method": "pick",
                        "pluck_position": 0.12 if direction == "down" else 0.135,
                        "attack_angle_deg": cfg["attack_angle_deg"],
                        "strength": cfg["entry_strength"],
                    },
                    "strum": {**cfg, "state": "muted" if muted else "sounding"},
                }
                if muted:
                    perf["left_hand"] = {"technique": "dead_note"}
                events.append({
                    "id": f"{stroke_id}n{ni}",
                    "type": "note",
                    "start_beat": base + offset,
                    "duration_beats": 0.18 if muted else 0.42,
                    "midi": midi,
                    "velocity": 0.69 if strong else 0.50,
                    "instrument_performance": perf,
                })
    return events


def build_score(song):
    return {
        "format": "code-composer-performance-score/v1",
        "source_song": {"format": "code-composer-song/v1", "fingerprint": song_fingerprint(song)},
        "meta": {"title": "Oh! Susanna — D3 groove-mute"},
        "tracks": [
            {"id": "rhythm", "events": deepcopy(build_groove_rhythm_events())},
            {"id": "melody", "events": deepcopy(BASE.build_melody_events())},
        ],
        "render": {
            "sample_rate": SR,
            "tail_seconds": 2.4,
            "mix": {
                "tracks": [
                    {"track": "rhythm", "gain": 0.30, "pan": -0.12, "reverb_send": 0.0},
                    {"track": "melody", "gain": 0.34, "pan": 0.10, "reverb_send": 0.0},
                ],
                "music_bus_gain": 1.0,
                "room_return_gain": 0.0,
                "master_gain": 0.78,
            },
        },
    }


def _sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _rms(x):
    x = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(x * x))) if x.size else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    song = BASE.build_song()
    score = build_score(song)
    rhythm = build_groove_rhythm_events()
    melody = BASE.build_melody_events()

    muted_stroke_ids = {
        e["instrument_performance"]["strum"]["stroke_id"]
        for e in rhythm
        if e["instrument_performance"]["strum"]["state"] == "muted"
    }
    all_stroke_ids = {
        e["instrument_performance"]["strum"]["stroke_id"]
        for e in rhythm
    }
    if len(all_stroke_ids) != 64:
        raise SystemExit(f"expected 64 strum strokes, got {len(all_stroke_ids)}")
    if len(muted_stroke_ids) != 20:
        raise SystemExit(f"expected 20 muted strokes, got {len(muted_stroke_ids)}")

    wav = out / "01_oh_susanna_d3_groove_mute.wav"
    repeat = out / "02_oh_susanna_d3_groove_mute_repeat.wav"
    result = render_song_score_to_files(
        song,
        score,
        wav,
        plan_path=out / "execution_plan.json",
        render_ir_path=out / "render_ir.json",
        resolved_path=out / "resolved_ir.json",
        analysis_path=out / "audio_analysis.json",
    )
    again = render_song_score_to_files(song, score, repeat)

    a = np.asarray(result["audio"], dtype=np.float64)
    b = np.asarray(again["audio"], dtype=np.float64)
    if not np.array_equal(a, b):
        raise SystemExit("groove-mute render is not deterministic")
    if not np.isfinite(a).all():
        raise SystemExit("groove-mute render contains non-finite samples")

    peak = float(np.max(np.abs(a))) if a.size else 0.0
    clipped = float(np.mean(np.abs(a) >= 1.0)) if a.size else 0.0
    if clipped != 0.0 or peak >= 0.98:
        raise SystemExit(f"unsafe output peak={peak} clipped={clipped}")

    authored_count = len(rhythm) + len(melody)
    realized_count = sum(len(t["events"]) for t in result["render_ir"]["tracks"])
    if realized_count != authored_count:
        raise SystemExit(f"event authority changed {authored_count} -> {realized_count}")

    metrics = {
        "schema": "code-composer-ag09-d3-public-domain-groove-mute/v1",
        "title": "Oh! Susanna — D3 groove-mute",
        "revision": "AG09-D3-PD-MUTE-R0",
        "public_domain_provenance": BASE.PUBLIC_DOMAIN_PROVENANCE,
        "sample_rate": SR,
        "bpm": BPM,
        "bars": 16,
        "melody_event_count": len(melody),
        "rhythm_event_count": len(rhythm),
        "strum_stroke_count": len(all_stroke_ids),
        "muted_stroke_count": len(muted_stroke_ids),
        "mute_pattern": {
            "regular": "stroke_index_1_each_bar",
            "phrase_end_extra": "stroke_index_3_on_bars_4_8_12_16",
        },
        "authored_event_count": authored_count,
        "render_ir_event_count": realized_count,
        "harmonic_certificate": BASE.harmonic_certificate(),
        "deterministic": True,
        "finite": True,
        "peak": peak,
        "rms": _rms(a),
        "clipped_sample_ratio": clipped,
        "sha256": _sha256(wav),
        "sha256_repeat": _sha256(repeat),
        "score_fingerprint": performance_score_fingerprint(score),
        "automatic_aesthetic_score": False,
        "human_listening_required": True,
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    (out / "README.md").write_text(
        "# Oh! Susanna — D3 groove-mute reference\n\n"
        "Same public-domain melody/harmony as the clean and phrase-choke variants. "
        "The rhythm guitar uses one regular offbeat dead-note mute in every bar, "
        "plus an extra phrase-ending choke on bars 4, 8, 12, and 16. "
        "This yields 20 muted strokes out of 64 total strum strokes.\n",
        encoding="utf-8",
    )
    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    (out / "SHA256SUMS.txt").write_text(
        "".join(f"{_sha256(p)}  {p.relative_to(out).as_posix()}\n" for p in files),
        encoding="utf-8",
    )
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
