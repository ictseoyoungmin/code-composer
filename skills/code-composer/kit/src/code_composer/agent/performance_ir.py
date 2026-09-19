from __future__ import annotations

from dataclasses import dataclass, asdict
from copy import deepcopy

from .expressive_score_plan import (
    ExpressiveScorePlan,
    ExpressiveValidationContext,
    ExpressivePlanValidationError,
    validate_expressive_score_plan,
)


class PerformanceIRValidationError(ValueError):
    pass


@dataclass(frozen=True)
class PerformanceIR:
    version: str
    phrases: tuple[dict, ...]
    motif_statements: tuple[dict, ...]
    register_plans: dict
    orchestration_sections: dict
    transitions: tuple[dict, ...]
    realization: dict


DEFAULT_REALIZATION={
    "seed":0,
    "microtiming":{"enabled":True,"max_abs_ms":12.0},
    "velocity_variation":{"enabled":True,"max_abs":0.025},
    "timing_quantization_guard_ms":1.0,
    "minimum_note_gap_ms":2.0,
}


def performance_ir_from_dict(data: dict) -> PerformanceIR:
    if not isinstance(data,dict):
        raise PerformanceIRValidationError("performance IR must be an object")
    required=(
        "version","phrases","motif_statements","register_plans",
        "orchestration_sections","transitions","realization",
    )
    missing=[k for k in required if k not in data]
    if missing:
        raise PerformanceIRValidationError(f"missing performance IR fields: {missing}")
    unknown=set(data)-set(required)
    if unknown:
        raise PerformanceIRValidationError(f"unknown performance IR fields: {sorted(unknown)}")
    return PerformanceIR(
        version=str(data["version"]),
        phrases=tuple(deepcopy(data["phrases"])),
        motif_statements=tuple(deepcopy(data["motif_statements"])),
        register_plans=deepcopy(data["register_plans"]),
        orchestration_sections=deepcopy(data["orchestration_sections"]),
        transitions=tuple(deepcopy(data["transitions"])),
        realization=deepcopy(data["realization"]),
    )


def performance_ir_to_dict(ir: PerformanceIR) -> dict:
    out=asdict(ir)
    out["phrases"]=[deepcopy(x) for x in ir.phrases]
    out["motif_statements"]=[deepcopy(x) for x in ir.motif_statements]
    out["transitions"]=[deepcopy(x) for x in ir.transitions]
    return out


def _num(v,name,lo=None,hi=None):
    if isinstance(v,bool):
        raise PerformanceIRValidationError(f"{name} must be numeric")
    try:
        x=float(v)
    except Exception as exc:
        raise PerformanceIRValidationError(f"{name} must be numeric") from exc
    if lo is not None and x<lo:
        raise PerformanceIRValidationError(f"{name} must be >= {lo}")
    if hi is not None and x>hi:
        raise PerformanceIRValidationError(f"{name} must be <= {hi}")
    return x


