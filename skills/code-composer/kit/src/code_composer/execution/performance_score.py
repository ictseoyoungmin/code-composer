"""CR03 canonical Performance Score.

The score is the Composer-authored performance state: exact pitches, voicings,
rhythm, explicit rests, dynamics, articulation, controls, and mix intent.

It intentionally does not infer or generate musical content.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any


PERFORMANCE_SCORE_FORMAT = "code-composer-performance-score/v1"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class PerformanceScoreValidationError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise PerformanceScoreValidationError(f"{path}: {message}")


def _object(value: Any, path: str) -> dict:
    if not isinstance(value, dict):
        _fail(path, "must be an object")
    return value


def _array(value: Any, path: str, *, nonempty: bool = False) -> list:
    if not isinstance(value, list):
        _fail(path, "must be an array")
    if nonempty and not value:
        _fail(path, "must not be empty")
    return value


def _strict(obj: dict, path: str, *, required=(), optional=()) -> None:
    missing = set(required) - set(obj)
    if missing:
        _fail(path, f"missing field(s): {sorted(missing)}")
    unknown = set(obj) - set(required) - set(optional)
    if unknown:
        _fail(path, f"unknown field(s): {sorted(unknown)}")


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(path, "must be a non-empty string")
    return value


def _identifier(value: Any, path: str) -> str:
    value = _string(value, path)
    if not _ID_RE.fullmatch(value):
        _fail(path, "must match [A-Za-z0-9][A-Za-z0-9._-]*")
    return value


def _number(value: Any, path: str, lo: float | None = None, hi: float | None = None) -> float:
    if isinstance(value, bool):
        _fail(path, "must be numeric")
    try:
        out = float(value)
    except Exception as exc:
        raise PerformanceScoreValidationError(f"{path}: must be numeric") from exc
    if not math.isfinite(out):
        _fail(path, "must be finite")
    if lo is not None and out < lo:
        _fail(path, f"must be >= {lo}")
    if hi is not None and out > hi:
        _fail(path, f"must be <= {hi}")
    return out


def _integer(value: Any, path: str, lo: int | None = None, hi: int | None = None) -> int:
    if isinstance(value, bool):
        _fail(path, "must be an integer")
    if isinstance(value, int):
        out = value
    elif isinstance(value, float) and math.isfinite(value) and value.is_integer():
        out = int(value)
    else:
        _fail(path, "must be an integer")
    if lo is not None and out < lo:
        _fail(path, f"must be >= {lo}")
    if hi is not None and out > hi:
        _fail(path, f"must be <= {hi}")
    return out


def _validate_sha256(value: Any, path: str) -> str:
    value = _string(value, path)
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        _fail(path, "must be lowercase sha256 hex")
    return value


def _validate_event(event: dict, path: str) -> None:
    event_type = event.get("type")
    if event_type == "note":
        _strict(
            event,
            path,
            required={"id", "type", "start_beat", "duration_beats", "midi", "velocity"},
            optional={"articulation", "expression", "piano_attack_offset_ms"},
        )
        _identifier(event["id"], f"{path}.id")
        _number(event["start_beat"], f"{path}.start_beat", 0)
        _number(event["duration_beats"], f"{path}.duration_beats", 1e-9)
        _integer(event["midi"], f"{path}.midi", 0, 127)
        _number(event["velocity"], f"{path}.velocity", 0, 1)
        if "articulation" in event:
            _string(event["articulation"], f"{path}.articulation")
        if "expression" in event:
            expression = _object(event["expression"], f"{path}.expression")
            for key, value in expression.items():
                _string(key, f"{path}.expression key")
                _number(value, f"{path}.expression.{key}")
        if "piano_attack_offset_ms" in event:
            _number(event["piano_attack_offset_ms"], f"{path}.piano_attack_offset_ms", -20, 20)
        return

    if event_type == "sustain_pedal":
        _strict(
            event,
            path,
            required={"id", "type", "start_beat", "duration_beats", "points"},
        )
        _identifier(event["id"], f"{path}.id")
        start = _number(event["start_beat"], f"{path}.start_beat", 0)
        duration = _number(event["duration_beats"], f"{path}.duration_beats", 1e-9)
        del start
        points = _array(event["points"], f"{path}.points", nonempty=True)
        if len(points) < 2:
            _fail(f"{path}.points", "must contain at least two points")
        previous = None
        for i, point in enumerate(points):
            p = f"{path}.points[{i}]"
            point = _object(point, p)
            _strict(point, p, required={"offset_beats", "position"})
            offset = _number(point["offset_beats"], f"{p}.offset_beats", 0, duration)
            _number(point["position"], f"{p}.position", 0, 1)
            if previous is not None and offset <= previous + 1e-12:
                _fail(f"{path}.points", "offsets must be strictly increasing")
            previous = offset
        if abs(float(points[0]["offset_beats"])) > 1e-12:
            _fail(f"{path}.points", "must start at offset 0")
        if abs(float(points[-1]["offset_beats"]) - duration) > 1e-9:
            _fail(f"{path}.points", "must end at duration_beats")
        return

    _fail(f"{path}.type", "must be note or sustain_pedal")


def validate_performance_score(score: dict[str, Any]) -> None:
    score = _object(score, "score")
    _strict(
        score,
        "score",
        required={"format", "source_song", "meta", "tracks", "render"},
    )
    if score["format"] != PERFORMANCE_SCORE_FORMAT:
        _fail("format", f"must equal {PERFORMANCE_SCORE_FORMAT!r}")

    source = _object(score["source_song"], "source_song")
    _strict(source, "source_song", required={"format", "fingerprint"})
    if source["format"] != "code-composer-song/v1":
        _fail("source_song.format", "must be code-composer-song/v1")
    _validate_sha256(source["fingerprint"], "source_song.fingerprint")

    meta = _object(score["meta"], "meta")
    _strict(meta, "meta", required={"title"}, optional={"revision"})
    _string(meta["title"], "meta.title")
    if "revision" in meta:
        _string(meta["revision"], "meta.revision")

    tracks = _array(score["tracks"], "tracks", nonempty=True)
    track_ids = set()
    event_ids = set()
    for i, track in enumerate(tracks):
        path = f"tracks[{i}]"
        track = _object(track, path)
        _strict(track, path, required={"id", "events"})
        tid = _identifier(track["id"], f"{path}.id")
        if tid in track_ids:
            _fail("tracks", f"duplicate id: {tid}")
        track_ids.add(tid)
        events = _array(track["events"], f"{path}.events", nonempty=True)
        previous_start = -1.0
        for j, event in enumerate(events):
            event = _object(event, f"{path}.events[{j}]")
            _validate_event(event, f"{path}.events[{j}]")
            eid = event["id"]
            if eid in event_ids:
                _fail("tracks", f"duplicate event id: {eid}")
            event_ids.add(eid)
            start = float(event["start_beat"])
            if start + 1e-12 < previous_start:
                _fail(f"{path}.events", "must be ordered by start_beat")
            previous_start = start

    render = _object(score["render"], "render")
    _strict(render, "render", required={"sample_rate", "tail_seconds", "mix"})
    _integer(render["sample_rate"], "render.sample_rate", 8000, 192000)
    _number(render["tail_seconds"], "render.tail_seconds", 0, 20)

    mix = _object(render["mix"], "render.mix")
    _strict(
        mix,
        "render.mix",
        required={"tracks", "music_bus_gain", "room_return_gain", "master_gain"},
    )
    mix_tracks = _array(mix["tracks"], "render.mix.tracks", nonempty=True)
    seen = set()
    for i, item in enumerate(mix_tracks):
        path = f"render.mix.tracks[{i}]"
        item = _object(item, path)
        _strict(item, path, required={"track", "gain", "pan", "reverb_send"})
        tid = _identifier(item["track"], f"{path}.track")
        if tid in seen:
            _fail("render.mix.tracks", f"duplicate track: {tid}")
        seen.add(tid)
        _number(item["gain"], f"{path}.gain", 0, 2)
        _number(item["pan"], f"{path}.pan", -1, 1)
        _number(item["reverb_send"], f"{path}.reverb_send", 0, 1)
    if seen != track_ids:
        _fail("render.mix.tracks", "must cover exactly the authored score tracks")
    _number(mix["music_bus_gain"], "render.mix.music_bus_gain", 0, 2)
    _number(mix["room_return_gain"], "render.mix.room_return_gain", 0, 2)
    _number(mix["master_gain"], "render.mix.master_gain", 0, 2)


def canonical_performance_score_json(score: dict[str, Any]) -> str:
    validate_performance_score(score)
    return json.dumps(score, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def performance_score_fingerprint(score: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_performance_score_json(score).encode("utf-8")).hexdigest()


__all__ = [
    "PERFORMANCE_SCORE_FORMAT",
    "PerformanceScoreValidationError",
    "validate_performance_score",
    "canonical_performance_score_json",
    "performance_score_fingerprint",
]
