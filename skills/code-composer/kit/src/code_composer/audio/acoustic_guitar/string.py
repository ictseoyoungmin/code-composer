"""Deterministic steel-string source model for AG01 + AG02 fingering mechanics.

Without an AG02 guitar realization this function preserves the accepted AG01
single-string path. With a resolved string/fret position it applies bounded
string-identity and effective-length effects before bridge/body radiation.
"""
from __future__ import annotations

import math
import numpy as np
from scipy.signal import lfilter

from ...core.theory import midi_to_hz


_STRING_PROFILES = {
    1: dict(rolloff=-0.10, stiffness=0.78, decay=0.90, damping=0.90, noise=1.08, coupling=0.96),
    2: dict(rolloff=-0.05, stiffness=0.88, decay=0.95, damping=0.96, noise=1.04, coupling=0.98),
    3: dict(rolloff=0.02, stiffness=1.05, decay=1.02, damping=1.02, noise=1.00, coupling=1.00),
    4: dict(rolloff=0.08, stiffness=1.18, decay=1.07, damping=1.08, noise=0.96, coupling=1.02),
    5: dict(rolloff=0.13, stiffness=1.30, decay=1.11, damping=1.13, noise=0.93, coupling=1.03),
    6: dict(rolloff=0.17, stiffness=1.42, decay=1.14, damping=1.18, noise=0.90, coupling=1.04),
}


def _one_pole_lowpass(x, sr, cutoff):
    cutoff = max(20.0, min(float(cutoff), sr * 0.45))
    alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff / sr)
    return lfilter([alpha], [1.0, -(1.0 - alpha)], x)


def _one_pole_highpass(x, sr, cutoff):
    return x - _one_pole_lowpass(x, sr, cutoff)


def _mechanics_parameters(graph: dict, mechanics: dict | None):
    rolloff = max(0.45, float(graph.get("partial_rolloff", 0.86)))
    inharmonicity = max(0.0, float(graph.get("string_inharmonicity", 0.000045)))
    base_decay = max(0.05, float(graph.get("base_decay_s", 2.35)))
    damping = max(0.0, float(graph.get("frequency_damping", 0.11)))
    fret_contact = max(0.0, min(1.0, float(graph.get("fret_contact", 0.30))))
    noise_scale = 1.0
    coupling = 1.0
    contact_strength = 0.030
    fret_spectral = 0.0
    seed_offset = 0

    if not isinstance(mechanics, dict):
        return (
            rolloff, inharmonicity, base_decay, damping, fret_contact,
            noise_scale, coupling, contact_strength, fret_spectral, seed_offset,
        )

    string_number = int(mechanics.get("string", 3))
    fret = max(0, int(mechanics.get("fret", 0)))
    length_ratio = max(0.25, min(1.0, float(
        mechanics.get("effective_length_ratio", 2.0 ** (-fret / 12.0))
    )))
    profile = _STRING_PROFILES.get(string_number, _STRING_PROFILES[3])

    rolloff = max(0.45, rolloff + profile["rolloff"] + 0.0035 * fret)
    inharmonicity *= profile["stiffness"] * (length_ratio ** -0.65)
    base_decay *= profile["decay"] * max(0.72, length_ratio ** 0.18)
    damping *= profile["damping"] * (1.0 + 0.012 * fret)
    fret_contact = 0.04 if fret == 0 else min(0.95, 0.30 + 0.018 * fret)
    noise_scale = profile["noise"] * (1.0 + 0.006 * fret)
    coupling = profile["coupling"]
    contact_strength = 0.065
    fret_spectral = 0.0045 * fret
    seed_offset = string_number * 65537 + fret * 4099
    return (
        rolloff, inharmonicity, base_decay, damping, fret_contact,
        noise_scale, coupling, contact_strength, fret_spectral, seed_offset,
    )


def render_steel_string_bridge_drive(
    midi: int,
    n: int,
    sr: int,
    graph: dict,
    *,
    velocity: float = 1.0,
    mechanics: dict | None = None,
):
    """Render one steel string as bridge-driving energy."""
    n = max(1, int(n))
    sr = int(sr)
    t = np.arange(n, dtype=np.float64) / float(sr)
    base = midi_to_hz(int(midi))
    vel = max(0.0, min(1.0, float(velocity)))

    max_partials = max(1, int(graph.get("max_partials", 30)))
    pluck_position = float(graph.get("pluck_position", 0.16))
    damping_power = max(0.2, float(graph.get("damping_power", 1.35)))
    decay_keytrack = float(graph.get("decay_keytrack", 0.012))
    decay_key_scale = 2.0 ** (-decay_keytrack * (int(midi) - 52))
    (
        rolloff,
        inharmonicity,
        base_decay,
        damping,
        fret_contact,
        noise_scale,
        coupling,
        contact_strength,
        fret_spectral,
        seed_offset,
    ) = _mechanics_parameters(graph, mechanics)

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
        if fret_spectral > 0.0:
            amp *= math.exp(-fret_spectral * ((harmonic - 1) ** 0.70))
        norm += abs(amp)

        contact_loss = 1.0 + fret_contact * contact_strength * ((harmonic - 1) ** 1.12)
        decay = (
            base_decay
            * decay_key_scale
            / (1.0 + damping * ((harmonic - 1) ** damping_power))
            / contact_loss
        )
        decay = max(0.025, decay)
        phase = 0.015 * harmonic * harmonic + 0.007 * int(midi) * harmonic
        if isinstance(mechanics, dict):
            phase += 0.003 * int(mechanics.get("string", 3)) * harmonic
        sig += amp * np.sin(2.0 * math.pi * freq * t + phase) * np.exp(-t / decay)

    if norm > 1e-12:
        sig /= norm

    ramp_s = max(0.0001, float(graph.get("string_release_ramp_s", 0.00045)))
    sig *= 1.0 - np.exp(-t / ramp_s)
    sig *= max(0.03, vel) ** 0.72

    noise_gain = max(0.0, float(graph.get("excitation_noise_gain", 0.040))) * noise_scale
    if noise_gain > 0.0:
        seed = (
            int(graph.get("seed", 11901))
            + int(midi) * 1009
            + int(n) * 17
            + seed_offset
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
    if isinstance(mechanics, dict) and int(mechanics.get("fret", 0)) > 0:
        click_gain *= 1.0 + min(0.35, 0.012 * int(mechanics["fret"]))
    if click_gain > 0.0:
        click_n = min(n, max(1, int(0.006 * sr)))
        u = np.arange(click_n, dtype=np.float64) / float(sr)
        click = np.sin(2.0 * math.pi * 2800.0 * u) * np.exp(-u / 0.0016)
        sig[:click_n] += click * click_gain * max(0.10, vel) ** 1.10

    return sig * coupling


__all__ = ["render_steel_string_bridge_drive"]