def _validate_realization(realization: dict) -> None:
    if not isinstance(realization,dict):
        raise PerformanceIRValidationError("realization must be an object")
    allowed={
        "seed","microtiming","velocity_variation",
        "timing_quantization_guard_ms","minimum_note_gap_ms","ensemble",
    }
    unknown=set(realization)-allowed
    if unknown:
        raise PerformanceIRValidationError(f"realization has unknown field(s): {sorted(unknown)}")
    if "seed" not in realization or isinstance(realization["seed"],bool) or not isinstance(realization["seed"],int):
        raise PerformanceIRValidationError("realization.seed must be integer")

    micro=realization.get("microtiming")
    if not isinstance(micro,dict) or set(micro)!={"enabled","max_abs_ms"}:
        raise PerformanceIRValidationError(
            "realization.microtiming must contain enabled and max_abs_ms only"
        )
    if not isinstance(micro["enabled"],bool):
        raise PerformanceIRValidationError("realization.microtiming.enabled must be boolean")
    _num(micro["max_abs_ms"],"realization.microtiming.max_abs_ms",0,30)

    vel=realization.get("velocity_variation")
    if not isinstance(vel,dict) or set(vel)!={"enabled","max_abs"}:
        raise PerformanceIRValidationError(
            "realization.velocity_variation must contain enabled and max_abs only"
        )
    if not isinstance(vel["enabled"],bool):
        raise PerformanceIRValidationError("realization.velocity_variation.enabled must be boolean")
    _num(vel["max_abs"],"realization.velocity_variation.max_abs",0,.15)

    if "timing_quantization_guard_ms" in realization:
        _num(
            realization["timing_quantization_guard_ms"],
            "realization.timing_quantization_guard_ms",0,20
        )
    if "minimum_note_gap_ms" in realization:
        _num(realization["minimum_note_gap_ms"],"realization.minimum_note_gap_ms",0,100)

    ensemble=realization.get("ensemble")
    if ensemble is not None:
        if not isinstance(ensemble,dict):
            raise PerformanceIRValidationError("realization.ensemble must be an object")
        unknown=set(ensemble)-{"enabled","role_pan_offsets"}
        if unknown:
            raise PerformanceIRValidationError(
                f"realization.ensemble has unknown field(s): {sorted(unknown)}"
            )
        enabled=ensemble.get("enabled",True)
        if not isinstance(enabled,bool):
            raise PerformanceIRValidationError("realization.ensemble.enabled must be boolean")
        pans=ensemble.get("role_pan_offsets",{})
        if not isinstance(pans,dict):
            raise PerformanceIRValidationError(
                "realization.ensemble.role_pan_offsets must be an object"
            )
        for role,value in pans.items():
            if not isinstance(role,str) or not role:
                raise PerformanceIRValidationError(
                    "realization.ensemble.role_pan_offsets keys must be non-empty strings"
                )
            _num(
                value,
                f"realization.ensemble.role_pan_offsets.{role}",
                -.5,.5,
            )


def validate_performance_ir(
    ir: PerformanceIR,
    context: ExpressiveValidationContext,
) -> None:
    if ir.version!="1.16":
        raise PerformanceIRValidationError("performance IR version must be 1.16")

    # Reuse the exact structural/cross-reference contract from ExpressiveScorePlan.
    structural=ExpressiveScorePlan(
        version=ir.version,
        narrative={"arc":"compiled performance IR structural validation"},
        phrases=ir.phrases,
        motif_statements=ir.motif_statements,
        register_plans=deepcopy(ir.register_plans),
        orchestration_sections=deepcopy(ir.orchestration_sections),
        transitions=ir.transitions,
    )
    try:
        validate_expressive_score_plan(structural,context)
    except ExpressivePlanValidationError as exc:
        raise PerformanceIRValidationError(str(exc)) from exc

    _validate_realization(ir.realization)


def compile_performance_ir(
    plan: ExpressiveScorePlan,
    context: ExpressiveValidationContext,
    *,
    seed: int,
    realization: dict | None = None,
) -> PerformanceIR:
    validate_expressive_score_plan(plan,context)
    cfg=deepcopy(DEFAULT_REALIZATION)
    cfg["seed"]=int(seed)
    if realization:
        if not isinstance(realization,dict):
            raise PerformanceIRValidationError("realization override must be an object")
        for key,value in realization.items():
            if key in {"microtiming","velocity_variation"} and isinstance(value,dict):
                cfg[key].update(deepcopy(value))
            else:
                cfg[key]=deepcopy(value)

    ir=PerformanceIR(
        version="1.16",
        phrases=tuple(deepcopy(plan.phrases)),
        motif_statements=tuple(deepcopy(plan.motif_statements)),
        register_plans=deepcopy(plan.register_plans),
        orchestration_sections=deepcopy(plan.orchestration_sections),
        transitions=tuple(deepcopy(plan.transitions)),
        realization=cfg,
    )
    validate_performance_ir(ir,context)
    return ir


__all__=[
    "PerformanceIRValidationError",
    "PerformanceIR",
    "DEFAULT_REALIZATION",
    "performance_ir_from_dict",
    "performance_ir_to_dict",
    "validate_performance_ir",
    "compile_performance_ir",
]
