"""CR02 lowering from canonical Song to deterministic Execution Plan."""
from __future__ import annotations

from copy import deepcopy

from ..audio.engines import (
    engine_name_for_patch,
    validate_runtime_patch,
    InstrumentEngineValidationError,
)
from ..core.song import song_fingerprint
from ..core.theory import SCALES
from ..presets import PresetError, get_preset, materialize_preset
from ..song_validation import validate_song_for_runtime
from .plan import EXECUTION_PLAN_FORMAT, validate_execution_plan


class SongLoweringError(ValueError):
    pass


_CANONICAL_DEFAULT_PRESETS = {
    ("piano", None): "piano.concert_grand_natural",
    ("piano", "acoustic-grand"): "piano.concert_grand_natural",
    ("violin", None): "bowed.violin.modeled_continuous",
    ("violin", "solo-arco"): "bowed.violin.modeled_continuous",
    ("bass", None): "bass.electric_finger_modeled",
    ("bass", "electric-finger"): "bass.electric_finger_modeled",
    ("drums", None): "drums.acoustic_kit_modeled",
    ("drums", "acoustic-kit"): "drums.acoustic_kit_modeled",
}

_CANONICAL_FAMILY_ENGINES = {
    "piano": "piano",
    "violin": "bowed_waveguide",
    "bass": "plucked_bass",
    "drums": "percussion",
}


def _default_preset_id(instrument: dict) -> str:
    family = instrument["family"]
    variant = instrument.get("variant")
    preset_id = _CANONICAL_DEFAULT_PRESETS.get((family, variant))
    if preset_id is None:
        suffix = f"/{variant}" if variant else ""
        raise SongLoweringError(
            f"instrument {instrument['id']}: no canonical runtime resolution for "
            f"{family}{suffix}; add an explicit render_lock.preset"
        )
    return preset_id


def _resolve_instrument(instrument: dict) -> dict:
    lock = instrument.get("render_lock") or {}
    explicit_preset = lock.get("preset")
    explicit_engine = lock.get("engine")

    if explicit_preset:
        preset_id = explicit_preset
        preset_version = lock.get("preset_version")
        resolution_source = "explicit_preset_lock"
    else:
        preset_id = _default_preset_id(instrument)
        preset_version = None
        resolution_source = "engine_lock_family_default" if explicit_engine else "family_default"

    try:
        definition = get_preset(preset_id, preset_version)
    except PresetError as exc:
        raise SongLoweringError(f"instrument {instrument['id']}: {exc}") from exc

    preset_engine = str(definition["engine"])
    expected_engine = _CANONICAL_FAMILY_ENGINES.get(instrument["family"])
    if expected_engine is not None and preset_engine != expected_engine:
        raise SongLoweringError(
            f"instrument {instrument['id']}: family {instrument['family']!r} "
            f"requires runtime engine {expected_engine!r}, preset uses {preset_engine!r}"
        )
    if explicit_engine is not None and explicit_engine != preset_engine:
        raise SongLoweringError(
            f"instrument {instrument['id']}: explicit engine {explicit_engine!r} "
            f"conflicts with resolved preset engine {preset_engine!r}"
        )

    try:
        patch = materialize_preset(
            preset_id,
            version=definition["version"],
            role=f"song-instrument:{instrument['id']}",
        )
        engine = engine_name_for_patch(patch)
        validate_runtime_patch(instrument["id"], patch)
    except (PresetError, InstrumentEngineValidationError) as exc:
        raise SongLoweringError(f"instrument {instrument['id']}: {exc}") from exc

    out = {
        "id": instrument["id"],
        "family": instrument["family"],
        "engine": engine,
        "patch": patch,
        "resolution": {
            "source": resolution_source,
            "preset_id": definition["preset_id"],
            "preset_version": definition["version"],
        },
    }
    if "name" in instrument:
        out["name"] = instrument["name"]
    if "variant" in instrument:
        out["variant"] = instrument["variant"]
    return out


