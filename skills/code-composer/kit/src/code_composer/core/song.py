"""CR01 canonical Composer-first Song model.

The Song document is the authored musical state. It deliberately does not depend on
seed IR, legacy arrangement roles, or renderer implementation details unless an
instrument explicitly carries a render_lock.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re
from typing import Any

from .theory import NOTE_TO_PC, SCALES


SONG_FORMAT = "code-composer-song/v1"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_BEAT_UNITS = {1, 2, 4, 8, 16, 32}


class SongValidationError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise SongValidationError(f"{path}: {message}")


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
        raise SongValidationError(f"{path}: must be numeric") from exc
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


def _unique_id_map(items: list, path: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i, item in enumerate(items):
        item = _object(item, f"{path}[{i}]")
        ident = _identifier(item.get("id"), f"{path}[{i}].id")
        if ident in out:
            _fail(path, f"duplicate id: {ident}")
        out[ident] = item
    return out


def _validate_meta(song: dict) -> None:
    meta = _object(song["meta"], "meta")
    _strict(meta, "meta", required={"title", "global_seed"}, optional={"revision"})
    _string(meta["title"], "meta.title")
    _integer(meta["global_seed"], "meta.global_seed", 0, 2**63 - 1)
    if "revision" in meta:
        _string(meta["revision"], "meta.revision")


def _validate_intent(song: dict) -> None:
    if "intent" not in song:
        return
    intent = _object(song["intent"], "intent")
    _strict(intent, "intent", optional={"concept", "notes"})
    if "concept" in intent:
        _string(intent["concept"], "intent.concept")
    if "notes" in intent:
        notes = _array(intent["notes"], "intent.notes")
        for i, note in enumerate(notes):
            _string(note, f"intent.notes[{i}]")


def _validate_transport(song: dict) -> tuple[float, int]:
    transport = _object(song["transport"], "transport")
    _strict(transport, "transport", required={"bpm", "meter"})
    bpm = _number(transport["bpm"], "transport.bpm", 20, 400)
    meter = _object(transport["meter"], "transport.meter")
    _strict(meter, "transport.meter", required={"beats_per_bar", "beat_unit"})
    beats = _integer(meter["beats_per_bar"], "transport.meter.beats_per_bar", 1, 32)
    beat_unit = _integer(meter["beat_unit"], "transport.meter.beat_unit")
    if beat_unit not in _BEAT_UNITS:
        _fail("transport.meter.beat_unit", f"must be one of {sorted(_BEAT_UNITS)}")
    return bpm, beats


def _validate_tonal(song: dict) -> tuple[str | None, str | None]:
    tonal = song.get("tonal")
    if tonal is None:
        return None, None
    tonal = _object(tonal, "tonal")
    _strict(tonal, "tonal", required={"root", "scale"})
    root = _string(tonal["root"], "tonal.root")
    scale = _string(tonal["scale"], "tonal.scale")
    if root not in NOTE_TO_PC:
        _fail("tonal.root", f"unsupported root: {root}")
    if scale not in SCALES:
        _fail("tonal.scale", f"unsupported scale: {scale}")
    return root, scale


def _validate_sections(song: dict) -> dict[str, dict]:
    sections = _array(song["sections"], "sections", nonempty=True)
    section_map = _unique_id_map(sections, "sections")
    for i, section in enumerate(sections):
        path = f"sections[{i}]"
        _strict(
            section, path,
            required={"id", "bars"},
            optional={"name", "energy", "intent"},
        )
        _integer(section["bars"], f"{path}.bars", 1, 100000)
        if "name" in section:
            _string(section["name"], f"{path}.name")
        if "energy" in section:
            _number(section["energy"], f"{path}.energy", 0, 1)
        if "intent" in section:
            _string(section["intent"], f"{path}.intent")
    return section_map


def _validate_instruments(song: dict) -> dict[str, dict]:
    instruments = _array(song["instruments"], "instruments", nonempty=True)
    instrument_map = _unique_id_map(instruments, "instruments")
    for i, instrument in enumerate(instruments):
        path = f"instruments[{i}]"
        _strict(
            instrument, path,
            required={"id", "family"},
            optional={"name", "variant", "render_lock"},
        )
        _string(instrument["family"], f"{path}.family")
        if "name" in instrument:
            _string(instrument["name"], f"{path}.name")
        if "variant" in instrument:
            _string(instrument["variant"], f"{path}.variant")
        if "render_lock" in instrument:
            lock = _object(instrument["render_lock"], f"{path}.render_lock")
            _strict(
                lock, f"{path}.render_lock",
                optional={"engine", "preset", "preset_version"},
            )
            if "engine" not in lock and "preset" not in lock:
                _fail(f"{path}.render_lock", "requires engine and/or preset")
            if "engine" in lock:
                _string(lock["engine"], f"{path}.render_lock.engine")
            if "preset" in lock:
                _string(lock["preset"], f"{path}.render_lock.preset")
            if "preset_version" in lock:
                if "preset" not in lock:
                    _fail(f"{path}.render_lock.preset_version", "requires preset")
                _string(lock["preset_version"], f"{path}.render_lock.preset_version")
    return instrument_map


def _validate_tracks(song: dict, instrument_map: dict[str, dict]) -> dict[str, dict]:
    tracks = _array(song["tracks"], "tracks", nonempty=True)
    track_map = _unique_id_map(tracks, "tracks")
    for i, track in enumerate(tracks):
        path = f"tracks[{i}]"
        _strict(track, path, required={"id", "function", "instrument"}, optional={"name"})
        _string(track["function"], f"{path}.function")
        instrument = _identifier(track["instrument"], f"{path}.instrument")
        if instrument not in instrument_map:
            _fail(f"{path}.instrument", f"unknown instrument: {instrument}")
        if "name" in track:
            _string(track["name"], f"{path}.name")
    return track_map


def _validate_materials(song: dict) -> dict[str, dict]:
    materials = _array(song["materials"], "materials", nonempty=True)
    material_map = _unique_id_map(materials, "materials")
    for i, material in enumerate(materials):
        path = f"materials[{i}]"
        kind = material.get("kind")
        if kind == "motif":
            _strict(material, path, required={"id", "kind", "intervals", "rhythm"})
            intervals = _array(material["intervals"], f"{path}.intervals", nonempty=True)
            rhythm = _array(material["rhythm"], f"{path}.rhythm", nonempty=True)
            if len(intervals) != len(rhythm):
                _fail(path, "motif intervals/rhythm length mismatch")
            for j, interval in enumerate(intervals):
                _integer(interval, f"{path}.intervals[{j}]", -127, 127)
            for j, duration in enumerate(rhythm):
                _number(duration, f"{path}.rhythm[{j}]", 1e-9, 100000)
        elif kind == "progression":
            _strict(material, path, required={"id", "kind", "degrees"}, optional={"rhythm"})
            degrees = _array(material["degrees"], f"{path}.degrees", nonempty=True)
            for j, degree in enumerate(degrees):
                _integer(degree, f"{path}.degrees[{j}]", 1, 32)
            if "rhythm" in material:
                rhythm = _array(material["rhythm"], f"{path}.rhythm", nonempty=True)
                if len(rhythm) != len(degrees):
                    _fail(path, "progression degrees/rhythm length mismatch")
                for j, duration in enumerate(rhythm):
                    _number(duration, f"{path}.rhythm[{j}]", 1e-9, 100000)
        elif kind == "rhythm":
            _strict(material, path, required={"id", "kind", "cycle_beats", "steps"})
            cycle = _number(material["cycle_beats"], f"{path}.cycle_beats", 1e-9, 100000)
            steps = _array(material["steps"], f"{path}.steps", nonempty=True)
            for j, step in enumerate(steps):
                sp = f"{path}.steps[{j}]"
                step = _object(step, sp)
                _strict(step, sp, required={"beat", "weight"}, optional={"duration"})
                beat = _number(step["beat"], f"{sp}.beat", 0, cycle)
                if beat >= cycle:
                    _fail(f"{sp}.beat", "must be < cycle_beats")
                _number(step["weight"], f"{sp}.weight", 0, 2)
                if "duration" in step:
                    _number(step["duration"], f"{sp}.duration", 1e-9, cycle)
        else:
            _fail(f"{path}.kind", "must be motif, progression, or rhythm")
    return material_map


def _validate_parts(
    song: dict,
    section_map: dict[str, dict],
    track_map: dict[str, dict],
    material_map: dict[str, dict],
    beats_per_bar: int,
) -> dict[str, dict]:
    parts = _array(song["parts"], "parts", nonempty=True)
    part_map = _unique_id_map(parts, "parts")
    for i, part in enumerate(parts):
        path = f"parts[{i}]"
        _strict(
            part, path,
            required={"id", "section", "track", "material"},
            optional={"start_beat", "repeats", "intent"},
        )
        section = _identifier(part["section"], f"{path}.section")
        track = _identifier(part["track"], f"{path}.track")
        material = _identifier(part["material"], f"{path}.material")
        if section not in section_map:
            _fail(f"{path}.section", f"unknown section: {section}")
        if track not in track_map:
            _fail(f"{path}.track", f"unknown track: {track}")
        if material not in material_map:
            _fail(f"{path}.material", f"unknown material: {material}")
        start = _number(part.get("start_beat", 0), f"{path}.start_beat", 0)
        section_beats = int(section_map[section]["bars"]) * beats_per_bar
        if start >= section_beats:
            _fail(f"{path}.start_beat", f"must be inside section (< {section_beats})")
        if "repeats" in part:
            _integer(part["repeats"], f"{path}.repeats", 1, 100000)
        if "intent" in part:
            _string(part["intent"], f"{path}.intent")
    return part_map


def _validate_locks(song: dict, bpm: float, root: str | None, scale: str | None) -> None:
    if "locks" not in song:
        return
    locks = _object(song["locks"], "locks")
    _strict(locks, "locks", optional={"bpm", "root", "scale"})
    if "bpm" in locks:
        locked = _number(locks["bpm"], "locks.bpm", 20, 400)
        if locked != bpm:
            _fail("locks.bpm", f"conflicts with transport.bpm ({bpm:g})")
    if "root" in locks:
        locked = _string(locks["root"], "locks.root")
        if root is None:
            _fail("locks.root", "requires tonal")
        if locked != root:
            _fail("locks.root", f"conflicts with tonal.root ({root})")
    if "scale" in locks:
        locked = _string(locks["scale"], "locks.scale")
        if scale is None:
            _fail("locks.scale", "requires tonal")
        if locked != scale:
            _fail("locks.scale", f"conflicts with tonal.scale ({scale})")


def validate_song(song: dict[str, Any]) -> None:
    song = _object(song, "song")
    _strict(
        song,
        "song",
        required={
            "format", "meta", "transport", "sections",
            "instruments", "tracks", "materials", "parts",
        },
        optional={"intent", "tonal", "locks"},
    )
    if song["format"] != SONG_FORMAT:
        _fail("format", f"must equal {SONG_FORMAT!r}")

    _validate_meta(song)
    _validate_intent(song)
    bpm, beats_per_bar = _validate_transport(song)
    root, scale = _validate_tonal(song)
    sections = _validate_sections(song)
    instruments = _validate_instruments(song)
    tracks = _validate_tracks(song, instruments)
    materials = _validate_materials(song)
    _validate_parts(song, sections, tracks, materials, beats_per_bar)
    _validate_locks(song, bpm, root, scale)


def song_from_dict(data: dict[str, Any]) -> dict[str, Any]:
    validate_song(data)
    return deepcopy(data)


def canonical_song_json(song: dict[str, Any]) -> str:
    validate_song(song)
    return json.dumps(song, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def song_fingerprint(song: dict[str, Any]) -> str:
    payload = canonical_song_json(song).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def song_summary(song: dict[str, Any]) -> dict[str, Any]:
    validate_song(song)
    return {
        "format": song["format"],
        "title": song["meta"]["title"],
        "fingerprint": song_fingerprint(song),
        "sections": len(song["sections"]),
        "instruments": len(song["instruments"]),
        "tracks": len(song["tracks"]),
        "materials": len(song["materials"]),
        "parts": len(song["parts"]),
    }


__all__ = [
    "SONG_FORMAT",
    "SongValidationError",
    "validate_song",
    "song_from_dict",
    "canonical_song_json",
    "song_fingerprint",
    "song_summary",
]
