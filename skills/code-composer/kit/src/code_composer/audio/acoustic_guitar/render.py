"""Deterministic acoustic-guitar rendering.

AG00's foundation path remains the historical A baseline. AG01 established the
accepted causal single-string core:
steel string -> bridge drive -> guitar body / air radiation.

AG02 may attach a resolved `performance.guitar_realization` containing physical
string/fret identity. The renderer consumes that realization but never chooses or
rewrites the fingering itself.
"""
from __future__ import annotations

import math
import numpy as np

from ...core.theory import midi_to_hz
from .body import radiate_acoustic_guitar_body
from .string import render_steel_string_bridge_drive


def _render_foundation_baseline(
    midi: int,
    gate_duration_s: float,
    sr: int,
    graph: dict,
    *,
    velocity: float,
    mechanics: dict | None = None,
):
    """Exact AG00 provisional renderer retained for matched A/B."""
    gate_s = max(1e-5, float(gate_duration_s))
    tail_s = max(0.0, float(graph.get("natural_tail_s", 0.45)))
    n = max(1, int((gate_s + tail_s) * int(sr)))
    active_n = min(n, max(1, int(gate_s * sr)))
    t = np.arange(n, dtype=np.float64) / float(sr)
    base = midi_to_hz(int(midi))

    partials = max(1, int(graph.get("max_partials", 14)))
    pluck_position = float(graph.get("pluck_position", 0.18))
    rolloff = max(0.5, float(graph.get("partial_rolloff", 1.15)))
    decay_s = max(0.05, float(graph.get("base_decay_s", 0.75)))
    damping = max(0.0, float(graph.get("frequency_damping", 0.28)))

    mono = np.zeros(n, dtype=np.float64)
    norm = 0.0
    for h in range(1, partials + 1):
        hz = base * h
        if hz >= sr * 0.47:
            break
        spatial = math.sin(math.pi * h * pluck_position)
        amp = spatial / (h ** rolloff)
        norm += abs(amp)
        tau = decay_s / (1.0 + damping * (h - 1))
        mono += (
            np.sin(2.0 * math.pi * hz * t + 0.07 * h)
            * amp
            * np.exp(-t / max(0.015, tau))
        )
    if norm > 1e-12:
        mono /= norm

    attack_s = max(0.0003, float(graph.get("attack_s", 0.0025)))
    mono *= 1.0 - np.exp(-t / attack_s)

    noise_gain = max(0.0, float(graph.get("pluck_noise_gain", 0.035)))
    if noise_gain > 0.0:
        seed = (
            int(graph.get("seed", 11900))
            + int(midi) * 1009
            + active_n * 17
        ) & 0xFFFFFFFF
        rng = np.random.default_rng(seed)
        noise = rng.standard_normal(n).astype(np.float64)
        mono += (
            noise
            * np.exp(
                -t / max(0.002, float(graph.get("pluck_noise_decay_s", 0.012)))
            )
            * noise_gain
        )

    post_gate_decay = max(0.015, float(graph.get("post_gate_decay_s", 0.18)))
    if active_n < n:
        rr = np.arange(n - active_n, dtype=np.float64) / float(sr)
        mono[active_n:] *= np.exp(-rr / post_gate_decay)

    mono *= max(0.0, min(1.0, float(velocity)))
    mono *= max(0.0, float(graph.get("output_gain", 0.72)))

    fade_n = min(
        n, max(1, int(float(graph.get("end_fade_s", 0.025)) * sr))
    )
    mono[-fade_n:] *= np.linspace(1.0, 0.0, fade_n, endpoint=True)
    peak = float(np.max(np.abs(mono))) if len(mono) else 0.0
    if peak > 1.0:
        mono /= peak
    return np.stack([mono, mono], axis=1)


def _render_ag01_modal_bridge_body(
    midi: int,
    gate_duration_s: float,
    sr: int,
    graph: dict,
    *,
    velocity: float,
):
    gate_s = max(1e-5, float(gate_duration_s))
    tail_s = max(0.0, float(graph.get("natural_tail_s", 2.20)))
    n = max(1, int((gate_s + tail_s) * int(sr)))
    active_n = min(n, max(1, int(gate_s * sr)))

    bridge = render_steel_string_bridge_drive(
        int(midi),
        n,
        int(sr),
        graph,
        velocity=float(velocity),
        mechanics=mechanics,
    )

    # Note-off damps string energy, but authored gate duration is not the same as
    # resonator lifetime. The residual string/body response remains audible.
    post_gate_decay = max(0.015, float(graph.get("post_gate_decay_s", 0.72)))
    if active_n < n:
        rr = np.arange(n - active_n, dtype=np.float64) / float(sr)
        bridge[active_n:] *= np.exp(-rr / post_gate_decay)

    stereo = radiate_acoustic_guitar_body(bridge, int(sr), graph)
    # Acoustic-guitar radiation efficiency rises through this register; compensate
    # the compact low-frequency body modes so E2-E4 listening is not dominated by
    # a pitch-dependent loudness collapse. One bounded slope applies to the whole
    # note and does not alter authored velocity relationships.
    radiation_keytrack = float(graph.get("radiation_keytrack", 1.10))
    radiation_gain = 2.0 ** (radiation_keytrack * (int(midi) - 52) / 12.0)
    stereo *= radiation_gain
    stereo *= max(0.0, float(graph.get("output_gain", 0.82)))

    fade_n = min(
        n, max(1, int(float(graph.get("end_fade_s", 0.035)) * sr))
    )
    stereo[-fade_n:] *= np.linspace(1.0, 0.0, fade_n, endpoint=True)[:, None]

    peak = float(np.max(np.abs(stereo))) if len(stereo) else 0.0
    if peak > 1.0:
        stereo /= peak
    return stereo


def render_acoustic_guitar_note(
    midi: int,
    gate_duration_s: float,
    sr: int,
    patch: dict,
    *,
    velocity: float = 1.0,
    performance: dict | None = None,
):
    graph = patch.get("acoustic_guitar_graph", {})
    model = graph.get("physical_model")
    mechanics = None
    if isinstance(performance, dict) and isinstance(
        performance.get("guitar_realization"), dict
    ):
        mechanics = performance["guitar_realization"]
    if model == "ag01_modal_bridge_body_v1":
        return _render_ag01_modal_bridge_body(
            midi,
            gate_duration_s,
            sr,
            graph,
            velocity=velocity,
            mechanics=mechanics,
        )
    return _render_foundation_baseline(
        midi, gate_duration_s, sr, graph, velocity=velocity
    )


__all__ = ["render_acoustic_guitar_note"]
