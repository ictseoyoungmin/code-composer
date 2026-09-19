"""Aggregate validation across core IR and runtime domain contracts."""
from ..core.ir import IRValidationError, validate_ir as validate_core_ir
from ..mix.mixer import MixGraphError, validate_mix_graph
from ..validation_contracts import ContractValidationError, validate_runtime_extensions
from ..composition.performance import validate_ir_performance_contract
from ..agent.performance_ir import PerformanceIRValidationError
from ..composition.register_voicing import RegisterVoicingError
from ..composition.orchestration_budget import OrchestrationBudgetError
from ..composition.ensemble_interaction import EnsembleInteractionError

def validate_ir(ir: dict) -> None:
    validate_core_ir(ir)
    try:
        validate_runtime_extensions(ir)
        validate_ir_performance_contract(ir)
    except (ContractValidationError, PerformanceIRValidationError, RegisterVoicingError, OrchestrationBudgetError, EnsembleInteractionError) as exc:
        raise IRValidationError(str(exc)) from exc
    graph = ir.get("mix", {}).get("graph")
    if graph is not None:
        validate_mix_graph(graph, {t.get("id") for t in ir.get("tracks", [])})

__all__ = [
    "IRValidationError", "MixGraphError", "ContractValidationError", "PerformanceIRValidationError", "RegisterVoicingError", "OrchestrationBudgetError", "EnsembleInteractionError",
    "validate_ir", "validate_core_ir",
]
