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
    "GuitarRightHandError",
    "RIGHT_HAND_METHODS",
    "resolve_right_hand",
    "realize_guitar_right_hand",
    "realize_guitar_performance",
]

from .right_hand import (
    GuitarRightHandError,
    RIGHT_HAND_METHODS,
    realize_guitar_right_hand,
    resolve_right_hand,
)


def realize_guitar_performance(ir, track_id, plan_instrument):
    """Compose AG02 fingering and AG03 right-hand realization."""
    out = realize_guitar_fingering(ir, track_id, plan_instrument)
    return realize_guitar_right_hand(out, track_id, plan_instrument)
