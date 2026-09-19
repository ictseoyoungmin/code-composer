"""Versioned factory preset registry and materialization.

Factory presets contain sound design only. They never contain notes, rhythms, chords,
progressions, arrangement events, or completed musical material.
"""
from __future__ import annotations

from copy import deepcopy
from importlib import resources
import json
from typing import Any

from .audio.engines import validate_authoring_patch, InstrumentEngineValidationError

FORMAT = "code-composer-factory-preset/v1"
_FORBIDDEN_MUSICAL_KEYS = {
    "notes", "note_events", "events", "melody", "motif", "motifs", "rhythm", "rhythms",
    "chords", "progression", "progressions", "arrangement", "form", "sections", "midi",
}

class PresetError(ValueError):
    pass


def _semver(v: str) -> tuple[int, int, int]:
    try:
        a,b,c=(int(x) for x in v.split("."))
        return a,b,c
    except Exception as exc:
        raise PresetError(f"invalid preset version: {v}") from exc


def _resource_dir():
    return resources.files("code_composer.reference").joinpath("presets")


def _validate_no_musical_content(value: Any, path: str = "preset") -> None:
    if isinstance(value, dict):
        for k,v in value.items():
            if str(k).lower() in _FORBIDDEN_MUSICAL_KEYS:
                raise PresetError(f"{path}: factory preset contains forbidden musical-content key {k!r}")
            _validate_no_musical_content(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i,v in enumerate(value):
            _validate_no_musical_content(v, f"{path}[{i}]")


def _validate_definition(d: dict) -> None:
    if not isinstance(d, dict) or d.get("format") != FORMAT:
        raise PresetError("invalid factory preset format")
    for key in ("preset_id","version","name","engine","character","strengths","limitations","recommended_roles","expression_capabilities","patch"):
        if key not in d:
            raise PresetError(f"preset missing {key}")
    if not d.get("preset_id") or not isinstance(d["preset_id"], str):
        raise PresetError("preset_id must be a non-empty string")
    _semver(str(d["version"]))
    if d.get("musical_content") is not False:
        raise PresetError("factory preset must declare musical_content=false")
    _validate_no_musical_content({k:v for k,v in d.items() if k != "patch"})
    _validate_no_musical_content(d["patch"])
    try:
        validate_authoring_patch("preset", d["patch"])
    except InstrumentEngineValidationError as exc:
        raise PresetError(str(exc)) from exc


def _definitions() -> list[dict]:
    out=[]
    root=_resource_dir()
    for item in sorted(root.iterdir(), key=lambda x: x.name):
        if item.name.endswith(".json"):
            d=json.loads(item.read_text(encoding="utf-8"))
            _validate_definition(d)
            out.append(d)
    return out


def list_presets(*, engine: str | None = None, family: str | None = None, role: str | None = None) -> list[dict]:
    result=[]
    for d in _definitions():
        if engine and d.get("engine") != engine: continue
        if family and d.get("family") != family: continue
        if role and role not in d.get("recommended_roles",[]): continue
        meta=deepcopy(d); meta.pop("patch",None)
        result.append(meta)
    return result


def get_preset(preset_id: str, version: str | None = None) -> dict:
    matches=[d for d in _definitions() if d["preset_id"] == preset_id]
    if version is not None:
        matches=[d for d in matches if d["version"] == version]
    if not matches:
        suffix=f"@{version}" if version else ""
        raise PresetError(f"unknown factory preset: {preset_id}{suffix}")
    matches.sort(key=lambda d:_semver(d["version"]), reverse=True)
    return deepcopy(matches[0])


def _deep_merge(base: dict, overrides: dict) -> dict:
    out=deepcopy(base)
    for k,v in overrides.items():
        if k in {"kind","engine","family","preset_provenance"}:
            raise PresetError(f"patch_overrides cannot replace identity field: {k}")
        if isinstance(v,dict) and isinstance(out.get(k),dict):
            out[k]=_deep_merge(out[k],v)
        else:
            out[k]=deepcopy(v)
    return out


def materialize_preset(preset_id: str, *, version: str | None = None, patch_overrides: dict | None = None, role: str = "preset") -> dict:
    d=get_preset(preset_id,version)
    patch=deepcopy(d["patch"])
    if patch_overrides:
        if not isinstance(patch_overrides,dict):
            raise PresetError("patch_overrides must be an object")
        _validate_no_musical_content(patch_overrides,"patch_overrides")
        patch=_deep_merge(patch,patch_overrides)
    try:
        validate_authoring_patch(role,patch)
    except InstrumentEngineValidationError as exc:
        raise PresetError(str(exc)) from exc
    patch["preset_provenance"]={
        "preset_id":d["preset_id"],
        "preset_version":d["version"],
        "materialized":True,
    }
    return patch


__all__=["PresetError","list_presets","get_preset","materialize_preset"]
