"""Deterministic steel-string source models for AG01.

R3 keeps the original AG01 source available as a legacy diagnostic and adds a
physically better constrained bridge-force source. The R3 model starts from the
triangular displacement spectrum of a released pluck: modal displacement falls
as 1/n^2 and differentiation at the bridge contributes one factor of n, yielding
a bridge-force-like 1/n envelope with pluck-position spectral nulls.

No sampled audio, IR, or fitted named-instrument response is used.
"""
from __future__ import annotations

import math
import numpy as np
from scipy.signal import lfilter

from ...core.theory import midi_to_hz


def _one_pole_lowpass(x, sr, cutoff):
    cutoff = max(20.0, min(float(cutoff), sr * 0.45))
    alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff / sr)
    return lfilter([alpha], [1.0, -(1.0 - alpha)], x)


def _one_pole_highpass(x, sr, cutoff):
    return x - _one_pole_lowpass(x, sr, cutoff)


def _render_legacy_bridge_drive(
    midi: int,
    n: int,
    sr: int,
    graph: dict,
    *,
    velocity: float,
):
    """Exact AG01 R2 source retained for audit/listening comparison."""
    n = max(1, int(n))
    sr = int(sr)
    t = np.arange(n, dtype=np.float64) / float(sr)
    base = midi_to_hz(int(midi))
    vel = max(0.0, min(1.0, float(velocity)))

    max_partials = max(1, int(graph.get("max_partials", 30)))
    pluck_position = float(graph.get("pluck_position", 0.16))
    rolloff = max(0.45, float(graph.get("partial_rolloff", 0.86)))
    inharmonicity = max(0.0, float(graph.get("string_inharmonicity", 0.000045)))
    base_decay = max(0.05, float(graph.get("base_decay_s", 2.35)))
    damping = max(0.0, float(graph.get("frequency_damping", 0.11)))
    damping_power = max(0.2, float(graph.get("damping_power", 1.35)))
    decay_keytrack = float(graph.get("decay_keytrack", 0.012))
    fret_contact = max(0.0, min(1.0, float(graph.get("fret_contact", 0.30))))
    decay_key_scale = 2.0 ** (-decay_keytrack * (int(midi) - 52))

    sig = np.zeros(n, dtype=np.float64)
    norm = 0.0
    for harmonic in range(1, max_partials + 1):
        ratio = harmonic * math.sqrt(1.0 + inharmonicity * harmonic * harmonic)
        freq = base * ratio
        if freq >= sr * 0.47:
            break

        spatial = math.sin(math.pi * harmonic * pluck_position)
        bridge_velocity_weight = harmonic ** 0.32
        amp = spatial * bridge_velocity_weight / (harmonic ** rolloff)
        norm += abs(amp)

        contact_loss = 1.0 + fret_contact * 0.030 * ((harmonic - 1) ** 1.12)
        decay = (
            base_decay
            * decay_key_scale
            / (1.0 + damping * ((harmonic - 1) ** damping_power))
            / contact_loss
        )
        decay = max(0.025, decay)
        phase = 0.015 * harmonic * harmonic + 0.007 * int(midi) * harmonic
        sig += amp * np.sin(2.0 * math.pi * freq * t + phase) * np.exp(-t / decay)

    if norm > 1e-12:
        sig /= norm

    ramp_s = max(0.0001, float(graph.get("string_release_ramp_s", 0.00045)))
    sig *= 1.0 - np.exp(-t / ramp_s)
    sig *= max(0.03, vel) ** 0.72

    noise_gain = max(0.0, float(graph.get("excitation_noise_gain", 0.040)))
    if noise_gain > 0.0:
        seed = (
            int(graph.get("seed", 11901))
            + int(midi) * 1009
            + int(n) * 17
        ) & 0xFFFFFFFF
        rng = np.random.default_rng(seed)
        noise = rng.standard_normal(n).astype(np.float64)
        noise = _one_pole_highpass(
            noise, sr, float(graph.get("excitation_highpass_hz", 850.0))
        )
        noise = _one_pole_lowpass(
            noise, sr, float(graph.get("excitation_lowpass_hz", 7200.0))
        )
        rms = float(np.sqrt(np.mean(noise * noise)) + 1e-12)
        noise /= rms
        excitation_decay = max(
            0.002, float(graph.get("excitation_decay_s", 0.018))
        )
        sig += (
            noise
            * np.exp(-t / excitation_decay)
            * noise_gain
            * max(0.10, vel) ** 0.86
        )

    click_gain = max(0.0, float(graph.get("release_click_gain", 0.018)))
    if click_gain > 0.0:
        click_n = min(n, max(1, int(0.006 * sr)))
        u = np.arange(click_n, dtype=np.float64) / float(sr)
        click = np.sin(2.0 * math.pi * 2800.0 * u) * np.exp(-u / 0.0016)
        sig[:click_n] += click * click_gain * max(0.10, vel) ** 1.10

    return sig


