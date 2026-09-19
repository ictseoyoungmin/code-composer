"""Compatibility shim preserving full IR validation semantics."""
from .pipeline.validation import IRValidationError, MixGraphError, validate_ir

__all__ = ["IRValidationError", "MixGraphError", "validate_ir"]
