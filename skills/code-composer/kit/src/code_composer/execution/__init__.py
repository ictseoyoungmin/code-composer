"""Composer-first execution-plan boundary introduced by CR02."""

from .plan import (
    EXECUTION_PLAN_FORMAT,
    ExecutionPlanValidationError,
    canonical_execution_plan_json,
    execution_plan_fingerprint,
    validate_execution_plan,
)
from .lowering import SongLoweringError, lower_song_to_execution_plan

__all__ = [
    "EXECUTION_PLAN_FORMAT",
    "ExecutionPlanValidationError",
    "SongLoweringError",
    "validate_execution_plan",
    "canonical_execution_plan_json",
    "execution_plan_fingerprint",
    "lower_song_to_execution_plan",
]
