"""CR02 deterministic execution-plan contract.

The execution plan contains only authored musical material plus deterministic runtime
facts needed for later realization. It does not invent notes, chord voicings, register
changes, dynamics, or fixed arrangement roles.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any


EXECUTION_PLAN_FORMAT = "code-composer-execution-plan/v1"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ExecutionPlanValidationError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise ExecutionPlanValidationError(f"{path}: {message}")


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


def _number(value: Any, path: str, lo: float | None = None) -> float:
    if isinstance(value, bool):
        _fail(path, "must be numeric")
    try:
        out = float(value)
    except Exception as exc:
        raise ExecutionPlanValidationError(f"{path}: must be numeric") from exc
    if not math.isfinite(out):
        _fail(path, "must be finite")
    if lo is not None and out < lo:
        _fail(path, f"must be >= {lo}")
    return out


def _integer(value: Any, path: str, lo: int | None = None) -> int:
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
    return out


def _unique(items: list, path: str) -> dict[str, dict]:
    result = {}
    for i, item in enumerate(items):
        item = _object(item, f"{path}[{i}]")
        ident = _identifier(item.get("id"), f"{path}[{i}].id")
        if ident in result:
            _fail(path, f"duplicate id: {ident}")
        result[ident] = item
    return result


def _validate_source(plan: dict) -> None:
    source = _object(plan["source_song"], "source_song")
    _strict(source, "source_song", required={"format", "fingerprint"})
    if source["format"] != "code-composer-song/v1":
        _fail("source_song.format", "must be code-composer-song/v1")
    fp = _string(source["fingerprint"], "source_song.fingerprint")
    if len(fp) != 64 or any(c not in "0123456789abcdef" for c in fp):
        _fail("source_song.fingerprint", "must be lowercase sha256 hex")


def _validate_meta(plan: dict) -> None:
    meta = _object(plan["meta"], "meta")
    _strict(meta, "meta", required={"title", "global_seed"})
    _string(meta["title"], "meta.title")
    _integer(meta["global_seed"], "meta.global_seed", 0)


def _validate_transport(plan: dict) -> None:
    transport = _object(plan["transport"], "transport")
    _strict(transport, "transport", required={"bpm", "meter"})
    _number(transport["bpm"], "transport.bpm", 1e-9)
    meter = _object(transport["meter"], "transport.meter")
    _strict(meter, "transport.meter", required={"beats_per_bar", "beat_unit"})
    _integer(meter["beats_per_bar"], "transport.meter.beats_per_bar", 1)
    _integer(meter["beat_unit"], "transport.meter.beat_unit", 1)


def _validate_tonal(plan: dict) -> None:
    if "tonal" not in plan:
        return
    tonal = _object(plan["tonal"], "tonal")
    _strict(tonal, "tonal", required={"root", "scale"})
    _string(tonal["root"], "tonal.root")
    _string(tonal["scale"], "tonal.scale")


def _validate_sections(plan: dict) -> dict[str, dict]:
    items = _array(plan["sections"], "sections", nonempty=True)
    sections = _unique(items, "sections")
    previous_end = 0.0
    for i, section in enumerate(items):
        path = f"sections[{i}]"
        _strict(
            section, path,
            required={"id", "start_bar", "bars", "start_beat", "duration_beats"},
            optional={"name", "energy", "intent"},
        )
        start_bar = _integer(section["start_bar"], f"{path}.start_bar", 0)
        bars = _integer(section["bars"], f"{path}.bars", 1)
        start = _number(section["start_beat"], f"{path}.start_beat", 0)
        duration = _number(section["duration_beats"], f"{path}.duration_beats", 1e-9)
        if i == 0 and (start_bar != 0 or abs(start) > 1e-12):
            _fail(path, "first section must start at bar/beat 0")
        if i > 0 and abs(start - previous_end) > 1e-9:
            _fail(path, "sections must form a contiguous timeline")
        previous_end = start + duration
        if "name" in section:
            _string(section["name"], f"{path}.name")
        if "intent" in section:
            _string(section["intent"], f"{path}.intent")
        if "energy" in section:
            value = _number(section["energy"], f"{path}.energy", 0)
            if value > 1:
                _fail(f"{path}.energy", "must be <= 1")
        del bars
    return sections


def _validate_instruments(plan: dict) -> dict[str, dict]:
    items = _array(plan["instruments"], "instruments", nonempty=True)
    instruments = _unique(items, "instruments")
    allowed_sources = {"family_default", "explicit_preset_lock", "engine_lock_family_default"}
    for i, instrument in enumerate(items):
        path = f"instruments[{i}]"
        _strict(
            instrument, path,
            required={"id", "family", "engine", "patch", "resolution"},
            optional={"name", "variant"},
        )
        _string(instrument["family"], f"{path}.family")
        _string(instrument["engine"], f"{path}.engine")
        if "name" in instrument:
            _string(instrument["name"], f"{path}.name")
        if "variant" in instrument:
            _string(instrument["variant"], f"{path}.variant")
        _object(instrument["patch"], f"{path}.patch")
        resolution = _object(instrument["resolution"], f"{path}.resolution")
        _strict(
            resolution, f"{path}.resolution",
            required={"source", "preset_id", "preset_version"},
        )
        if resolution["source"] not in allowed_sources:
            _fail(f"{path}.resolution.source", f"must be one of {sorted(allowed_sources)}")
        _string(resolution["preset_id"], f"{path}.resolution.preset_id")
        _string(resolution["preset_version"], f"{path}.resolution.preset_version")
    return instruments


def _validate_tracks(plan: dict, instruments: dict[str, dict]) -> dict[str, dict]:
    items = _array(plan["tracks"], "tracks", nonempty=True)
    tracks = _unique(items, "tracks")
    for i, track in enumerate(items):
        path = f"tracks[{i}]"
        _strict(track, path, required={"id", "function", "instrument"}, optional={"name"})
        _string(track["function"], f"{path}.function")
        inst = _identifier(track["instrument"], f"{path}.instrument")
        if inst not in instruments:
            _fail(f"{path}.instrument", f"unknown instrument: {inst}")
        if "name" in track:
            _string(track["name"], f"{path}.name")
    return tracks


def _validate_materials(plan: dict) -> dict[str, dict]:
    items = _array(plan["materials"], "materials", nonempty=True)
    materials = _unique(items, "materials")
    for i, material in enumerate(items):
        path = f"materials[{i}]"
        kind = material.get("kind")
        if kind == "motif":
            _strict(material, path, required={"id", "kind", "intervals", "rhythm", "duration_beats"})
            intervals = _array(material["intervals"], f"{path}.intervals", nonempty=True)
            rhythm = _array(material["rhythm"], f"{path}.rhythm", nonempty=True)
            if len(intervals) != len(rhythm):
                _fail(path, "motif intervals/rhythm length mismatch")
            for j, value in enumerate(intervals):
                _integer(value, f"{path}.intervals[{j}]")
            total = sum(_number(v, f"{path}.rhythm[{j}]", 1e-9) for j, v in enumerate(rhythm))
        elif kind == "progression":
            _strict(material, path, required={"id", "kind", "degrees", "rhythm", "duration_beats"})
            degrees = _array(material["degrees"], f"{path}.degrees", nonempty=True)
            rhythm = _array(material["rhythm"], f"{path}.rhythm", nonempty=True)
            if len(degrees) != len(rhythm):
                _fail(path, "progression degrees/rhythm length mismatch")
            for j, value in enumerate(degrees):
                _integer(value, f"{path}.degrees[{j}]", 1)
            total = sum(_number(v, f"{path}.rhythm[{j}]", 1e-9) for j, v in enumerate(rhythm))
        elif kind == "rhythm":
            _strict(material, path, required={"id", "kind", "cycle_beats", "steps", "duration_beats"})
            cycle = _number(material["cycle_beats"], f"{path}.cycle_beats", 1e-9)
            steps = _array(material["steps"], f"{path}.steps", nonempty=True)
            for j, step in enumerate(steps):
                step = _object(step, f"{path}.steps[{j}]")
                _strict(step, f"{path}.steps[{j}]", required={"beat", "weight"}, optional={"duration"})
                beat = _number(step["beat"], f"{path}.steps[{j}].beat", 0)
                if beat >= cycle:
                    _fail(f"{path}.steps[{j}].beat", "must be < cycle_beats")
                _number(step["weight"], f"{path}.steps[{j}].weight", 0)
                if "duration" in step:
                    _number(step["duration"], f"{path}.steps[{j}].duration", 1e-9)
            total = cycle
        else:
            _fail(f"{path}.kind", "must be motif, progression, or rhythm")
        authored = _number(material["duration_beats"], f"{path}.duration_beats", 1e-9)
        if abs(authored - total) > 1e-9:
            _fail(f"{path}.duration_beats", f"must equal authored material duration ({total:g})")
    return materials


def _validate_instances(
    plan: dict,
    sections: dict[str, dict],
    tracks: dict[str, dict],
    instruments: dict[str, dict],
    materials: dict[str, dict],
) -> None:
    items = _array(plan["part_instances"], "part_instances", nonempty=True)
    _unique(items, "part_instances")
    for i, instance in enumerate(items):
        path = f"part_instances[{i}]"
        _strict(
            instance, path,
            required={
                "id", "source_part", "repeat_index", "section", "track", "instrument",
                "material", "material_kind", "start_beat", "duration_beats",
            },
        )
        _identifier(instance["source_part"], f"{path}.source_part")
        _integer(instance["repeat_index"], f"{path}.repeat_index", 0)
        sid = _identifier(instance["section"], f"{path}.section")
        tid = _identifier(instance["track"], f"{path}.track")
        iid = _identifier(instance["instrument"], f"{path}.instrument")
        mid = _identifier(instance["material"], f"{path}.material")
        if sid not in sections:
            _fail(f"{path}.section", f"unknown section: {sid}")
        if tid not in tracks:
            _fail(f"{path}.track", f"unknown track: {tid}")
        if iid not in instruments:
            _fail(f"{path}.instrument", f"unknown instrument: {iid}")
        if mid not in materials:
            _fail(f"{path}.material", f"unknown material: {mid}")
        if tracks[tid]["instrument"] != iid:
            _fail(f"{path}.instrument", "must match track instrument")
        if materials[mid]["kind"] != instance["material_kind"]:
            _fail(f"{path}.material_kind", "must match material kind")
        start = _number(instance["start_beat"], f"{path}.start_beat", 0)
        duration = _number(instance["duration_beats"], f"{path}.duration_beats", 1e-9)
        section = sections[sid]
        section_start = float(section["start_beat"])
        section_end = section_start + float(section["duration_beats"])
        if start < section_start - 1e-9 or start + duration > section_end + 1e-9:
            _fail(path, "instance must fit inside referenced section")


def validate_execution_plan(plan: dict[str, Any]) -> None:
    plan = _object(plan, "plan")
    _strict(
        plan,
        "plan",
        required={
            "format", "source_song", "meta", "transport", "sections",
            "instruments", "tracks", "materials", "part_instances",
        },
        optional={"tonal"},
    )
    if plan["format"] != EXECUTION_PLAN_FORMAT:
        _fail("format", f"must equal {EXECUTION_PLAN_FORMAT!r}")
    _validate_source(plan)
    _validate_meta(plan)
    _validate_transport(plan)
    _validate_tonal(plan)
    sections = _validate_sections(plan)
    instruments = _validate_instruments(plan)
    tracks = _validate_tracks(plan, instruments)
    materials = _validate_materials(plan)
    _validate_instances(plan, sections, tracks, instruments, materials)


def canonical_execution_plan_json(plan: dict[str, Any]) -> str:
    validate_execution_plan(plan)
    return json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def execution_plan_fingerprint(plan: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_execution_plan_json(plan).encode("utf-8")).hexdigest()


__all__ = [
    "EXECUTION_PLAN_FORMAT",
    "ExecutionPlanValidationError",
    "validate_execution_plan",
    "canonical_execution_plan_json",
    "execution_plan_fingerprint",
]
