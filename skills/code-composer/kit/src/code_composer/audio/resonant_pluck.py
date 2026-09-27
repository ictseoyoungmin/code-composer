"""Deterministic resonant plucked-string synthesis.

The authored note duration is the excitation/gate duration. The string/body may
continue to ring after note-off; that physical lifetime is owned by the instrument
patch rather than by a song-specific renderer table.
"""
from __future__ import annotations

import math
import numpy as np
from scipy.signal import lfilter

from ..core.theory import midi_to_hz


def _smoothstep01(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def _one_pole_lowpass(x, sr, cutoff):
    cutoff = max(20.0, min(float(cutoff), sr * .45))
    alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff / sr)
    return lfilter([alpha], [1.0, -(1.0 - alpha)], x)


def _expression(performance):
    if not isinstance(performance, dict):
        return {}
    value = performance.get("instrument_expression", {})
    return value if isinstance(value, dict) else {}


def _pitch_ratio(n, sr, expr):
    start = float(expr.get("pitch_start_cents", 0.0))
    end = float(expr.get("pitch_end_cents", 0.0))
    time_s = max(1e-4, float(expr.get("pitch_time_s", .10)))
    m = min(n, max(1, int(time_s * sr)))
    cents = np.full(n, end, dtype=np.float64)
    u = _smoothstep01(np.linspace(0.0, 1.0, m, endpoint=True))
    cents[:m] = start + (end - start) * u
    vib_depth = max(0.0, float(expr.get("vibrato_depth_cents", 0.0)))
    vib_rate = max(0.0, float(expr.get("vibrato_rate_hz", 5.2)))
    if vib_depth > 0.0 and vib_rate > 0.0:
        t = np.arange(n, dtype=np.float64) / sr
        onset = max(0.0, float(expr.get("vibrato_onset_s", .08)))
        fade = max(1e-4, float(expr.get("vibrato_fade_s", .08)))
        gate = _smoothstep01((t - onset) / fade)
        cents += np.sin(2 * np.pi * vib_rate * t) * vib_depth * gate
    return 2.0 ** (cents / 1200.0)


def render_resonant_pluck_note(
    midi: int,
    gate_duration_s: float,
    sr: int,
    patch: dict,
    velocity: float = 1.0,
    performance: dict | None = None,
):
    graph = patch.get("resonant_pluck_graph", {})
    if not isinstance(graph, dict):
        graph = {}
    gate_s = max(1e-5, float(gate_duration_s))
    tail_s = max(0.0, float(graph.get("natural_tail_s", .70)))
    n = max(1, int((gate_s + tail_s) * int(sr)))
    active_n = min(n, max(1, int(gate_s * sr)))
    t = np.arange(n, dtype=np.float64) / sr
    expr = _expression(performance)
    ratio = _pitch_ratio(n, sr, expr)
    base = midi_to_hz(int(midi))

    max_partials = max(1, int(graph.get("max_partials", 12)))
    pluck_pos = float(graph.get("pluck_position", .17))
    rolloff = max(.25, float(graph.get("partial_rolloff", 1.02)))
    inharm = max(0.0, float(graph.get("inharmonicity", .00010)))
    base_decay = max(.03, float(graph.get("base_decay_s", .95)))
    frequency_damping = max(0.0, float(graph.get("frequency_damping", .24)))
    width = max(0.0, min(.75, float(graph.get("stereo_width", .14))))

    left = np.zeros(n, dtype=np.float64)
    right = np.zeros(n, dtype=np.float64)
    norm = 0.0
    for h in range(1, max_partials + 1):
        hz = base * h * math.sqrt(1.0 + inharm * h * h)
        if hz >= sr * .47:
            break
        spatial = math.sin(math.pi * h * pluck_pos)
        amp = spatial / (h ** rolloff)
        norm += abs(amp)
        decay = base_decay / (1.0 + frequency_damping * (h - 1))
        natural = np.exp(-t / max(.015, decay))
        phase = 2 * np.pi * np.cumsum(hz * ratio) / sr
        sig = np.sin(phase + .11 * h) * amp * natural
        pan = (-1.0 if h % 2 else 1.0) * width * min(1.0, h / 7.0)
        angle = (pan + 1.0) * math.pi / 4.0
        left += sig * math.cos(angle)
        right += sig * math.sin(angle)
    if norm > 1e-12:
        left /= norm
        right /= norm

    noise_gain = max(0.0, float(graph.get("pluck_noise_gain", .075)))
    if noise_gain > 0:
        seed = (int(graph.get("seed", 8128)) + int(midi) * 1009 + active_n * 17) & 0xFFFFFFFF
        rng = np.random.default_rng(seed)
        noise = rng.standard_normal(n).astype(np.float64)
        noise = _one_pole_lowpass(noise, sr, float(graph.get("pluck_noise_lowpass_hz", 6500.0)))
        attack_noise = noise * np.exp(-t / max(.002, float(graph.get("pluck_noise_decay_s", .022)))) * noise_gain
        left += attack_noise * math.sqrt(.5)
        right += attack_noise * math.sqrt(.5)

    freqs = graph.get("body_resonances_hz", [390.0, 690.0])
    gains = graph.get("body_gains", [.055, .035])
    decays = graph.get("body_decay_s", [.18, .13])
    body = np.zeros(n, dtype=np.float64)
    for i, hz in enumerate(freqs):
        hz = float(hz)
        if not (20.0 < hz < sr * .45):
            continue
        gain = float(gains[i] if i < len(gains) else 0.0)
        decay = max(.01, float(decays[i] if i < len(decays) else .12))
        body += np.sin(2 * np.pi * hz * t + .07 * i) * np.exp(-t / decay) * gain
    body_mix = max(0.0, min(1.0, float(graph.get("body_mix", .18))))
    left = left * (1.0 - body_mix) + body * body_mix
    right = right * (1.0 - body_mix) + body * body_mix

    # Note-off starts damping. It does not truncate the resonator buffer.
    release_damping = max(.20, min(4.0, float(expr.get("release_damping", 1.0))))
    tau = max(.015, float(graph.get("post_gate_decay_s", .28)) / release_damping)
    gate = np.ones(n, dtype=np.float64)
    if active_n < n:
        rr = np.arange(n - active_n, dtype=np.float64) / sr
        gate[active_n:] = np.exp(-rr / tau)
    attack_s = max(.0003, float(graph.get("attack_s", .0035)))
    attack = 1.0 - np.exp(-t / attack_s)
    left *= attack * gate * float(velocity)
    right *= attack * gate * float(velocity)

    fade_s = max(.002, float(graph.get("end_fade_s", .035)))
    fade_n = min(n, max(1, int(fade_s * sr)))
    fade = _smoothstep01(np.linspace(1.0, 0.0, fade_n, endpoint=True))
    left[-fade_n:] *= fade
    right[-fade_n:] *= fade

    cutoff = float(graph.get("lowpass_hz", 7600.0))
    left = _one_pole_lowpass(left, sr, cutoff)
    right = _one_pole_lowpass(right, sr, cutoff)
    drive = max(.05, float(graph.get("drive", 1.25)))
    left = np.tanh(left * drive)
    right = np.tanh(right * drive)
    gain = max(0.0, float(graph.get("output_gain", .86)))
    left *= gain
    right *= gain
    peak = max(
        float(np.max(np.abs(left))) if len(left) else 0.0,
        float(np.max(np.abs(right))) if len(right) else 0.0,
    )
    if peak > 1.0:
        left /= peak
        right /= peak
    return np.stack([left, right], axis=1)


__all__ = ["render_resonant_pluck_note"]
