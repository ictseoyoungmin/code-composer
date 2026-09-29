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
    "GuitarLeftHandError",
    "LEFT_HAND_TECHNIQUES",
    "resolve_left_hand",
    "realize_guitar_left_hand",
]

from .right_hand import (
    GuitarRightHandError,
    RIGHT_HAND_METHODS,
    realize_guitar_right_hand,
    resolve_right_hand,
)


def realize_guitar_performance(ir, track_id, plan_instrument):
    """Compose AG02 fingering, AG03 right hand, and AG04 left hand."""
    out = realize_guitar_fingering(ir, track_id, plan_instrument)
    out = realize_guitar_right_hand(out, track_id, plan_instrument)
    return realize_guitar_left_hand(out, track_id, plan_instrument)

from .left_hand import (
    GuitarLeftHandError,
    LEFT_HAND_TECHNIQUES,
    realize_guitar_left_hand,
    resolve_left_hand,
)
