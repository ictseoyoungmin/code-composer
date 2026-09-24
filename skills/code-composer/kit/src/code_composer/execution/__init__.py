"""Composer-first execution-plan boundary introduced by CR02."""

from .plan import (
    EXECUTION_PLAN_FORMAT,
    ExecutionPlanValidationError,
    canonical_execution_plan_json,
    execution_plan_fingerprint,
    validate_execution_plan,
)
from .lowering import SongLoweringError, lower_song_to_execution_plan
from .performance_score import (
    PERFORMANCE_SCORE_FORMAT,
    PerformanceScoreValidationError,
    canonical_performance_score_json,
    performance_score_fingerprint,
    validate_performance_score,
)
from .render_bridge import (
    PerformanceBridgeError,
    compile_performance_score_to_render_ir,
    realize_instrument_mechanics,
)
from .artistic_render import render_song_score_to_files

__all__ = [
    "EXECUTION_PLAN_FORMAT",
    "ExecutionPlanValidationError",
    "SongLoweringError",
    "validate_execution_plan",
    "canonical_execution_plan_json",
    "execution_plan_fingerprint",
    "lower_song_to_execution_plan",
    "PERFORMANCE_SCORE_FORMAT",
    "PerformanceScoreValidationError",
    "validate_performance_score",
    "canonical_performance_score_json",
    "performance_score_fingerprint",
    "PerformanceBridgeError",
    "compile_performance_score_to_render_ir",
    "realize_instrument_mechanics",
    "render_song_score_to_files",
]
