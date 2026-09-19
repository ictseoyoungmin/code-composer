"""Agent-authored composition and expressive-performance contracts.

Natural-language interpretation belongs to the external Composer Agent.
This package validates and compiles explicit structured plans.
"""

from .composition_brief import CompositionBrief, BriefValidationError
from .expressive_score_plan import (
    ExpressiveScorePlan,
    ExpressiveValidationContext,
    ExpressivePlanValidationError,
    expressive_score_plan_from_dict,
    expressive_score_plan_to_dict,
    validate_expressive_score_plan,
    build_validation_context_from_composition,
)
from .performance_ir import (
    PerformanceIR,
    PerformanceIRValidationError,
    compile_performance_ir,
    validate_performance_ir,
    performance_ir_from_dict,
    performance_ir_to_dict,
)

__all__=[
    "CompositionBrief","BriefValidationError",
    "ExpressiveScorePlan","ExpressiveValidationContext","ExpressivePlanValidationError",
    "expressive_score_plan_from_dict","expressive_score_plan_to_dict",
    "validate_expressive_score_plan","build_validation_context_from_composition",
    "PerformanceIR","PerformanceIRValidationError",
    "compile_performance_ir","validate_performance_ir",
    "performance_ir_from_dict","performance_ir_to_dict",
]
