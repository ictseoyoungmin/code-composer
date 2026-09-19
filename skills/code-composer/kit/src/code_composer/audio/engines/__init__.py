"""Instrument engine boundary. Normal callers use the registry, not engine modules directly."""
from .base import InstrumentEngine, EngineCapabilities, InstrumentEngineValidationError
from .registry import (
    register_engine,
    registered_engines,
    engine_name_for_patch,
    engine_for_patch,
    validate_ir_patch,
    validate_runtime_patch,
    validate_authoring_patch,
    engine_capabilities,
)

__all__ = [
    "InstrumentEngine", "EngineCapabilities", "InstrumentEngineValidationError",
    "register_engine", "registered_engines", "engine_name_for_patch", "engine_for_patch",
    "validate_ir_patch", "validate_runtime_patch", "validate_authoring_patch", "engine_capabilities",
]
