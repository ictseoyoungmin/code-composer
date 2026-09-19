from __future__ import annotations

from .base import InstrumentEngine, InstrumentEngineValidationError

_ENGINES: dict[str, InstrumentEngine] = {}
_ALIASES: dict[str, str] = {}
_BUILTINS_READY = False


def register_engine(engine: InstrumentEngine, *, replace: bool = False) -> None:
    name = str(engine.name).strip()
    if not name:
        raise ValueError("instrument engine name must be non-empty")
    if not replace and name in _ENGINES:
        raise ValueError(f"instrument engine already registered: {name}")
    _ENGINES[name] = engine
    for alias in (name, *engine.aliases):
        alias = str(alias).strip()
        if not alias:
            continue
        if not replace and alias in _ALIASES and _ALIASES[alias] != name:
            raise ValueError(f"instrument engine alias already registered: {alias}")
        _ALIASES[alias] = name


def _ensure_builtins() -> None:
    global _BUILTINS_READY
    if _BUILTINS_READY:
        return
    from .generic import GenericSynthEngine
    from .piano import PianoEngine
    from .bowed_string import BowedStringEngine
    from .bowed_waveguide import BowedWaveguideEngine
    from .plucked_bass import PluckedBassEngine
    from .percussion import PercussionEngine
    register_engine(GenericSynthEngine())
    register_engine(PianoEngine())
    register_engine(BowedStringEngine())
    register_engine(BowedWaveguideEngine())
    register_engine(PluckedBassEngine())
    register_engine(PercussionEngine())
    _BUILTINS_READY = True


def registered_engines() -> tuple[str, ...]:
    _ensure_builtins()
    return tuple(sorted(_ENGINES))


def _legacy_engine_hint(patch: dict) -> str:
    if patch.get("kind") == "piano" or "piano_graph" in patch or "electric_piano_graph" in patch or "piano_design" in patch:
        return "piano"
    if patch.get("kind") == "bowed_string" or "bowed_string_graph" in patch:
        return "bowed_string"
    if patch.get("kind") == "percussion" or "drum_graph" in patch:
        return "percussion"
    return "generic"


def engine_name_for_patch(patch: dict) -> str:
    _ensure_builtins()
    if not isinstance(patch, dict):
        raise InstrumentEngineValidationError("instrument patch must be an object")
    requested = patch.get("engine")
    hint = str(requested).strip() if requested is not None else _legacy_engine_hint(patch)
    canonical = _ALIASES.get(hint)
    if canonical is None:
        raise InstrumentEngineValidationError(f"unknown instrument engine: {hint}")
    return canonical


def engine_for_patch(patch: dict) -> InstrumentEngine:
    return _ENGINES[engine_name_for_patch(patch)]


def validate_ir_patch(subject: str, patch: dict) -> None:
    engine_for_patch(patch).validate_ir_patch(subject, patch)


def validate_runtime_patch(subject: str, patch: dict) -> None:
    engine_for_patch(patch).validate_runtime_patch(subject, patch)


def validate_authoring_patch(role: str, patch: dict) -> None:
    engine_for_patch(patch).validate_authoring_patch(role, patch)


def engine_capabilities(patch: dict) -> dict:
    return engine_for_patch(patch).describe()


__all__ = [
    "InstrumentEngineValidationError",
    "register_engine",
    "registered_engines",
    "engine_name_for_patch",
    "engine_for_patch",
    "validate_ir_patch",
    "validate_runtime_patch",
    "validate_authoring_patch",
    "engine_capabilities",
]
