"""CR04 Composer-authored Performance Score revision operations.

Analysis may provide evidence, but it never chooses or applies an operation.
Every plan binds to one exact source Performance Score fingerprint.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re
from typing import Any

from .performance_score import (
    performance_score_fingerprint,
    validate_performance_score,
)


REVISION_PLAN_FORMAT = "code-composer-revision-plan/v1"
REVISION_RECORD_FORMAT = "code-composer-revision-record/v1"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class PerformanceRevisionError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise PerformanceRevisionError(f"{path}: {message}")


def _strict(obj: dict, path: str, *, required=(), optional=()) -> None:
    if not isinstance(obj, dict):
        _fail(path, "must be an object")
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


def _number(value: Any, path: str, lo=None, hi=None) -> float:
    if isinstance(value, bool):
        _fail(path, "must be numeric")
    try:
        out = float(value)
    except Exception as exc:
        raise PerformanceRevisionError(f"{path}: must be numeric") from exc
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


def _sha256(value: Any, path: str) -> str:
    value = _string(value, path)
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        _fail(path, "must be lowercase sha256 hex")
    return value


def _string_array(value: Any, path: str, *, nonempty=False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        _fail(path, "must be a non-empty array" if nonempty else "must be an array")
    out = []
    for i, item in enumerate(value):
        out.append(_string(item, f"{path}[{i}]"))
    return out


def validate_revision_plan(plan: dict[str, Any]) -> None:
    _strict(
        plan,
        "plan",
        required={"format", "source_score", "meta", "critique", "ops"},
    )
    if plan["format"] != REVISION_PLAN_FORMAT:
        _fail("format", f"must equal {REVISION_PLAN_FORMAT!r}")

    source = plan["source_score"]
    _strict(source, "source_score", required={"format", "fingerprint"})
    if source["format"] != "code-composer-performance-score/v1":
        _fail("source_score.format", "must be code-composer-performance-score/v1")
    _sha256(source["fingerprint"], "source_score.fingerprint")

    meta = plan["meta"]
    _strict(meta, "meta", required={"id", "summary"})
    _identifier(meta["id"], "meta.id")
    _string(meta["summary"], "meta.summary")

    critique = plan["critique"]
    _strict(critique, "critique", required={"observations", "preserve", "acceptance"})
    _string_array(critique["observations"], "critique.observations", nonempty=True)
    _string_array(critique["preserve"], "critique.preserve", nonempty=True)
    _string_array(critique["acceptance"], "critique.acceptance", nonempty=True)

    ops = plan["ops"]
    if not isinstance(ops, list) or not ops:
        _fail("ops", "must be a non-empty array")

    for i, op in enumerate(ops):
        path = f"ops[{i}]"
        if not isinstance(op, dict):
            _fail(path, "must be an object")
        kind = op.get("op")
        if kind == "scale_velocity":
            _strict(
                op, path,
                required={"op", "track", "start_beat", "end_beat", "factor"},
                optional={"event_ids"},
            )
            _identifier(op["track"], f"{path}.track")
            start = _number(op["start_beat"], f"{path}.start_beat", 0)
            end = _number(op["end_beat"], f"{path}.end_beat", 0)
            if end <= start:
                _fail(path, "end_beat must be greater than start_beat")
            _number(op["factor"], f"{path}.factor", 0.1, 2.0)
            if "event_ids" in op:
                ids = _string_array(op["event_ids"], f"{path}.event_ids", nonempty=True)
                if len(set(ids)) != len(ids):
                    _fail(f"{path}.event_ids", "must be unique")
        elif kind == "thin_accompaniment":
            _strict(op, path, required={"op", "track", "event_ids", "reason"})
            _identifier(op["track"], f"{path}.track")
            ids = _string_array(op["event_ids"], f"{path}.event_ids", nonempty=True)
            if len(set(ids)) != len(ids):
                _fail(f"{path}.event_ids", "must be unique")
            _string(op["reason"], f"{path}.reason")
        elif kind == "set_track_mix_gain":
            _strict(op, path, required={"op", "track", "gain"})
            _identifier(op["track"], f"{path}.track")
            _number(op["gain"], f"{path}.gain", 0, 2)
        elif kind == "shift_register":
            _strict(
                op, path,
                required={"op", "track", "start_beat", "end_beat", "octaves"},
            )
            _identifier(op["track"], f"{path}.track")
            start = _number(op["start_beat"], f"{path}.start_beat", 0)
            end = _number(op["end_beat"], f"{path}.end_beat", 0)
            if end <= start:
                _fail(path, "end_beat must be greater than start_beat")
            _integer(op["octaves"], f"{path}.octaves", -2, 2)
            if op["octaves"] == 0:
                _fail(f"{path}.octaves", "must not be zero")
        else:
            _fail(f"{path}.op", "unsupported revision operation")


def canonical_revision_plan_json(plan: dict[str, Any]) -> str:
    validate_revision_plan(plan)
    return json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def revision_plan_fingerprint(plan: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_revision_plan_json(plan).encode("utf-8")).hexdigest()


def _track(score: dict, track_id: str) -> dict:
    for track in score["tracks"]:
        if track["id"] == track_id:
            return track
    raise PerformanceRevisionError(f"unknown track: {track_id}")


def _mix_track(score: dict, track_id: str) -> dict:
    for item in score["render"]["mix"]["tracks"]:
        if item["track"] == track_id:
            return item
    raise PerformanceRevisionError(f"missing mix route for track: {track_id}")


def apply_revision_plan(score: dict, plan: dict) -> tuple[dict, dict]:
    validate_performance_score(score)
    validate_revision_plan(plan)

    before_fp = performance_score_fingerprint(score)
    expected = plan["source_score"]["fingerprint"]
    if before_fp != expected:
        raise PerformanceRevisionError(
            f"source score fingerprint mismatch: expected {expected}, got {before_fp}"
        )

    out = deepcopy(score)
    changes = []
    changed_event_ids = set()
    changed_mix_tracks = set()

    for i, op in enumerate(plan["ops"]):
        kind = op["op"]
        detail = {"index": i, "op": kind, "changes": []}

        if kind == "scale_velocity":
            track = _track(out, op["track"])
            start = float(op["start_beat"])
            end = float(op["end_beat"])
            factor = float(op["factor"])
            selected_ids = set(op.get("event_ids", []))
            seen_selected = set()
            for event in track["events"]:
                if event["type"] != "note":
                    continue
                beat = float(event["start_beat"])
                id_match = not selected_ids or event["id"] in selected_ids
                if start <= beat < end and id_match:
                    seen_selected.add(event["id"])
                    before = float(event["velocity"])
                    after = max(0.0, min(1.0, before * factor))
                    event["velocity"] = round(after, 9)
                    detail["changes"].append({
                        "event_id": event["id"],
                        "field": "velocity",
                        "before": before,
                        "after": event["velocity"],
                    })
                    changed_event_ids.add(event["id"])
            if selected_ids:
                missing = sorted(selected_ids - seen_selected)
                if missing:
                    raise PerformanceRevisionError(
                        f"ops[{i}]: scale_velocity unknown/out-of-range event id(s): {missing}"
                    )
            if not detail["changes"]:
                raise PerformanceRevisionError(
                    f"ops[{i}]: scale_velocity matched no note events"
                )

        elif kind == "thin_accompaniment":
            track = _track(out, op["track"])
            wanted = list(op["event_ids"])
            found = {}
            kept = []
            for event in track["events"]:
                if event["id"] not in wanted:
                    kept.append(event)
                    continue
                if event["type"] != "note":
                    raise PerformanceRevisionError(
                        f"ops[{i}]: thin_accompaniment may remove note events only: {event['id']}"
                    )
                found[event["id"]] = deepcopy(event)
            missing = [eid for eid in wanted if eid not in found]
            if missing:
                raise PerformanceRevisionError(
                    f"ops[{i}]: unknown event id(s): {missing}"
                )
            track["events"] = kept
            for eid in wanted:
                detail["changes"].append({
                    "event_id": eid,
                    "field": "event",
                    "before": found[eid],
                    "after": None,
                })
                changed_event_ids.add(eid)

        elif kind == "set_track_mix_gain":
            route = _mix_track(out, op["track"])
            before = float(route["gain"])
            route["gain"] = float(op["gain"])
            detail["changes"].append({
                "track": op["track"],
                "field": "mix.gain",
                "before": before,
                "after": route["gain"],
            })
            changed_mix_tracks.add(op["track"])

        elif kind == "shift_register":
            track = _track(out, op["track"])
            start = float(op["start_beat"])
            end = float(op["end_beat"])
            delta = 12 * int(op["octaves"])
            for event in track["events"]:
                if event["type"] != "note":
                    continue
                beat = float(event["start_beat"])
                if start <= beat < end:
                    before = int(event["midi"])
                    after = before + delta
                    if not 0 <= after <= 127:
                        raise PerformanceRevisionError(
                            f"ops[{i}]: event {event['id']} would leave MIDI range"
                        )
                    event["midi"] = after
                    detail["changes"].append({
                        "event_id": event["id"],
                        "field": "midi",
                        "before": before,
                        "after": after,
                    })
                    changed_event_ids.add(event["id"])
            if not detail["changes"]:
                raise PerformanceRevisionError(
                    f"ops[{i}]: shift_register matched no note events"
                )

        changes.append(detail)

    out["meta"]["revision"] = plan["meta"]["id"]
    validate_performance_score(out)
    after_fp = performance_score_fingerprint(out)
    if after_fp == before_fp:
        raise PerformanceRevisionError("revision produced no score change")

    record = {
        "format": REVISION_RECORD_FORMAT,
        "revision_id": plan["meta"]["id"],
        "summary": plan["meta"]["summary"],
        "source_score_fingerprint": before_fp,
        "revision_plan_fingerprint": revision_plan_fingerprint(plan),
        "after_score_fingerprint": after_fp,
        "source_song_fingerprint": score["source_song"]["fingerprint"],
        "critique": deepcopy(plan["critique"]),
        "operations": changes,
        "changed_event_ids": sorted(changed_event_ids),
        "changed_mix_tracks": sorted(changed_mix_tracks),
    }
    return out, record


__all__ = [
    "REVISION_PLAN_FORMAT",
    "REVISION_RECORD_FORMAT",
    "PerformanceRevisionError",
    "validate_revision_plan",
    "canonical_revision_plan_json",
    "revision_plan_fingerprint",
    "apply_revision_plan",
]
