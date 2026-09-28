"""Compact bridge/body/radiation model for AG01 acoustic guitar.

The modal frequencies are project-authored generic design values, not measured
responses from a named instrument. Low-Q parallel modes provide broad guitar-body
colour while a direct bridge path preserves string attack and avoids a single
foreground pitched "body tone".
"""
from __future__ import annotations

import math
import numpy as np
from scipy.signal import lfilter


_BODY_MODES = (
    (103.0, 1.8, 0.22),
    (188.0, 2.2, 0.20),
    (247.0, 2.6, 0.17),
    (365.0, 3.0, 0.14),
    (515.0, 3.5, 0.12),
    (720.0, 3.9, 0.10),
    (980.0, 4.2, 0.080),
    (1370.0, 4.6, 0.064),
    (1940.0, 5.0, 0.050),
    (2760.0, 5.2, 0.036),
)


def _one_pole_lowpass(x, sr, cutoff):
    cutoff = max(20.0, min(float(cutoff), sr * 0.45))
    alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff / sr)
    return lfilter([alpha], [1.0, -(1.0 - alpha)], x)


def _one_pole_highpass(x, sr, cutoff):
    return x - _one_pole_lowpass(x, sr, cutoff)


def _modal_resonator(x, sr, freq_hz, q, gain):
    freq_hz = max(20.0, min(float(freq_hz), sr * 0.45))
    q = max(0.5, float(q))
    radius = math.exp(-math.pi * freq_hz / (q * sr))
    theta = 2.0 * math.pi * freq_hz / sr
    y = lfilter(
        [1.0 - radius],
        [1.0, -2.0 * radius * math.cos(theta), radius * radius],
        x,
    )
    return y * float(gain)


def radiate_acoustic_guitar_body(bridge_drive, sr: int, graph: dict):
    """Transform bridge drive into a compact stereo acoustic-body radiation field."""
    x = np.asarray(bridge_drive, dtype=np.float64)
    sr = int(sr)

    bridge = _one_pole_highpass(
        x, sr, float(graph.get("bridge_highpass_hz", 58.0))
    )
    bridge = _one_pole_lowpass(
        bridge, sr, float(graph.get("bridge_lowpass_hz", 9200.0))
    )

    modal = np.zeros_like(bridge)
    body_scale = max(0.0, float(graph.get("body_modal_mix", 1.0)))
    modal_shift = float(graph.get("body_mode_shift", 1.0))
    modal_damping = max(0.55, float(graph.get("body_mode_damping", 1.0)))
    if body_scale > 0.0:
        for freq, q, gain in _BODY_MODES:
            modal += _modal_resonator(
                bridge,
                sr,
                freq * modal_shift,
                q / modal_damping,
                gain * body_scale,
            )

    direct = bridge * max(0.0, float(graph.get("direct_bridge_mix", 0.34)))
    air = _modal_resonator(
        bridge,
        sr,
        float(graph.get("air_mode_hz", 108.0)),
        float(graph.get("air_mode_q", 1.35)),
        float(graph.get("air_mode_mix", 0.11)),
    )

    top = direct + modal + air
    top = _one_pole_highpass(top, sr, 55.0)
    top = _one_pole_lowpass(
        top, sr, float(graph.get("radiation_lowpass_hz", 8800.0))
    )

    # Small frequency-dependent radiation asymmetry, not a chorus/delay effect.
    width = max(0.0, min(0.20, float(graph.get("stereo_width", 0.065))))
    side = _one_pole_highpass(modal, sr, float(graph.get("side_highpass_hz", 320.0)))
    left = top - side * width
    right = top + side * width

    drive = max(0.05, float(graph.get("body_drive", 0.92)))
    if abs(drive - 1.0) > 1e-12:
        denom = math.tanh(drive)
        left = np.tanh(left * drive) / denom
        right = np.tanh(right * drive) / denom

    return np.stack([left, right], axis=1)


__all__ = ["radiate_acoustic_guitar_body"]
