"""CR06 evidence-first QA for Composer-first Song / Performance Score.

Hard integrity checks are binary and limited to correctness/integrity. Musical evidence
is descriptive only. This module intentionally has no aesthetic score, "good music"
verdict, or automatic revision authority.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from ..analysis.analysis import analyze_audio
from .artistic_render import render_song_score_to_files
from .performance_score import performance_score_fingerprint, validate_performance_score
from .plan import execution_plan_fingerprint


QA_REQUEST_FORMAT = "code-composer-qa-request/v1"
QA_REPORT_FORMAT = "code-composer-qa-report/v1"
QA_COMPARISON_FORMAT = "code-composer-qa-comparison/v1"


class QaValidationError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise QaValidationError(f"{path}: {message}")


def _strict(value: Any, path: str, *, required=(), optional=()) -> dict:
    if not isinstance(value, dict):
        _fail(path, "must be an object")
    missing = set(required) - set(value)
    if missing:
        _fail(path, f"missing field(s): {sorted(missing)}")
    unknown = set(value) - set(required) - set(optional)
    if unknown:
        _fail(path, f"unknown field(s): {sorted(unknown)}")
    return value


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(path, "must be a non-empty string")
    return value


def _sha256(value: Any, path: str) -> str:
    value = _string(value, path)
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        _fail(path, "must be lowercase sha256 hex")
    return value


def _number(value: Any, path: str, lo=None, hi=None) -> float:
    if isinstance(value, bool):
        _fail(path, "must be numeric")
    try:
        out = float(value)
    except Exception as exc:
        raise QaValidationError(f"{path}: must be numeric") from exc
    if not math.isfinite(out):
        _fail(path, "must be finite")
    if lo is not None and out < lo:
        _fail(path, f"must be >= {lo}")
    if hi is not None and out > hi:
        _fail(path, f"must be <= {hi}")
    return out


def _integer(value: Any, path: str, lo=None, hi=None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(path, "must be an integer")
    if lo is not None and value < lo:
        _fail(path, f"must be >= {lo}")
    if hi is not None and value > hi:
        _fail(path, f"must be <= {hi}")
    return int(value)


def validate_qa_request(request: dict[str, Any]) -> None:
    _strict(
        request,
        "request",
        required={"format", "source_score", "hard_policy", "evidence"},
    )
    if request["format"] != QA_REQUEST_FORMAT:
        _fail("format", f"must equal {QA_REQUEST_FORMAT!r}")

    source = _strict(
        request["source_score"],
        "source_score",
        required={"format", "fingerprint"},
    )
    if source["format"] != "code-composer-performance-score/v1":
        _fail("source_score.format", "must be code-composer-performance-score/v1")
    _sha256(source["fingerprint"], "source_score.fingerprint")

    policy = _strict(
        request["hard_policy"],
        "hard_policy",
        required={
            "max_clipped_sample_ratio",
            "require_exact_note_authority",
            "require_provenance",
            "require_mechanical_realization",
        },
    )
    _number(
        policy["max_clipped_sample_ratio"],
        "hard_policy.max_clipped_sample_ratio",
        0.0,
        1.0,
    )
    for key in (
        "require_exact_note_authority",
        "require_provenance",
        "require_mechanical_realization",
    ):
        if not isinstance(policy[key], bool):
            _fail(f"hard_policy.{key}", "must be boolean")

    evidence = _strict(
        request["evidence"],
        "evidence",
        required={"focus", "parameters"},
    )
    focus = evidence["focus"]
    allowed = {
        "dynamics",
        "spectrum",
        "register",
        "phrase_continuity",
        "repetition",
        "voice_leading",
        "tension_release",
        "masking",
    }
    if not isinstance(focus, list) or not focus:
        _fail("evidence.focus", "must be a non-empty array")
    for i, item in enumerate(focus):
        if item not in allowed:
            _fail(f"evidence.focus[{i}]", f"unsupported focus {item!r}")
    if len(set(focus)) != len(focus):
        _fail("evidence.focus", "must be unique")

    params = _strict(
        evidence["parameters"],
        "evidence.parameters",
        required={
            "rms_window_ms",
            "spectrum_fft_size",
            "high_register_midi",
            "close_register_semitones",
        },
    )
    _number(params["rms_window_ms"], "evidence.parameters.rms_window_ms", 10.0, 5000.0)
    fft_size = _integer(
        params["spectrum_fft_size"],
        "evidence.parameters.spectrum_fft_size",
        256,
        65536,
    )
    if fft_size & (fft_size - 1):
        _fail("evidence.parameters.spectrum_fft_size", "must be a power of two")
    _integer(params["high_register_midi"], "evidence.parameters.high_register_midi", 0, 127)
    _integer(
        params["close_register_semitones"],
        "evidence.parameters.close_register_semitones",
        0,
        24,
    )


def canonical_qa_request_json(request: dict[str, Any]) -> str:
    validate_qa_request(request)
    return json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def qa_request_fingerprint(request: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_qa_request_json(request).encode("utf-8")).hexdigest()


def qa_target_fingerprint(request: dict[str, Any]) -> str:
    validate_qa_request(request)
    target = {
        "hard_policy": request["hard_policy"],
        "evidence": request["evidence"],
    }
    payload = json.dumps(target, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _score_note_signature(score: dict) -> dict[str, list[tuple[float, float, int]]]:
    return {
        track["id"]: [
            (float(e["start_beat"]), float(e["duration_beats"]), int(e["midi"]))
            for e in track["events"]
            if e["type"] == "note"
        ]
        for track in score["tracks"]
    }


def _ir_note_signature(ir: dict) -> dict[str, list[tuple[float, float, int]]]:
    return {
        track["id"]: [
            (float(e["start_beat"]), float(e["duration_beats"]), int(e["midi"]))
            for e in track.get("events", [])
            if "midi" in e
        ]
        for track in ir.get("tracks", [])
    }


def _check(check_id: str, passed: bool, *, observed=None, expected=None, message="") -> dict:
    return {
        "id": check_id,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
        "message": message,
    }


def _integrity(score: dict, request: dict, render_result: dict) -> dict:
    audio = np.asarray(render_result["audio"], dtype=np.float64)
    policy = request["hard_policy"]
    score_fp = performance_score_fingerprint(score)
    checks = []

    finite = bool(np.isfinite(audio).all())
    checks.append(_check(
        "audio_finite", finite,
        observed=finite, expected=True,
        message="Rendered audio must contain only finite samples.",
    ))

    clipped = float(np.mean(np.abs(audio) >= 1.0)) if len(audio) else 0.0
    max_clip = float(policy["max_clipped_sample_ratio"])
    checks.append(_check(
        "clipping_policy", clipped <= max_clip + 1e-15,
        observed=clipped, expected={"max": max_clip},
        message="Clipped-sample ratio must remain within the explicit hard policy.",
    ))

    source_bound = request["source_score"]["fingerprint"] == score_fp
    checks.append(_check(
        "source_score_binding", source_bound,
        observed=score_fp, expected=request["source_score"]["fingerprint"],
        message="QA request must bind the exact Performance Score.",
    ))

    plan = render_result["plan"]
    plan_fp = execution_plan_fingerprint(plan)
    provenance = (
        render_result.get("render_ir", {})
        .get("meta", {})
        .get("composer_provenance", {})
    )
    provenance_ok = (
        render_result.get("performance_score_fingerprint") == score_fp
        and render_result.get("execution_plan_fingerprint") == plan_fp
        and provenance.get("performance_score_fingerprint") == score_fp
        and provenance.get("execution_plan_fingerprint") == plan_fp
        and provenance.get("song_fingerprint") == score["source_song"]["fingerprint"]
        and plan["source_song"]["fingerprint"] == score["source_song"]["fingerprint"]
    )
    checks.append(_check(
        "provenance_chain",
        provenance_ok if policy["require_provenance"] else True,
        observed={
            "render_score": render_result.get("performance_score_fingerprint"),
            "render_plan": render_result.get("execution_plan_fingerprint"),
            "ir": deepcopy(provenance),
        },
        expected={
            "score": score_fp,
            "plan": plan_fp,
            "song": score["source_song"]["fingerprint"],
        },
        message="Song → Score → Execution Plan → realized IR provenance must remain coherent.",
    ))

    exact_notes = _score_note_signature(score) == _ir_note_signature(render_result["render_ir"])
    checks.append(_check(
        "exact_note_authority",
        exact_notes if policy["require_exact_note_authority"] else True,
        observed=exact_notes,
        expected=True,
        message="Physical realization must not change authored pitch/timing/duration.",
    ))

    violin_tracks = []
    plan_instruments = {x["id"]: x for x in plan["instruments"]}
    plan_tracks = {x["id"]: x for x in plan["tracks"]}
    for track in score["tracks"]:
        pt = plan_tracks[track["id"]]
        family = plan_instruments[pt["instrument"]]["family"]
        if family == "violin":
            violin_tracks.append(track)
    mech_ok = True
    mech_observed = {"violin_tracks": len(violin_tracks), "reports": []}
    if violin_tracks:
        report = render_result.get("violin_performance_report")
        if not isinstance(report, dict):
            mech_ok = False
            mech_observed["reports"].append({"missing": True})
        else:
            expected_notes = sum(
                1 for t in violin_tracks for e in t["events"] if e["type"] == "note"
            )
            classification = (report.get("playability") or {}).get("classification")
            event_count = int(report.get("event_count", -1))
            row = {
                "track_id": report.get("track_id"),
                "event_count": event_count,
                "expected_note_count": expected_notes,
                "classification": classification,
                "warning_count": int((report.get("playability") or {}).get("warning_count", 0)),
            }
            mech_observed["reports"].append(row)
            mech_ok = (
                event_count == expected_notes
                and classification not in {None, "impractical"}
            )
    checks.append(_check(
        "mechanical_realization",
        mech_ok if policy["require_mechanical_realization"] else True,
        observed=mech_observed,
        expected="all pitched instrument events mechanically realized; no impossible state",
        message="Mechanical realization must cover authored notes without impossible instrument state.",
    ))

    failed = [x["id"] for x in checks if not x["passed"]]
    return {
        "status": "PASS" if not failed else "FAIL",
        "failure_count": len(failed),
        "failed_checks": failed,
        "checks": checks,
    }


def _window_rms(audio: np.ndarray, sr: int, window_ms: float) -> dict:
    if len(audio) == 0:
        return {
            "window_ms": float(window_ms),
            "window_count": 0,
            "rms_db_min": -240.0,
            "rms_db_p10": -240.0,
            "rms_db_median": -240.0,
            "rms_db_p90": -240.0,
            "rms_db_max": -240.0,
            "p90_minus_p10_db": 0.0,
        }
    mono = np.mean(audio, axis=1)
    size = max(1, int(round(float(window_ms) * sr / 1000.0)))
    values = []
    for start in range(0, len(mono), size):
        x = mono[start:start + size]
        if len(x):
            rms = float(np.sqrt(np.mean(x * x)))
            values.append(20.0 * math.log10(max(rms, 1e-12)))
    a = np.asarray(values, dtype=np.float64)
    return {
        "window_ms": float(window_ms),
        "window_count": int(len(a)),
        "rms_db_min": float(np.min(a)),
        "rms_db_p10": float(np.percentile(a, 10)),
        "rms_db_median": float(np.median(a)),
        "rms_db_p90": float(np.percentile(a, 90)),
        "rms_db_max": float(np.max(a)),
        "p90_minus_p10_db": float(np.percentile(a, 90) - np.percentile(a, 10)),
    }


def _spectrum(audio: np.ndarray, sr: int, fft_size: int) -> dict:
    if len(audio) == 0:
        return {"fft_size": int(fft_size), "spectral_centroid_hz": 0.0, "band_energy_fraction": {}}
    mono = np.mean(audio, axis=1)
    hop = max(1, fft_size // 2)
    accum = np.zeros(fft_size // 2 + 1, dtype=np.float64)
    count = 0
    window = np.hanning(fft_size)
    if len(mono) < fft_size:
        padded = np.zeros(fft_size, dtype=np.float64)
        padded[:len(mono)] = mono
        frames = [padded]
    else:
        frames = [mono[i:i+fft_size] for i in range(0, len(mono)-fft_size+1, hop)]
    for frame in frames:
        mag = np.abs(np.fft.rfft(frame * window)) ** 2
        accum += mag
        count += 1
    power = accum / max(1, count)
    freqs = np.fft.rfftfreq(fft_size, 1.0 / sr)
    total = float(np.sum(power))
    centroid = float(np.sum(freqs * power) / total) if total > 0 else 0.0
    bands = {
        "sub_20_80": (20.0, 80.0),
        "low_80_250": (80.0, 250.0),
        "low_mid_250_800": (250.0, 800.0),
        "mid_800_2500": (800.0, 2500.0),
        "presence_2500_6000": (2500.0, 6000.0),
        "air_6000_nyquist": (6000.0, sr / 2.0 + 1.0),
    }
    fractions = {}
    for name, (lo, hi) in bands.items():
        mask = (freqs >= lo) & (freqs < hi)
        fractions[name] = float(np.sum(power[mask]) / total) if total > 0 else 0.0
    return {
        "fft_size": int(fft_size),
        "frame_count": int(count),
        "spectral_centroid_hz": centroid,
        "band_energy_fraction": fractions,
    }


def _note_tracks(score: dict) -> dict[str, list[dict]]:
    return {
        track["id"]: [e for e in track["events"] if e["type"] == "note"]
        for track in score["tracks"]
    }


def _register_evidence(score: dict, high_midi: int) -> dict:
    out = {}
    for track_id, events in _note_tracks(score).items():
        if not events:
            out[track_id] = {"note_count": 0}
            continue
        durations = np.asarray([float(e["duration_beats"]) for e in events], dtype=np.float64)
        midis = np.asarray([int(e["midi"]) for e in events], dtype=np.float64)
        total = float(np.sum(durations))
        high = float(np.sum(durations[midis >= high_midi])) if total > 0 else 0.0
        out[track_id] = {
            "note_count": len(events),
            "midi_min": int(np.min(midis)),
            "midi_max": int(np.max(midis)),
            "midi_median": float(np.median(midis)),
            "duration_weighted_mean_midi": float(np.sum(midis * durations) / total) if total > 0 else 0.0,
            "high_register_midi": int(high_midi),
            "high_register_duration_fraction": float(high / total) if total > 0 else 0.0,
        }
    return out


def _phrase_continuity(score: dict) -> dict:
    out = {}
    for track_id, events in _note_tracks(score).items():
        ordered = sorted(events, key=lambda e: (float(e["start_beat"]), int(e["midi"])))
        gaps = []
        overlaps = []
        for a, b in zip(ordered, ordered[1:]):
            gap = float(b["start_beat"]) - (
                float(a["start_beat"]) + float(a["duration_beats"])
            )
            if gap > 1e-9:
                gaps.append(gap)
            elif gap < -1e-9:
                overlaps.append(-gap)
        out[track_id] = {
            "positive_gap_count": len(gaps),
            "positive_gaps_beats": [round(x, 6) for x in gaps],
            "max_gap_beats": float(max(gaps)) if gaps else 0.0,
            "mean_gap_beats": float(np.mean(gaps)) if gaps else 0.0,
            "overlap_count": len(overlaps),
            "max_overlap_beats": float(max(overlaps)) if overlaps else 0.0,
        }
    return out


def _repetition(score: dict) -> dict:
    out = {}
    for track_id, events in _note_tracks(score).items():
        ordered = sorted(events, key=lambda e: float(e["start_beat"]))
        pitches = [int(e["midi"]) for e in ordered]
        intervals = [b-a for a, b in zip(pitches, pitches[1:])]
        trigrams = [tuple(intervals[i:i+3]) for i in range(max(0, len(intervals)-2))]
        counts = Counter(trigrams)
        repeated = sum(n for n in counts.values() if n > 1)
        out[track_id] = {
            "interval_count": len(intervals),
            "unique_interval_count": len(set(intervals)),
            "interval_trigram_count": len(trigrams),
            "repeated_interval_trigram_occurrences": int(repeated),
            "most_common_interval_trigrams": [
                {"intervals": list(k), "count": int(v)}
                for k, v in counts.most_common(5)
            ],
        }
    return out


def _voice_leading(score: dict) -> dict:
    out = {}
    for track_id, events in _note_tracks(score).items():
        ordered = sorted(events, key=lambda e: float(e["start_beat"]))
        motions = [int(b["midi"]) - int(a["midi"]) for a, b in zip(ordered, ordered[1:])]
        abs_motion = [abs(x) for x in motions]
        direction_changes = 0
        signs = [1 if x > 0 else -1 if x < 0 else 0 for x in motions]
        nonzero = [x for x in signs if x]
        for a, b in zip(nonzero, nonzero[1:]):
            direction_changes += int(a != b)
        out[track_id] = {
            "transition_count": len(motions),
            "mean_abs_semitone_motion": float(np.mean(abs_motion)) if abs_motion else 0.0,
            "max_abs_semitone_motion": int(max(abs_motion)) if abs_motion else 0,
            "direction_change_count": int(direction_changes),
            "motion_sequence": motions,
        }
    return out


def _section_evidence(score: dict, plan: dict, audio: np.ndarray, sr: int) -> list[dict]:
    tracks = _note_tracks(score)
    bpm = float(plan["transport"]["bpm"])
    beat_s = 60.0 / bpm
    rows = []
    for section in plan["sections"]:
        start = float(section["start_beat"])
        end = start + float(section["duration_beats"])
        a = max(0, int(round(start * beat_s * sr)))
        b = min(len(audio), int(round(end * beat_s * sr)))
        segment = audio[a:b]
        rms = float(np.sqrt(np.mean(segment * segment))) if len(segment) else 0.0
        notes = [
            e for events in tracks.values() for e in events
            if start <= float(e["start_beat"]) < end - 1e-12
        ]
        velocities = [float(e["velocity"]) for e in notes]
        midis = [int(e["midi"]) for e in notes]
        rows.append({
            "section_id": section["id"],
            "start_beat": start,
            "end_beat": end,
            "audio_rms": rms,
            "note_count": len(notes),
            "notes_per_beat": float(len(notes) / max(1e-12, end-start)),
            "mean_velocity": float(np.mean(velocities)) if velocities else 0.0,
            "mean_midi": float(np.mean(midis)) if midis else 0.0,
            "authored_energy": float(section["energy"]) if "energy" in section else None,
        })
    return rows


def _masking(score: dict, close_semitones: int) -> list[dict]:
    tracks = _note_tracks(score)
    ids = list(tracks)
    rows = []
    for i, a_id in enumerate(ids):
        for b_id in ids[i+1:]:
            pairs = 0
            close_overlap = 0.0
            closest = 128
            for a in tracks[a_id]:
                a0 = float(a["start_beat"])
                a1 = a0 + float(a["duration_beats"])
                for b in tracks[b_id]:
                    b0 = float(b["start_beat"])
                    b1 = b0 + float(b["duration_beats"])
                    shared = max(0.0, min(a1, b1) - max(a0, b0))
                    if shared <= 1e-12:
                        continue
                    distance = abs(int(a["midi"]) - int(b["midi"]))
                    closest = min(closest, distance)
                    if distance <= close_semitones:
                        pairs += 1
                        close_overlap += shared
            rows.append({
                "tracks": [a_id, b_id],
                "close_register_semitones": int(close_semitones),
                "close_overlap_event_pairs": int(pairs),
                "close_register_overlap_beats": float(close_overlap),
                "closest_pitch_distance": None if closest == 128 else int(closest),
            })
    return rows


def _musical_evidence(score: dict, request: dict, render_result: dict) -> dict:
    audio = np.asarray(render_result["audio"], dtype=np.float64)
    sr = int(render_result["sr"])
    focus = set(request["evidence"]["focus"])
    p = request["evidence"]["parameters"]
    out = {}
    if "dynamics" in focus:
        out["dynamics"] = {
            "global": analyze_audio(audio, sr),
            "windowed": _window_rms(audio, sr, float(p["rms_window_ms"])),
        }
    if "spectrum" in focus:
        out["spectrum"] = _spectrum(audio, sr, int(p["spectrum_fft_size"]))
    if "register" in focus:
        out["register"] = _register_evidence(score, int(p["high_register_midi"]))
    if "phrase_continuity" in focus:
        out["phrase_continuity"] = _phrase_continuity(score)
    if "repetition" in focus:
        out["repetition"] = _repetition(score)
    if "voice_leading" in focus:
        out["voice_leading"] = _voice_leading(score)
    if "tension_release" in focus:
        out["tension_release"] = {
            "sections": _section_evidence(
                score, render_result["plan"], audio, sr
            ),
            "semantics": "descriptive section motion only; no tension quality score",
        }
    if "masking" in focus:
        out["masking"] = _masking(score, int(p["close_register_semitones"]))
    return out


def build_qa_report(
    score: dict,
    request: dict,
    render_result: dict,
    wav_path,
) -> dict:
    validate_performance_score(score)
    validate_qa_request(request)
    score_fp = performance_score_fingerprint(score)
    if request["source_score"]["fingerprint"] != score_fp:
        raise QaValidationError(
            "QA request source score fingerprint does not match Performance Score"
        )
    wav_path = Path(wav_path)
    integrity = _integrity(score, request, render_result)
    evidence = _musical_evidence(score, request, render_result)
    evidence_payload = json.dumps(
        evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return {
        "format": QA_REPORT_FORMAT,
        "source": {
            "song_fingerprint": score["source_song"]["fingerprint"],
            "performance_score_fingerprint": score_fp,
            "execution_plan_fingerprint": render_result["execution_plan_fingerprint"],
            "wav_sha256": _file_sha256(wav_path),
        },
        "request": {
            "fingerprint": qa_request_fingerprint(request),
            "target_fingerprint": qa_target_fingerprint(request),
            "hard_policy": deepcopy(request["hard_policy"]),
            "evidence": deepcopy(request["evidence"]),
        },
        "integrity": integrity,
        "musical_evidence": evidence,
        "musical_evidence_fingerprint": hashlib.sha256(evidence_payload.encode("utf-8")).hexdigest(),
        "semantics": {
            "hard_gate_authority": "objective integrity/correctness only",
            "musical_evidence_authority": "descriptive evidence for Composer interpretation",
            "aesthetic_score": False,
            "automatic_musical_acceptance": False,
            "automatic_revision": False,
        },
    }


def run_song_score_qa_to_dir(song: dict, score: dict, request: dict, output_dir) -> dict:
    validate_performance_score(score)
    validate_qa_request(request)
    score_fp = performance_score_fingerprint(score)
    if request["source_score"]["fingerprint"] != score_fp:
        raise QaValidationError(
            "QA request source score fingerprint does not match Performance Score"
        )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    wav = out / "qa.wav"
    result = render_song_score_to_files(
        song,
        score,
        wav,
        plan_path=out / "execution_plan.json",
        render_ir_path=out / "realized_ir.json",
        resolved_path=out / "resolved_ir.json",
        analysis_path=out / "audio_analysis.json",
    )
    report = build_qa_report(score, request, result, wav)
    (out / "qa_request.json").write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "qa_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"report": report, "render_result": result, "wav_path": wav}


def _changed_target_fields(before: dict, after: dict) -> list[str]:
    fields = []
    for key in sorted(set(before["hard_policy"]) | set(after["hard_policy"])):
        if before["hard_policy"].get(key) != after["hard_policy"].get(key):
            fields.append(f"hard_policy.{key}")
    if before["evidence"].get("focus") != after["evidence"].get("focus"):
        fields.append("evidence.focus")
    bp = before["evidence"].get("parameters", {})
    ap = after["evidence"].get("parameters", {})
    for key in sorted(set(bp) | set(ap)):
        if bp.get(key) != ap.get(key):
            fields.append(f"evidence.parameters.{key}")
    return fields


def compare_qa_reports(before: dict, after: dict) -> dict:
    if before.get("format") != QA_REPORT_FORMAT or after.get("format") != QA_REPORT_FORMAT:
        raise QaValidationError("compare_qa_reports requires QA report v1 inputs")
    changed = _changed_target_fields(before["request"], after["request"])
    target_mutation = bool(changed)
    return {
        "format": QA_COMPARISON_FORMAT,
        "before": {
            "score_fingerprint": before["source"]["performance_score_fingerprint"],
            "target_fingerprint": before["request"]["target_fingerprint"],
            "hard_gate_status": before["integrity"]["status"],
            "musical_evidence_fingerprint": before["musical_evidence_fingerprint"],
        },
        "after": {
            "score_fingerprint": after["source"]["performance_score_fingerprint"],
            "target_fingerprint": after["request"]["target_fingerprint"],
            "hard_gate_status": after["integrity"]["status"],
            "musical_evidence_fingerprint": after["musical_evidence_fingerprint"],
        },
        "target_mutation": {
            "detected": target_mutation,
            "changed_fields": changed,
            "same_target_comparison": not target_mutation,
        },
        "integrity_transition": {
            "before": before["integrity"]["status"],
            "after": after["integrity"]["status"],
        },
        "evidence_changed": (
            before["musical_evidence_fingerprint"]
            != after["musical_evidence_fingerprint"]
        ),
        "semantics": {
            "improvement_verdict": False,
            "aesthetic_ranking": False,
            "target_mutation_cannot_be_presented_as_improvement": True,
        },
    }


__all__ = [
    "QA_REQUEST_FORMAT",
    "QA_REPORT_FORMAT",
    "QA_COMPARISON_FORMAT",
    "QaValidationError",
    "validate_qa_request",
    "canonical_qa_request_json",
    "qa_request_fingerprint",
    "qa_target_fingerprint",
    "build_qa_report",
    "run_song_score_qa_to_dir",
    "compare_qa_reports",
]
