"""AG08-S6 passive-energy and stability diagnostics.

This module is deliberately non-rendering: it does not change the sound path.
It evaluates the already-active S1-S5 equations and reports conservative
stability/passivity quantities for CI and evidence generation.
"""
from __future__ import annotations

import math
import numpy as np

from .body import _BODY_MODES
from .stateful import (
    _shared_body_loading_curve,
    _string_contact_loading_curve,
    _technique_carry_tau_scale,
    stateful_config,
)


def _modal_pole_radius(freq_hz: float, q: float, sr: int) -> float:
    freq_hz = max(20.0, min(float(freq_hz), float(sr) * 0.45))
    q = max(0.5, float(q))
    return float(math.exp(-math.pi * freq_hz / (q * float(sr))))


def body_pole_certificate(sr: int, graph: dict) -> dict:
    """Return exact pole radii used by the current body modal resonators."""
    sr = int(sr)
    shift = float(graph.get("body_mode_shift", 1.0))
    damping = max(0.55, float(graph.get("body_mode_damping", 1.0)))
    radii = []
    for freq, q, _gain in _BODY_MODES:
        radii.append(
            _modal_pole_radius(float(freq) * shift, float(q) / damping, sr)
        )

    air_radius = _modal_pole_radius(
        float(graph.get("air_mode_hz", 108.0)),
        float(graph.get("air_mode_q", 1.35)),
        sr,
    )
    all_radii = radii + [air_radius]
    return {
        "body_mode_radii": radii,
        "air_mode_radius": air_radius,
        "max_pole_radius": max(all_radii),
        "all_strictly_inside_unit_circle": all(0.0 <= r < 1.0 for r in all_radii),
    }


def passive_transition_certificate(sr: int, patch: dict) -> dict:
    """Conservative certificate for S2-S5 state transforms.

    The certificate is about internal state transforms, not loudspeaker-domain
    waveform L2 gain. Body radiation is feed-forward and may color/amplify some
    frequencies; it is not fed back into string/bridge state.
    """
    graph = patch.get("acoustic_guitar_graph", {}) if isinstance(patch, dict) else {}
    cfg = stateful_config(graph)

    same_memory = max(0.0, min(0.98, float(cfg.get("same_string_memory", 0.0))))
    bridge_memory = max(0.0, min(0.98, float(cfg.get("bridge_memory", 0.0))))
    action_memory = max(0.0, min(0.98, float(cfg.get("action_body_memory", 0.0))))
    transition_memory = max(
        0.0, min(0.98, float(cfg.get("technique_transition_memory", 0.0)))
    )
    cross = max(0.0, min(0.98, float(cfg.get("cross_string_coupling", 0.0))))
    sympathetic = max(0.0, min(0.98, float(cfg.get("sympathetic_gain", 0.0))))

    # S3 loading: sample representative residual states across the full bounded
    # RMS weighting interval. Every curve must start at 1 and never exceed it.
    body_curves = []
    for memory in (bridge_memory, action_memory):
        for residual_rms in (0.0, 0.02, 0.05, 0.10, 0.20):
            curve = _shared_body_loading_curve(
                memory, residual_rms, int(sr), max(64, int(0.25 * int(sr)))
            )
            body_curves.append(curve)

    body_max = max(float(np.max(x)) for x in body_curves) if body_curves else 1.0
    body_min = min(float(np.min(x)) for x in body_curves) if body_curves else 1.0
    body_nonincreasing = all(
        bool(np.all(np.diff(x) <= 1e-12)) for x in body_curves
    )

    # S5 contact loading at the strongest valid authored strength and several
    # residual levels. These curves multiply already-existing state only.
    contact_curves = []
    for action in ("muted_strum", "dead_strum", "string_slap"):
        for residual_rms in (0.0, 0.02, 0.05, 0.08, 0.16):
            curve = _string_contact_loading_curve(
                transition_memory,
                action,
                1.0,
                residual_rms,
                int(sr),
                max(64, int(0.25 * int(sr))),
            )
            contact_curves.append(curve)

    contact_max = max(float(np.max(x)) for x in contact_curves)
    contact_min = min(float(np.min(x)) for x in contact_curves)
    contact_nonincreasing = all(
        bool(np.all(np.diff(x) <= 1e-12)) for x in contact_curves
    )

    # S4 bridge-domain allocation is explicitly quadratic-energy bounded.
    transfer_budget = min(0.12, cross * sympathetic)
    source_keep = math.sqrt(max(0.0, 1.0 - transfer_budget))
    accounting = source_keep * source_keep + transfer_budget

    # S2/S5 same-string carry changes only positive decay constants. Check the
    # full technique set used by AG04/S5.
    technique_scales = {}
    for technique in (
        "",
        "slide",
        "hammer_on",
        "pull_off",
        "natural_harmonic",
        "palm_mute",
        "fretting_mute",
        "dead_note",
    ):
        event = {
            "performance": {
                "left_hand_realization": {"technique": technique}
            }
        }
        technique_scales[technique or "ordinary"] = _technique_carry_tau_scale(
            event, transition_memory
        )

    body = body_pole_certificate(int(sr), graph)
    passive = (
        body["all_strictly_inside_unit_circle"]
        and body_max <= 1.0 + 1e-12
        and body_nonincreasing
        and contact_max <= 1.0 + 1e-12
        and contact_nonincreasing
        and 0.0 <= transfer_budget <= 0.12 + 1e-12
        and abs(accounting - 1.0) <= 1e-12
        and same_memory >= 0.0
        and all(scale > 0.0 for scale in technique_scales.values())
    )

    return {
        "passive_internal_state_transforms": bool(passive),
        "body": body,
        "shared_body_loading": {
            "max_multiplier": body_max,
            "min_multiplier": body_min,
            "nonincreasing": body_nonincreasing,
        },
        "string_contact_loading": {
            "max_multiplier": contact_max,
            "min_multiplier": contact_min,
            "nonincreasing": contact_nonincreasing,
        },
        "sympathetic_bridge_energy": {
            "configured_budget": transfer_budget,
            "source_keep": source_keep,
            "source_keep_squared_plus_budget": accounting,
        },
        "same_string": {
            "memory": same_memory,
            "technique_carry_tau_scales": technique_scales,
            "all_decay_scales_positive": all(
                scale > 0.0 for scale in technique_scales.values()
            ),
        },
        "scope_note": (
            "Certificate covers internal forward state transforms. "
            "Body radiation is feed-forward and is validated separately by "
            "finite-impulse / no-input-decay evidence."
        ),
    }


__all__ = ["body_pole_certificate", "passive_transition_certificate"]
