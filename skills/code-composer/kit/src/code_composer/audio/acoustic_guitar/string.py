"""Deterministic steel-string source model for AG01.

The output represents string energy arriving at the bridge. It is intentionally
separate from guitar-body radiation so later slices can extend string/fret and
right-hand mechanics without collapsing them into an EQ preset.
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


def render_steel_string_bridge_drive(
    midi: int,
    n: int,
    sr: int,
    graph: dict,
    *,
    velocity: float = 1.0,
):
    """Render one steel string as bridge-driving energy.

    This is a compact modal string, not a sampled guitar and not a fitted named
    instrument. Pluck position sets spectral nulls; stiffness adds bounded
    inharmonicity; upper partials decay faster; a short band-limited release
    transient supplies excitation texture without becoming a second oscillator.
    """
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

    # A pluck begins essentially immediately. A sub-millisecond ramp prevents a
    # mathematical discontinuity without turning the string into a slow synth attack.
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


__all__ = ["render_steel_string_bridge_drive"]
