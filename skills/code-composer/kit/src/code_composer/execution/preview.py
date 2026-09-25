"""CR05 deterministic fast preview / incremental dry-stem cache.

Preview is an iteration surface, not the final/master authority. Stateful instruments
are always rendered from the beginning of the full piece into aligned dry stems; bar
or beat slicing happens only after deterministic mixing so pedal/string/body state is
never initialized at an arbitrary range boundary.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import wave
from typing import Any

import numpy as np

from ..composition.arrange import arrange_ir
from ..composition.performance import realize_performance_ir, validate_ir_performance_contract
from ..composition.resolve import resolve_ir
from ..core.constraints import enforce_forbidden_track_events
from ..core.ir import validate_ir
from ..mix.mixer import mix_graph, validate_mix_graph
from ..render import _render_dry_track, _timeline_size
from ..validation_contracts import validate_runtime_extensions
from .lowering import lower_song_to_execution_plan
from .performance_score import performance_score_fingerprint
from .plan import execution_plan_fingerprint
from .render_bridge import compile_performance_score_to_render_ir, realize_instrument_mechanics


PREVIEW_REQUEST_FORMAT = "code-composer-preview-request/v1"
PREVIEW_REPORT_FORMAT = "code-composer-preview-report/v1"
STEM_CACHE_FORMAT = "code-composer-preview-stem-cache/v1"

# Explicit renderer epoch. Any source change that can alter dry-track samples must bump
# this value so persistent caches cannot silently survive an engine implementation change.
STEM_CACHE_RENDERER_EPOCH = "cr05-renderer-epoch-1"


class PreviewValidationError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise PreviewValidationError(f"{path}: {message}")


def _strict(obj: Any, path: str, *, required=(), optional=()) -> dict:
    if not isinstance(obj, dict):
        _fail(path, "must be an object")
    missing = set(required) - set(obj)
    if missing:
        _fail(path, f"missing field(s): {sorted(missing)}")
    unknown = set(obj) - set(required) - set(optional)
    if unknown:
        _fail(path, f"unknown field(s): {sorted(unknown)}")
    return obj


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
        raise PreviewValidationError(f"{path}: must be numeric") from exc
    if not np.isfinite(out):
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


def validate_preview_request(request: dict[str, Any]) -> None:
    request = _strict(
        request,
        "request",
        required={"format", "source_score", "range", "tracks", "sample_rate"},
    )
    if request["format"] != PREVIEW_REQUEST_FORMAT:
        _fail("format", f"must equal {PREVIEW_REQUEST_FORMAT!r}")

    source = _strict(
        request["source_score"],
        "source_score",
        required={"format", "fingerprint"},
    )
    if source["format"] != "code-composer-performance-score/v1":
        _fail("source_score.format", "must be code-composer-performance-score/v1")
    _sha256(source["fingerprint"], "source_score.fingerprint")

    rng = _strict(
        request["range"],
        "range",
        required=set(),
        optional={"start_bar", "end_bar", "start_beat", "end_beat"},
    )
    bar_mode = "start_bar" in rng or "end_bar" in rng
    beat_mode = "start_beat" in rng or "end_beat" in rng
    if bar_mode == beat_mode:
        _fail("range", "must specify exactly one of bar range or beat range")
    if bar_mode:
        if set(rng) != {"start_bar", "end_bar"}:
            _fail("range", "bar range requires start_bar and end_bar only")
        start = _integer(rng["start_bar"], "range.start_bar", 1)
        end = _integer(rng["end_bar"], "range.end_bar", 1)
        if end < start:
            _fail("range", "end_bar must be >= start_bar")
    else:
        if set(rng) != {"start_beat", "end_beat"}:
            _fail("range", "beat range requires start_beat and end_beat only")
        start = _number(rng["start_beat"], "range.start_beat", 0)
        end = _number(rng["end_beat"], "range.end_beat", 0)
        if end <= start:
            _fail("range", "end_beat must be > start_beat")

    tracks = request["tracks"]
    if not isinstance(tracks, list) or not tracks:
        _fail("tracks", "must be a non-empty array")
    for i, item in enumerate(tracks):
        _string(item, f"tracks[{i}]")
    if len(set(tracks)) != len(tracks):
        _fail("tracks", "must be unique")

    _integer(request["sample_rate"], "sample_rate", 8000, 48000)


def canonical_preview_request_json(request: dict[str, Any]) -> str:
    validate_preview_request(request)
    return json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def preview_request_fingerprint(request: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_preview_request_json(request).encode("utf-8")).hexdigest()


def _prepare_render_ir(song: dict, score: dict, sample_rate: int) -> tuple[dict, dict]:
    plan = lower_song_to_execution_plan(song)
    render_ir = compile_performance_score_to_render_ir(plan, score)
    ir = realize_instrument_mechanics(render_ir, plan)
    ir = deepcopy(ir)
    ir["meta"]["sample_rate"] = int(sample_rate)

    validate_ir(ir)
    validate_runtime_extensions(ir)
    validate_ir_performance_contract(ir)
    graph0 = ir.get("mix", {}).get("graph")
    if graph0 is not None:
        validate_mix_graph(graph0, {t.get("id") for t in ir["tracks"]})
    if ir.get("arrangement") and not ir.get("arrangement_resolved"):
        ir = arrange_ir(ir)
    ir = resolve_ir(ir)
    if ir.get("performance_ir") and not ir.get("performance_resolved"):
        ir = realize_performance_ir(ir)
    ir["tracks"] = enforce_forbidden_track_events(ir.get("tracks", []), ir)
    return plan, ir


def _canonical_hash(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _stem_cache_identity(ir: dict, track: dict, *, n: int, sr: int, graph_mode: bool) -> dict:
    instrument_id = track["instrument"]
    return {
        "format": STEM_CACHE_FORMAT,
        "renderer_epoch": STEM_CACHE_RENDERER_EPOCH,
        "sample_rate": int(sr),
        "timeline_samples": int(n),
        "bpm": float(ir["transport"]["bpm"]),
        "beats_per_bar": int(ir["transport"]["beats_per_bar"]),
        "global_seed": int(ir["meta"].get("global_seed", 0)),
        "graph_mode": bool(graph_mode),
        "track": deepcopy(track),
        "instrument_id": instrument_id,
        "instrument_patch": deepcopy(ir["instruments"][instrument_id]),
    }


def _load_or_render_stem(
    ir: dict,
    track: dict,
    *,
    n: int,
    sr: int,
    beat_s: float,
    graph_mode: bool,
    cache_dir: Path,
) -> tuple[np.ndarray, dict]:
    identity = _stem_cache_identity(ir, track, n=n, sr=sr, graph_mode=graph_mode)
    key = _canonical_hash(identity)
    cache_dir.mkdir(parents=True, exist_ok=True)
    stem_path = cache_dir / f"{key}.npy"
    meta_path = cache_dir / f"{key}.json"

    hit = False
    buf = None
    if stem_path.exists():
        try:
            candidate = np.load(stem_path, allow_pickle=False)
            if candidate.dtype == np.float64 and candidate.shape == (n, 2):
                buf = candidate
                hit = True
        except Exception:
            buf = None

    if buf is None:
        buf = _render_dry_track(ir, track, n, sr, beat_s, graph_mode=graph_mode)
        buf = np.asarray(buf, dtype=np.float64)
        if buf.shape != (n, 2):
            raise PreviewValidationError(
                f"track {track['id']}: dry stem shape {buf.shape} != {(n, 2)}"
            )
        tmp_path = cache_dir / f".{key}.tmp.npy"
        np.save(tmp_path, buf, allow_pickle=False)
        tmp_path.replace(stem_path)
        meta_path.write_text(
            json.dumps(
                {
                    "format": STEM_CACHE_FORMAT,
                    "renderer_epoch": STEM_CACHE_RENDERER_EPOCH,
                    "cache_key": key,
                    "track": track["id"],
                    "identity_fingerprint": _canonical_hash(identity),
                    "samples": int(n),
                    "sample_rate": int(sr),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return buf, {
        "track": track["id"],
        "cache_key": key,
        "cache_hit": bool(hit),
        "samples": int(n),
        "sample_rate": int(sr),
        "cache_file": stem_path.name,
    }


def _resolve_range(request: dict, *, beats_per_bar: int, total_beats: float) -> tuple[float, float, dict]:
    rng = request["range"]
    if "start_bar" in rng:
        start_bar = int(rng["start_bar"])
        end_bar = int(rng["end_bar"])
        start_beat = float((start_bar - 1) * beats_per_bar)
        end_beat = float(end_bar * beats_per_bar)
        source = {
            "mode": "bars",
            "start_bar": start_bar,
            "end_bar": end_bar,
        }
    else:
        start_beat = float(rng["start_beat"])
        end_beat = float(rng["end_beat"])
        source = {
            "mode": "beats",
            "start_beat": start_beat,
            "end_beat": end_beat,
        }
    if start_beat >= total_beats - 1e-12:
        raise PreviewValidationError("preview range starts at or beyond piece end")
    if end_beat > total_beats + 1e-9:
        raise PreviewValidationError(
            f"preview range ends at beat {end_beat:g}, beyond piece end {total_beats:g}"
        )
    return start_beat, end_beat, source


def _write_wav(path: Path, audio: np.ndarray, sr: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(int(sr))
        wf.writeframes(pcm.tobytes())


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def render_song_score_preview(
    song: dict,
    score: dict,
    request: dict,
    wav_path,
    cache_dir,
    *,
    report_path=None,
) -> dict:
    validate_preview_request(request)
    source_fp = performance_score_fingerprint(score)
    if request["source_score"]["fingerprint"] != source_fp:
        raise PreviewValidationError(
            "preview request source score fingerprint does not match Performance Score"
        )

    plan, ir = _prepare_render_ir(song, score, int(request["sample_rate"]))
    track_map = {t["id"]: t for t in ir["tracks"]}
    selected = list(request["tracks"])
    missing = [tid for tid in selected if tid not in track_map]
    if missing:
        raise PreviewValidationError(f"unknown preview track(s): {missing}")

    sr = int(ir["meta"]["sample_rate"])
    bpm = float(ir["transport"]["bpm"])
    beat_s = 60.0 / bpm
    n = _timeline_size(ir, sr, beat_s)
    graph = ir.get("mix", {}).get("graph")
    if not graph:
        raise PreviewValidationError("CR05 preview requires graph-mode Performance Score mixing")
    graph_mode = True

    stems = {}
    cache_reports = []
    cache_root = Path(cache_dir)
    for tid in selected:
        buf, cache_info = _load_or_render_stem(
            ir,
            track_map[tid],
            n=n,
            sr=sr,
            beat_s=beat_s,
            graph_mode=graph_mode,
            cache_dir=cache_root,
        )
        stems[tid] = buf
        cache_reports.append(cache_info)

    master, mix_report = mix_graph(stems, sr, graph, ir=ir)

    total_beats = max(
        float(section["start_beat"]) + float(section["duration_beats"])
        for section in plan["sections"]
    )
    start_beat, end_beat, range_source = _resolve_range(
        request,
        beats_per_bar=int(ir["transport"]["beats_per_bar"]),
        total_beats=total_beats,
    )
    start_sample = max(0, int(round(start_beat * beat_s * sr)))
    end_sample = min(len(master), int(round(end_beat * beat_s * sr)))
    if end_sample <= start_sample:
        raise PreviewValidationError("preview range resolved to an empty audio slice")
    preview = np.asarray(master[start_sample:end_sample], dtype=np.float64)

    wav_path = Path(wav_path)
    _write_wav(wav_path, preview, sr)

    peak = float(np.max(np.abs(preview))) if len(preview) else 0.0
    rms = float(np.sqrt(np.mean(preview * preview))) if len(preview) else 0.0
    clipped = float(np.mean(np.abs(preview) >= 1.0)) if len(preview) else 0.0
    hits = sum(1 for x in cache_reports if x["cache_hit"])
    misses = len(cache_reports) - hits

    report = {
        "format": PREVIEW_REPORT_FORMAT,
        "authority": "draft-preview-only",
        "renderer_epoch": STEM_CACHE_RENDERER_EPOCH,
        "source_song_fingerprint": plan["source_song"]["fingerprint"],
        "source_score_fingerprint": source_fp,
        "execution_plan_fingerprint": execution_plan_fingerprint(plan),
        "preview_request_fingerprint": preview_request_fingerprint(request),
        "sample_rate": sr,
        "selected_tracks": selected,
        "range": {
            **range_source,
            "start_beat": start_beat,
            "end_beat": end_beat,
            "start_sample": start_sample,
            "end_sample": end_sample,
        },
        "cache": {
            "format": STEM_CACHE_FORMAT,
            "hits": hits,
            "misses": misses,
            "tracks": cache_reports,
        },
        "mix_report": mix_report,
        "preview_metrics": {
            "duration_seconds": float(len(preview) / sr),
            "peak": peak,
            "rms": rms,
            "clipped_sample_ratio": clipped,
        },
        "wav": str(wav_path),
        "wav_sha256": _file_sha256(wav_path),
        "final_render_authority": False,
    }
    if report_path is not None:
        Path(report_path).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return {
        "audio": preview,
        "sr": sr,
        "report": report,
        "plan": plan,
        "render_ir": ir,
        "wav_path": wav_path,
    }


__all__ = [
    "PREVIEW_REQUEST_FORMAT",
    "PREVIEW_REPORT_FORMAT",
    "STEM_CACHE_FORMAT",
    "STEM_CACHE_RENDERER_EPOCH",
    "PreviewValidationError",
    "validate_preview_request",
    "canonical_preview_request_json",
    "preview_request_fingerprint",
    "render_song_score_preview",
]
