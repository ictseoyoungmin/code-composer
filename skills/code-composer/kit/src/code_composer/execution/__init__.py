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
from .performance_revision import (
    REVISION_PLAN_FORMAT,
    REVISION_RECORD_FORMAT,
    PerformanceRevisionError,
    apply_revision_plan,
    canonical_revision_plan_json,
    revision_plan_fingerprint,
    validate_revision_plan,
)
from .revision_compare import (
    REVISION_COMPARISON_FORMAT,
    render_revision_comparison_to_dir,
)
from .preview import (
    PREVIEW_REQUEST_FORMAT,
    PREVIEW_REPORT_FORMAT,
    STEM_CACHE_FORMAT,
    STEM_CACHE_RENDERER_EPOCH,
    PreviewValidationError,
    validate_preview_request,
    canonical_preview_request_json,
    preview_request_fingerprint,
    render_song_score_preview,
)

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
    "REVISION_PLAN_FORMAT",
    "REVISION_RECORD_FORMAT",
    "PerformanceRevisionError",
    "validate_revision_plan",
    "canonical_revision_plan_json",
    "revision_plan_fingerprint",
    "apply_revision_plan",
    "REVISION_COMPARISON_FORMAT",
    "render_revision_comparison_to_dir",
    "PREVIEW_REQUEST_FORMAT",
    "PREVIEW_REPORT_FORMAT",
    "STEM_CACHE_FORMAT",
    "STEM_CACHE_RENDERER_EPOCH",
    "PreviewValidationError",
    "validate_preview_request",
    "canonical_preview_request_json",
    "preview_request_fingerprint",
    "render_song_score_preview",
]
