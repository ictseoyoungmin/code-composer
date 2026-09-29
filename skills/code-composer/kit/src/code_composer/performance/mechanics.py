"""Instrument-mechanics realizer registry.

This layer keeps performance-domain realizers out of audio-engine modules, preserving
the package import DAG while letting an engine declaratively select a realizer.
"""
from __future__ import annotations

from typing import Callable


class InstrumentMechanicsError(ValueError):
    pass


_REALIZERS: dict[str, Callable[[dict, str, dict], dict]] = {}
_BUILTINS_READY = False


def register_mechanics_realizer(name: str, fn: Callable[[dict, str, dict], dict], *, replace: bool = False) -> None:
    key = str(name).strip()
    if not key:
        raise ValueError("mechanics realizer name must be non-empty")
    if not callable(fn):
        raise TypeError("mechanics realizer must be callable")
    if key in _REALIZERS and not replace:
        raise ValueError(f"mechanics realizer already registered: {key}")
    _REALIZERS[key] = fn


def _ensure_builtins() -> None:
    global _BUILTINS_READY
    if _BUILTINS_READY:
        return

    from .violin import ViolinPerformanceError, realize_violin_performance
    from .guitar import (
        GuitarFingeringError,
        GuitarRightHandError,
        GuitarLeftHandError,
        realize_guitar_performance,
    )

    def _violin(ir: dict, track_id: str, plan_instrument: dict) -> dict:
        if plan_instrument.get("family") != "violin":
            return ir
        try:
            return realize_violin_performance(ir, track_id, config={"strict_comfort": True})
        except ViolinPerformanceError as exc:
            raise InstrumentMechanicsError(str(exc)) from exc

    def _acoustic_guitar(ir: dict, track_id: str, plan_instrument: dict) -> dict:
        if plan_instrument.get("family") != "acoustic_guitar":
            return ir
        try:
            return realize_guitar_performance(ir, track_id, plan_instrument)
        except (GuitarFingeringError, GuitarRightHandError, GuitarLeftHandError) as exc:
            raise InstrumentMechanicsError(str(exc)) from exc

    register_mechanics_realizer("violin", _violin)
    register_mechanics_realizer("acoustic_guitar", _acoustic_guitar)
    _BUILTINS_READY = True


def realize_registered_mechanics(engine, ir: dict, track_id: str, plan_instrument: dict) -> dict:
    key = getattr(engine, "mechanics_realizer", None)
    if key is None:
        return ir
    _ensure_builtins()
    fn = _REALIZERS.get(str(key))
    if fn is None:
        raise InstrumentMechanicsError(
            f"engine {getattr(engine, 'name', '<unknown>')!r} references unknown mechanics realizer {key!r}"
        )
    return fn(ir, track_id, plan_instrument)


__all__ = [
    "InstrumentMechanicsError",
    "register_mechanics_realizer",
    "realize_registered_mechanics",
]
