#!/usr/bin/env python3
"""Production renderer for Cedar Rain, Afterlight.

Renders each through-composed section with the same v1.19 stateful acoustic-guitar
engine, then overlap-adds only the engine-generated section tails at exact musical
section boundaries. No resampling, normalization, EQ, compression, synthetic
reverb, samples, or non-guitar audio are introduced.
"""
from __future__ import annotations

import argparse, hashlib, json
from copy import deepcopy
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files
from code_composer.execution.performance_score import performance_score_fingerprint

import compose_cedar_rain_afterlight as comp


def _song(section_id: str, bars: int, seed: int):
    return {
        "format": "code-composer-song/v1",
        "meta": {
            "title": f"Cedar Rain, Afterlight — {section_id}",
            "global_seed": int(seed),
            "revision": "SOLO-ACOUSTIC-PROD-R2",
        },
        "transport": {"bpm": comp.BPM, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
        "tonal": {"root": "E", "scale": "natural_minor"},
        "sections": [{"id": section_id, "bars": int(bars), "name": section_id.title()}],
        "instruments": [{
            "id": "guitar", "family": "acoustic_guitar", "variant": "steel-string",
            "render_lock": {"preset": comp.PRESET, "preset_version": "1.0.0"},
        }],
        "tracks": [{"id": "guitar", "function": "solo-acoustic-guitar", "instrument": "guitar"}],
        "materials": [{"id": "through-composed", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": f"{section_id}-part", "section": section_id, "track": "guitar", "material": "through-composed"}],
    }


def _local_events(all_events, start_bar: int, bars: int):
    lo = float(start_bar * 4)
    hi = float((start_bar + bars) * 4)
    out = []
    for src in all_events:
        st = float(src["start_beat"])
        if lo <= st < hi:
            e = deepcopy(src)
            e["start_beat"] = st - lo
            out.append(e)
    return out


def _master_gain_for_rate(sr: int) -> float:
    # Fixed production headroom, not measured normalization or limiting.
    # The physical renderer has a higher peak response at 48 kHz than 24 kHz;
    # retain the exact performance and lower only the final linear bus gain.
    return 0.56 if int(sr) >= 44100 else 0.80


def _score(song, events, sr: int):
    return {
        "format": "code-composer-performance-score/v1",
        "source_song": {"format": "code-composer-song/v1", "fingerprint": song_fingerprint(song)},
        "meta": {"title": song["meta"]["title"]},
        "tracks": [{"id": "guitar", "events": deepcopy(events)}],
        "render": {
            "sample_rate": int(sr),
            "tail_seconds": 3.2,
            "mix": {
                "tracks": [{"track": "guitar", "gain": 0.43, "pan": 0.0, "reverb_send": 0.0}],
                "music_bus_gain": 1.0,
                "room_return_gain": 0.0,
                "master_gain": _master_gain_for_rate(sr),
            },
        },
    }


def _sha(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _rms(x):
    a = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(a * a))) if a.size else 0.0


def _render_one(out: Path, section_id: str, bars: int, start_bar: int, sr: int, seed: int, *, suffix=""):
    events = _local_events(comp.build_events(), start_bar, bars)
    song = _song(section_id, bars, seed)
    score = _score(song, events, sr)
    stem = f"section_{start_bar+1:02d}_{section_id}{suffix}"
    wav = out / f"{stem}.wav"
    result = render_song_score_to_files(
        song, score, wav,
        plan_path=out / f"{stem}_execution_plan.json",
        render_ir_path=out / f"{stem}_render_ir.json",
    )
    audio = np.asarray(result["audio"], dtype=np.float64)
    realized = result["render_ir"]["tracks"][0]["events"]
    if int(result["sr"]) != int(sr):
        raise SystemExit(f"{section_id}: sample-rate mismatch")
    if len(realized) != len(events):
        raise SystemExit(f"{section_id}: event authority {len(events)}->{len(realized)}")
    if not np.isfinite(audio).all():
        raise SystemExit(f"{section_id}: non-finite")
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    clipped = float(np.mean(np.abs(audio) >= 1.0)) if audio.size else 0.0
    if peak >= 0.98 or clipped != 0.0:
        raise SystemExit(f"{section_id}: unsafe peak/clipping {peak}/{clipped}")
    return {
        "id": section_id,
        "bars": bars,
        "start_bar": start_bar,
        "event_count": len(events),
        "peak": peak,
        "rms": _rms(audio),
        "wav": wav,
        "audio": audio,
        "wav_sha256": _sha(wav),
        "song_fingerprint": song_fingerprint(song),
        "performance_score_fingerprint": performance_score_fingerprint(score),
    }


def _write_float_wav(path: Path, sr: int, audio):
    x = np.asarray(audio, dtype=np.float64)
    if not np.isfinite(x).all():
        raise SystemExit("master contains non-finite samples")
    wavfile.write(path, int(sr), np.asarray(x, dtype=np.float32))


def _bar_signatures(events):
    return comp.bar_sigs(events)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--sample-rate", type=int, default=48000)
    ap.add_argument("--determinism-check", action="store_true")
    args = ap.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    sr = int(args.sample_rate)
    all_events = comp.build_events()

    sigs = _bar_signatures(all_events)
    unique_bars = len(set(sigs))
    windows = [tuple(sigs[i:i+4]) for i in range(comp.TOTAL_BARS - 3)]
    if unique_bars < 50:
        raise SystemExit(f"simple repetition gate: {unique_bars}/60 unique bars")
    if len(windows) != len(set(windows)):
        raise SystemExit("identical four-bar window detected")

    section_results = []
    start_bar = 0
    for idx, (section_id, bars) in enumerate(comp.SECTIONS):
        section_results.append(_render_one(out, section_id, bars, start_bar, sr, 1919060 + idx))
        start_bar += bars

    deterministic = None
    det_section = None
    if args.determinism_check:
        start_bar = comp.START["development"]
        bars = dict(comp.SECTIONS)["development"]
        a = next(x for x in section_results if x["id"] == "development")
        b = _render_one(out, "development", bars, start_bar, sr, 1919062, suffix="_repeat")
        deterministic = bool(np.array_equal(a["audio"], b["audio"]))
        if not deterministic:
            raise SystemExit("development section is not sample-exact deterministic")
        det_section = "development"

    beat_s = 60.0 / comp.BPM
    bar_samples = 4.0 * beat_s * sr
    nominal_samples = int(round(comp.TOTAL_BARS * bar_samples))
    final_len = nominal_samples + int(round(3.2 * sr))
    master = np.zeros((final_len, 2), dtype=np.float64)

    for r in section_results:
        start = int(round(r["start_bar"] * bar_samples))
        end = min(final_len, start + len(r["audio"]))
        master[start:end] += r["audio"][: end - start]

    peak = float(np.max(np.abs(master))) if master.size else 0.0
    clipped = float(np.mean(np.abs(master) >= 1.0)) if master.size else 0.0
    if peak >= 0.98 or clipped != 0.0:
        raise SystemExit(f"assembled master unsafe peak/clipping {peak}/{clipped}")

    duration = len(master) / sr
    if not 176.0 <= duration <= 181.0:
        raise SystemExit(f"duration {duration} outside production target")

    master_path = out / f"01_cedar_rain_afterlight_master_{sr//1000}k_float32.wav"
    _write_float_wav(master_path, sr, master)

    cut_files = []
    cursor = 0
    for i, (section_id, bars) in enumerate(comp.SECTIONS, 1):
        a = int(round(cursor * bar_samples))
        z = int(round((cursor + bars) * bar_samples))
        p = out / f"{i+1:02d}_{section_id}.wav"
        _write_float_wav(p, sr, master[a:z])
        cut_files.append(p.name)
        cursor += bars

    note_events = [e for e in all_events if e["type"] == "note"]
    action_events = [e for e in all_events if e["type"] == "instrument_action"]
    methods = {}
    left = {}
    strum_notes = 0
    actions = {}
    for e in note_events:
        perf = e["instrument_performance"]
        method = perf["right_hand"]["method"]
        methods[method] = methods.get(method, 0) + 1
        lh = (perf.get("left_hand") or {}).get("technique")
        if lh:
            left[lh] = left.get(lh, 0) + 1
        if perf.get("strum"):
            strum_notes += 1
    for e in action_events:
        actions[e["action"]] = actions.get(e["action"], 0) + 1
    if not {"finger", "thumb", "nail", "pick"}.issubset(methods):
        raise SystemExit(f"right-hand coverage incomplete: {methods}")
    if strum_notes < 100 or len(action_events) < 20:
        raise SystemExit(f"technique coverage incomplete: strum={strum_notes} actions={len(action_events)}")

    report = {
        "schema": "code-composer-production-solo-acoustic-section-tail/v1",
        "title": "Cedar Rain, Afterlight",
        "revision": "SOLO-ACOUSTIC-PROD-R2",
        "sample_rate": sr,
        "bpm": comp.BPM,
        "bars": comp.TOTAL_BARS,
        "duration_seconds": duration,
        "instrument_family": "acoustic_guitar",
        "preset": comp.PRESET,
        "other_instruments": 0,
        "section_tail_overlap_only": True,
        "post_normalization": False,
        "post_eq": False,
        "post_compression": False,
        "synthetic_reverb": False,
        "fixed_master_gain": _master_gain_for_rate(sr),
        "peak": peak,
        "rms": _rms(master),
        "clipped_sample_ratio": clipped,
        "unique_bar_signatures": unique_bars,
        "identical_four_bar_windows": 0,
        "authored_event_count": len(all_events),
        "pitched_note_count": len(note_events),
        "instrument_action_count": len(action_events),
        "right_hand_method_counts": methods,
        "left_hand_technique_counts": left,
        "strum_note_count": strum_notes,
        "action_counts": actions,
        "sections": [{k: v for k, v in r.items() if k not in {"audio", "wav"}} for r in section_results],
        "deterministic_exact": deterministic,
        "determinism_section": det_section,
        "master_wav_sha256": _sha(master_path),
        "harmonic_path": list(comp.HARMONY),
        "inspiration": comp.INSPIRATION,
        "listening_cuts": cut_files,
        "human_listening_required": True,
        "automatic_aesthetic_score": False,
    }
    (out / "metrics.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "PROVENANCE.md").write_text(
        "# Cedar Rain, Afterlight — provenance\n\n"
        "Original Code Composer composition for steel-string acoustic guitar only.\n\n"
        "## External score consulted\n"
        "- Mauro Giuliani — *12 Divertimenti per chitarra, Op.40*\n"
        "- IMSLP 2026 typeset by Marieh, marked Creative Commons Zero 1.0\n"
        "- High-level idiom/structure inspiration only: alternating bass, voice-leading, cadential variation.\n"
        "- No melody, bar, chord sequence, voicing sequence, or arrangement passage was copied.\n\n"
        "## Production render\n"
        "- Every audible source is the same Code Composer v1.19 stateful steel-string acoustic-guitar engine.\n"
        "- Sections are captured separately for tractable long-form rendering and joined only by overlap-adding their engine-generated natural tails at exact section boundaries.\n"
        "- 48 kHz uses a fixed 0.56 linear master gain for deterministic headroom; this is not measured normalization or limiting.\n"
        "- No samples, other instruments, resampling, normalization, EQ, compression, or synthetic reverb are added.\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
