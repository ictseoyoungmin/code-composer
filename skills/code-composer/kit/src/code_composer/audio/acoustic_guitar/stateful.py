"""AG08 reduced-order persistent acoustic-guitar state.

S1 establishes the state contract and a strict zero-coupling bypass. It does not
change sound. Later AG08 slices may activate bounded same-string/body/cross-string
coupling only after preservation and passive-energy gates pass.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


STATE_MODEL = "ag08_reduced_order_state_v1"


@dataclass
class AcousticGuitarState:
    model: str
    sample_rate: int
    sample_index: int
    string_energy: np.ndarray
    string_phase_proxy: np.ndarray
    bridge_state: np.ndarray
    body_state: np.ndarray
    active_fret: np.ndarray

    def copy(self) -> "AcousticGuitarState":
        return AcousticGuitarState(
            model=self.model,
            sample_rate=self.sample_rate,
            sample_index=self.sample_index,
            string_energy=self.string_energy.copy(),
            string_phase_proxy=self.string_phase_proxy.copy(),
            bridge_state=self.bridge_state.copy(),
            body_state=self.body_state.copy(),
            active_fret=self.active_fret.copy(),
        )


def stateful_config(graph: dict) -> dict:
    cfg = graph.get("stateful_coupling")
    return cfg if isinstance(cfg, dict) else {}


def stateful_enabled(graph: dict) -> bool:
    cfg = stateful_config(graph)
    return bool(cfg.get("enabled", False))


def coupling_is_zero(graph: dict) -> bool:
    cfg = stateful_config(graph)
    return all(
        abs(float(cfg.get(key, 0.0))) <= 1e-15
        for key in (
            "same_string_memory",
            "bridge_memory",
            "cross_string_coupling",
            "sympathetic_gain",
            "action_body_memory",
        )
    )


def initialize_acoustic_guitar_state(sr: int, graph: dict) -> AcousticGuitarState:
    """Create deterministic zero-energy AG08 state.

    The compact arrays are intentionally generic project-owned state variables.
    S1 makes no measured-body or externally fitted state claim.
    """
    cfg = stateful_config(graph)
    body_order = max(2, min(32, int(cfg.get("body_state_order", 10))))
    bridge_order = max(1, min(8, int(cfg.get("bridge_state_order", 2))))
    return AcousticGuitarState(
        model=STATE_MODEL,
        sample_rate=int(sr),
        sample_index=0,
        string_energy=np.zeros(6, dtype=np.float64),
        string_phase_proxy=np.zeros(6, dtype=np.float64),
        bridge_state=np.zeros(bridge_order, dtype=np.float64),
        body_state=np.zeros(body_order, dtype=np.float64),
        active_fret=np.full(6, -1, dtype=np.int16),
    )


def state_energy(state: AcousticGuitarState) -> float:
    """Diagnostic quadratic energy proxy used by later passive-state gates."""
    return float(
        np.dot(state.string_energy, state.string_energy)
        + np.dot(state.string_phase_proxy, state.string_phase_proxy)
        + np.dot(state.bridge_state, state.bridge_state)
        + np.dot(state.body_state, state.body_state)
    )


def render_stateful_acoustic_guitar_track(
    events,
    n: int,
    sr: int,
    patch: dict,
    beat_s: float,
    *,
    gain: float = 1.0,
    pan: float = 0.0,
):
    """AG08 whole-track entrypoint.

    S1 strict invariant:
    enabled + zero coupling => return None, which delegates to the pre-AG08
    canonical event renderer sample-exactly. The state is still constructed and
    validated by tests, but no arithmetic is inserted in the audio path.
    """
    graph = patch.get("acoustic_guitar_graph", {}) if isinstance(patch, dict) else {}
    if not stateful_enabled(graph):
        return None

    # Deterministic state construction is part of the S1 contract.
    state = initialize_acoustic_guitar_state(sr, graph)
    if state.model != STATE_MODEL or state.sample_rate != int(sr):
        raise ValueError("invalid AG08 acoustic-guitar state initialization")

    if coupling_is_zero(graph):
        return None

    raise NotImplementedError(
        "AG08 stateful coupling is not active beyond the S1 zero-coupling bypass"
    )


__all__ = [
    "STATE_MODEL",
    "AcousticGuitarState",
    "stateful_config",
    "stateful_enabled",
    "coupling_is_zero",
    "initialize_acoustic_guitar_state",
    "state_energy",
    "render_stateful_acoustic_guitar_track",
]