def _render_triangular_pluck_bridge_force(
    midi: int,
    n: int,
    sr: int,
    graph: dict,
    *,
    velocity: float,
    mechanics: dict | None = None,
    right_hand: dict | None = None,
):
    """R3 bridge-force model from a released triangular string displacement."""
    n = max(1, int(n))
    sr = int(sr)
    t = np.arange(n, dtype=np.float64) / float(sr)
    base = midi_to_hz(int(midi))
    vel = max(0.0, min(1.0, float(velocity)))

    max_partials = max(1, int(graph.get("max_partials", 30)))
    pluck_position = float(graph.get("pluck_position", 0.14))
    force_rolloff = max(0.80, float(graph.get("bridge_force_rolloff", 1.06)))
    inharmonicity = max(0.0, float(graph.get("string_inharmonicity", 0.000035)))
    base_decay = max(0.05, float(graph.get("base_decay_s", 2.25)))
    damping = max(0.0, float(graph.get("frequency_damping", 0.14)))
    damping_power = max(0.2, float(graph.get("damping_power", 1.30)))
    decay_keytrack = float(graph.get("decay_keytrack", 0.014))
    fret_contact = max(0.0, min(1.0, float(graph.get("fret_contact", 0.26))))
    decay_key_scale = 2.0 ** (-decay_keytrack * (int(midi) - 52))

    # AG02 is a bounded position layer over the CLOSED AG01 R3 source.
    # No mechanics and the canonical reference position are deliberately inert.
    if isinstance(mechanics, dict) and not bool(mechanics.get("position_is_reference", False)):
        distance = max(0.0, min(1.0, float(mechanics.get("position_distance", 0.0))))
        string_delta = (
            int(mechanics.get("string", 3))
            - int(mechanics.get("reference_string", 3))
        ) / 5.0
        fret_delta = (
            int(mechanics.get("fret", 0))
            - int(mechanics.get("reference_fret", 0))
        ) / 20.0

        # Keep the AG01 attack identity intact: do not alter noise seed, phase,
        # contact-burst envelope, body coupling or pluck position here.
        force_rolloff = max(
            0.80, force_rolloff + 0.014 * string_delta + 0.008 * fret_delta
        )
        inharmonicity *= 1.0 + 0.025 * distance
        base_decay *= 1.0 - 0.025 * distance
        damping *= 1.0 + 0.035 * distance
        fret_contact = min(1.0, fret_contact + 0.040 * distance)

    # AG03 owns right-hand excitation only. Defaults are exact no-ops so an
    # absent/reference right-hand state preserves the CLOSED AG02 render.
    contact_ramp_scale = 1.0
    contact_noise_gain_scale = 1.0
    contact_noise_hp_scale = 1.0
    contact_noise_lp_scale = 1.0
    contact_noise_decay_scale = 1.0

    if isinstance(right_hand, dict):
        method = str(right_hand.get("method", "neutral"))
        profiles = {
            "neutral": (0.0, 1.0, 1.0, 1.0, 1.0, 1.0),
            "finger": (0.035, 1.12, 0.78, 0.85, 0.90, 1.12),
            "thumb": (0.060, 1.22, 0.68, 0.75, 0.82, 1.18),
            "nail": (-0.025, 0.92, 1.12, 1.08, 1.08, 0.90),
            "pick": (-0.045, 0.82, 1.28, 1.18, 1.18, 0.78),
        }
        (
            method_rolloff,
            contact_ramp_scale,
            contact_noise_gain_scale,
            contact_noise_hp_scale,
            contact_noise_lp_scale,
            contact_noise_decay_scale,
        ) = profiles.get(method, profiles["neutral"])

        pluck_position = max(
            0.03, min(0.49, float(right_hand.get("pluck_position", pluck_position)))
        )
        angle_delta = (
            max(0.0, min(90.0, float(right_hand.get("attack_angle_deg", 45.0))))
            - 45.0
        ) / 45.0
        strength_delta = (
            max(0.0, min(1.0, float(right_hand.get("strength", 0.5)))) - 0.5
        )
        velocity_delta = vel - 0.65

        force_rolloff = max(
            0.80,
            force_rolloff
            + method_rolloff
            - 0.015 * angle_delta
            - 0.025 * strength_delta
            - 0.020 * velocity_delta,
        )
        contact_ramp_scale *= max(0.75, 1.0 - 0.10 * strength_delta)
        contact_noise_gain_scale *= max(
            0.70,
            1.0 + 0.10 * angle_delta + 0.20 * strength_delta + 0.15 * velocity_delta,
        )
        contact_noise_hp_scale *= max(0.80, 1.0 + 0.08 * angle_delta)
        contact_noise_lp_scale *= max(0.80, 1.0 + 0.10 * angle_delta)

    sig = np.zeros(n, dtype=np.float64)
    norm = 0.0
    for harmonic in range(1, max_partials + 1):
        ratio = harmonic * math.sqrt(1.0 + inharmonicity * harmonic * harmonic)
        freq = base * ratio
        if freq >= sr * 0.47:
            break

        # A released triangular displacement has modal displacement ~ sin(n*pi*p)/n^2.
        # Bridge force differentiates spatially at the fixed end, contributing n.
        spatial = math.sin(math.pi * harmonic * pluck_position)
        amp = spatial / (harmonic ** force_rolloff)
        norm += abs(amp)

        contact_loss = 1.0 + fret_contact * 0.026 * ((harmonic - 1) ** 1.10)
        decay = (
            base_decay
            * decay_key_scale
            / (1.0 + damping * ((harmonic - 1) ** damping_power))
            / contact_loss
        )
        decay = max(0.025, decay)

        # Zero initial velocity -> cosine modal phase at release. Using one coherent
        # physical phase avoids the metallic/synthetic phase cloud of the R2 source.
        sig += amp * np.cos(2.0 * math.pi * freq * t) * np.exp(-t / decay)

    if norm > 1e-12:
        sig /= norm

    # A very short release ramp regularizes the discrete-time start while keeping
    # the coherent pluck front intact.
    ramp_s = max(
        0.0001,
        float(graph.get("string_release_ramp_s", 0.00028)) * contact_ramp_scale,
    )
    sig *= 1.0 - np.exp(-t / ramp_s)
    sig *= max(0.03, vel) ** 0.74

    # Pick/string release is modeled as a short colored contact burst. R3 removes
    # the fixed 2.8 kHz sinusoidal click because it reads as a separate pitched event.
    noise_gain = (
        max(0.0, float(graph.get("excitation_noise_gain", 0.024)))
        * contact_noise_gain_scale
    )
    if noise_gain > 0.0:
        seed = (
            int(graph.get("seed", 11901))
            + int(midi) * 1009
            + int(n) * 17
        ) & 0xFFFFFFFF
        rng = np.random.default_rng(seed)
        noise = rng.standard_normal(n).astype(np.float64)
        noise = _one_pole_highpass(
            noise,
            sr,
            float(graph.get("excitation_highpass_hz", 650.0))
            * contact_noise_hp_scale,
        )
        noise = _one_pole_lowpass(
            noise,
            sr,
            float(graph.get("excitation_lowpass_hz", 6200.0))
            * contact_noise_lp_scale,
        )
        rms = float(np.sqrt(np.mean(noise * noise)) + 1e-12)
        noise /= rms
        excitation_decay = max(
            0.002,
            float(graph.get("excitation_decay_s", 0.0085))
            * contact_noise_decay_scale,
        )
        sig += (
            noise
            * np.exp(-t / excitation_decay)
            * noise_gain
            * max(0.10, vel) ** 0.92
        )

    return sig


def render_steel_string_bridge_drive(
    midi: int,
    n: int,
    sr: int,
    graph: dict,
    *,
    velocity: float = 1.0,
    mechanics: dict | None = None,
    right_hand: dict | None = None,
):
    model = str(graph.get("string_source_model", "ag01_legacy_modal_v1"))
    if model == "triangular_pluck_bridge_force_v2":
        return _render_triangular_pluck_bridge_force(
            midi,
            n,
            sr,
            graph,
            velocity=velocity,
            mechanics=mechanics,
            right_hand=right_hand,
        )
    return _render_legacy_bridge_drive(midi, n, sr, graph, velocity=velocity)


__all__ = ["render_steel_string_bridge_drive"]
