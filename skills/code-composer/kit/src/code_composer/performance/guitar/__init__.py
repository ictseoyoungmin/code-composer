"""Acoustic-guitar performance mechanics."""
from .fingering import (
    GuitarFingeringError,
    MAX_FRET,
    STANDARD_TUNING,
    fingering_candidates,
    realize_guitar_fingering,
    resolve_fingering,
)

__all__ = [
    "GuitarFingeringError",
    "MAX_FRET",
    "STANDARD_TUNING",
    "fingering_candidates",
    "resolve_fingering",
    "realize_guitar_fingering",
]