def _material_duration(material: dict) -> float:
    kind = material["kind"]
    if kind == "motif":
        return float(sum(float(x) for x in material["rhythm"]))
    if kind == "progression":
        rhythm = material.get("rhythm")
        if not rhythm:
            raise SongLoweringError(
                f"material {material['id']}: progression rhythm is required for execution lowering"
            )
        return float(sum(float(x) for x in rhythm))
    if kind == "rhythm":
        return float(material["cycle_beats"])
    raise SongLoweringError(f"material {material['id']}: unsupported kind {kind!r}")


def _runtime_tonal(song: dict) -> dict | None:
    tonal = song.get("tonal")
    pitched = any(m["kind"] in {"motif", "progression"} for m in song["materials"])
    if pitched and tonal is None:
        raise SongLoweringError("pitched motif/progression material requires tonal for runtime lowering")
    if tonal is None:
        return None
    scale = tonal["scale"]
    if scale not in SCALES:
        raise SongLoweringError(
            f"tonal.scale {scale!r} is authored-valid but unsupported by the current runtime; "
            "do not silently remap it"
        )
    return deepcopy(tonal)


def lower_song_to_execution_plan(song: dict) -> dict:
    validate_song_for_runtime(song)
    tonal = _runtime_tonal(song)

    beats_per_bar = int(song["transport"]["meter"]["beats_per_bar"])
    sections = []
    section_map = {}
    cursor_bar = 0
    cursor_beat = 0.0
    for section in song["sections"]:
        duration = float(int(section["bars"]) * beats_per_bar)
        lowered = {
            "id": section["id"],
            "start_bar": cursor_bar,
            "bars": int(section["bars"]),
            "start_beat": cursor_beat,
            "duration_beats": duration,
        }
        for key in ("name", "energy", "intent"):
            if key in section:
                lowered[key] = deepcopy(section[key])
        sections.append(lowered)
        section_map[section["id"]] = lowered
        cursor_bar += int(section["bars"])
        cursor_beat += duration

    instruments = [_resolve_instrument(x) for x in song["instruments"]]
    instrument_map = {x["id"]: x for x in instruments}

    tracks = [deepcopy(x) for x in song["tracks"]]
    track_map = {x["id"]: x for x in tracks}

    materials = []
    material_map = {}
    for authored in song["materials"]:
        lowered = deepcopy(authored)
        lowered["duration_beats"] = _material_duration(authored)
        materials.append(lowered)
        material_map[authored["id"]] = lowered

    instances = []
    for part in song["parts"]:
        material = material_map[part["material"]]
        section = section_map[part["section"]]
        track = track_map[part["track"]]
        duration = float(material["duration_beats"])
        repeats = int(part.get("repeats", 1))
        local_start = float(part.get("start_beat", 0.0))
        section_duration = float(section["duration_beats"])
        if local_start + repeats * duration > section_duration + 1e-9:
            raise SongLoweringError(
                f"part {part['id']}: repeated material ends at local beat "
                f"{local_start + repeats * duration:g}, outside section "
                f"{part['section']} duration {section_duration:g}"
            )
        for repeat_index in range(repeats):
            instances.append({
                "id": f"{part['id']}.{repeat_index + 1}",
                "source_part": part["id"],
                "repeat_index": repeat_index,
                "section": part["section"],
                "track": part["track"],
                "instrument": track["instrument"],
                "material": part["material"],
                "material_kind": material["kind"],
                "start_beat": float(section["start_beat"]) + local_start + repeat_index * duration,
                "duration_beats": duration,
            })

    plan = {
        "format": EXECUTION_PLAN_FORMAT,
        "source_song": {
            "format": song["format"],
            "fingerprint": song_fingerprint(song),
        },
        "meta": {
            "title": song["meta"]["title"],
            "global_seed": int(song["meta"]["global_seed"]),
        },
        "transport": deepcopy(song["transport"]),
        "sections": sections,
        "instruments": instruments,
        "tracks": tracks,
        "materials": materials,
        "part_instances": instances,
    }
    if tonal is not None:
        plan["tonal"] = tonal

    validate_execution_plan(plan)
    return plan


__all__ = ["SongLoweringError", "lower_song_to_execution_plan"]
