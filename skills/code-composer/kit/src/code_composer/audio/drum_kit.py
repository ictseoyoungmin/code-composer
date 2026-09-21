"""Deterministic kit-level integration for acoustic-drum rendering.

This module intentionally operates *after* individual drum-event synthesis.  It
models a compact recording/performance layer: near-coincident overhead capture,
small-room early reflections, a diffuse late field, and gentle parallel bus
compression.  It does not invent drum hits, timing, or orchestration.
"""
from __future__ import annotations

import math
import numpy as np

from .dsp import one_pole_highpass, one_pole_lowpass


def _rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, dtype=np.float64) ** 2))) if len(x) else 0.0


def _event_room_weight(kind, cfg):
    """Resolve room-send weight without changing authored event semantics.

    S26 knew only the five legacy drum names.  Later authenticity slices add
    explicit hi-hat, snare and tom articulations, so S27-G may override their
    room excitation individually while older presets keep the exact legacy
    fallback behavior.
    """
    weights = {
        "kick": float(cfg.get("kick_room_weight", 0.92)),
        "snare": float(cfg.get("snare_room_weight", 1.00)),
        "hat": float(cfg.get("hat_room_weight", 0.30)),
        "ride": float(cfg.get("ride_room_weight", 0.58)),
        "crash": float(cfg.get("crash_room_weight", 1.10)),
        "tom": float(cfg.get("tom_room_weight", 0.45)),
    }
    overrides = cfg.get("articulation_room_weights", {})
    if isinstance(overrides, dict) and kind in overrides:
        return float(overrides[kind])
    if kind in weights:
        return weights[kind]
    if kind.startswith("hat_"):
        return weights["hat"]
    if kind.startswith("snare_"):
        return weights["snare"]
    if kind.startswith("tom_"):
        return weights["tom"]
    return 0.45


def _event_envelope(events, n, sr, beat_s, cfg):
    """Build a deterministic excitation envelope from authored drum events.

    The dry renderer already carries velocity in its amplitude.  This envelope
    adds only a bounded nonlinear *room-send* emphasis so accents excite the
    shared acoustic field more strongly than quiet timekeeping hits.
    """
    env = np.zeros(int(n), dtype=np.float64)
    power = float(cfg.get("room_velocity_power", 1.45))
    decay_s = max(0.005, float(cfg.get("event_env_decay_s", 0.095)))
    pulse_n = max(1, int(min(0.45, decay_s * 5.0) * sr))
    pulse = np.exp(-np.arange(pulse_n, dtype=np.float64) / max(1.0, decay_s * sr))

    for ev in events or []:
        if ev.get("event_type") != "drum":
            continue
        start = int(float(ev.get("start_beat", 0.0)) * float(beat_s) * sr)
        if start >= n:
            continue
        kind = str(ev.get("drum", ""))
        weight = _event_room_weight(kind, cfg)
        velocity = max(0.0, min(1.25, float(ev.get("velocity", 0.8))))
        amp = weight * (min(1.0, velocity) ** power)
        end = min(n, start + pulse_n)
        if end > start:
            env[start:end] += amp * pulse[:end-start]

    # Soft normalization retains overlapping-hit build-up without unbounded send.
    return 1.0 - np.exp(-env)


def _delay_stereo(sig, sr, delay_ms):
    """Apply a pure stereo propagation delay.  A zero delay is byte-preserving."""
    sig = np.asarray(sig, dtype=np.float64)
    d = max(0, int(round(float(delay_ms) * 0.001 * sr)))
    if d <= 0 or not len(sig):
        return sig.copy()
    out = np.zeros_like(sig, dtype=np.float64)
    if d < len(sig):
        out[d:] = sig[:-d]
    return out


def _stereo_taps(sig, sr, taps):
    out = np.zeros_like(sig, dtype=np.float64)
    for delay_s, gain, cross in taps:
        d = max(1, int(float(delay_s) * sr))
        if d >= len(sig):
            continue
        src = sig[:-d]
        cross = max(0.0, min(1.0, float(cross)))
        wet = np.column_stack([
            src[:, 0] * (1.0 - cross) + src[:, 1] * cross,
            src[:, 1] * (1.0 - cross) + src[:, 0] * cross,
        ])
        out[d:] += wet * float(gain)
    return out


def _fdn_room(mono, sr, cfg):
    """Four-line lossless-matrix FDN with frequency-dependent feedback damping.

    Delay lengths are intentionally short and mutually non-integer-related at
    common audio sample rates.  Feedback gains are derived from the requested
    RT60 instead of hand-authoring arbitrary decay gains.
    """
    mono = np.asarray(mono, dtype=np.float64)
    n = len(mono)
    if n == 0:
        return np.zeros((0, 2), dtype=np.float64)

    delay_ms = cfg.get("fdn_delays_ms", [31.3, 37.9, 43.7, 53.1])
    if not isinstance(delay_ms, list) or len(delay_ms) != 4:
        delay_ms = [31.3, 37.9, 43.7, 53.1]
    lengths = [max(3, int(float(ms) * 0.001 * sr)) for ms in delay_ms]
    rt60 = max(0.12, float(cfg.get("room_rt60_s", 0.52)))
    damping = max(0.0, min(0.97, float(cfg.get("room_hf_damping", 0.56))))
    predelay = max(0, int(float(cfg.get("room_predelay_ms", 8.0)) * 0.001 * sr))

    buffers = [np.zeros(m, dtype=np.float64) for m in lengths]
    idx = [0, 0, 0, 0]
    lp = np.zeros(4, dtype=np.float64)
    gains = np.asarray([10.0 ** (-3.0 * (m / sr) / rt60) for m in lengths], dtype=np.float64)
    in_gain = np.asarray([0.50, -0.50, 0.50, 0.50], dtype=np.float64)
    out = np.zeros((n, 2), dtype=np.float64)

    # Normalized 4x4 Hadamard feedback matrix.
    H = 0.5 * np.asarray([
        [1.0, 1.0, 1.0, 1.0],
        [1.0, -1.0, 1.0, -1.0],
        [1.0, 1.0, -1.0, -1.0],
        [1.0, -1.0, -1.0, 1.0],
    ], dtype=np.float64)

    for s in range(n):
        y = np.asarray([buffers[i][idx[i]] for i in range(4)], dtype=np.float64)
        fb = H @ y
        lp = (1.0 - damping) * fb + damping * lp
        x = mono[s - predelay] if s >= predelay else 0.0
        write = in_gain * x + gains * lp
        for i in range(4):
            buffers[i][idx[i]] = write[i]
            idx[i] += 1
            if idx[i] >= lengths[i]:
                idx[i] = 0

        # Orthogonal-ish stereo readout avoids a mono late field.
        out[s, 0] = 0.50 * (y[0] + y[1] - y[2] + y[3])
        out[s, 1] = 0.50 * (y[0] - y[1] + y[2] + y[3])

    return out


def _feedforward_compressor(sig, sr, threshold_db, ratio, attack_s, release_s, makeup_db=0.0):
    """Predictable feed-forward compressor with smoothed gain reduction.

    The detector is peak-like; gain reduction itself is attack/release smoothed,
    allowing the initial drum transient to pass before the bus settles.
    """
    sig = np.asarray(sig, dtype=np.float64)
    if len(sig) == 0:
        return sig.copy(), np.ones(0, dtype=np.float64)
    level = np.max(np.abs(sig), axis=1)
    level_db = 20.0 * np.log10(level + 1e-12)
    over = np.maximum(0.0, level_db - float(threshold_db))
    target_gr = over * (1.0 - 1.0 / max(1.0, float(ratio)))

    a_att = math.exp(-1.0 / max(1.0, float(sr) * max(1e-5, float(attack_s))))
    a_rel = math.exp(-1.0 / max(1.0, float(sr) * max(1e-5, float(release_s))))
    gr = np.zeros(len(sig), dtype=np.float64)
    state = 0.0
    for i, target in enumerate(target_gr):
        coeff = a_att if target > state else a_rel
        state = coeff * state + (1.0 - coeff) * target
        gr[i] = state
    gain = 10.0 ** ((float(makeup_db) - gr) / 20.0)
    return sig * gain[:, None], gain


def integrate_drum_kit(dry, sr, events, beat_s, cfg):
    """Add a compact shared overhead/room/bus layer to a synthesized kit.

    Returns ``(integrated, report)``.  The dry source is never altered in-place.
    """
    dry = np.asarray(dry, dtype=np.float64)
    if dry.ndim != 2 or dry.shape[1] != 2:
        raise ValueError("drum-kit integration requires stereo [frames,2] audio")
    if not len(dry):
        return dry.copy(), {"enabled": True, "input_rms": 0.0, "output_rms": 0.0}

    close_gain = float(cfg.get("close_gain", 1.0))
    overhead_gain = float(cfg.get("overhead_gain", 0.26))
    room_gain = float(cfg.get("room_gain", 0.20))
    output_gain = float(cfg.get("output_gain", 0.92))

    # Overhead path: mostly direct kit image plus a few early reflections.
    overhead = one_pole_highpass(dry, sr, float(cfg.get("overhead_highpass_hz", 115.0)))
    overhead = one_pole_lowpass(overhead, sr, float(cfg.get("overhead_lowpass_hz", 14500.0)))
    overhead = _delay_stereo(overhead, sr, float(cfg.get("overhead_predelay_ms", 0.0)))
    overhead_early = _stereo_taps(overhead, sr, [
        (0.0037, 0.16, 0.20),
        (0.0061, 0.11, 0.72),
        (0.0094, 0.075, 0.35),
        (0.0138, 0.050, 0.82),
    ])
    overhead = overhead + overhead_early

    # Room path: authored hit velocity changes room excitation without changing
    # the dry source or synthesizer decay constants.
    exc = _event_envelope(events, len(dry), sr, beat_s, cfg)
    send_floor = float(cfg.get("room_send_floor", 0.48))
    send_scale = float(cfg.get("room_send_scale", 0.78))
    room_in = dry * (send_floor + send_scale * exc[:, None])
    room_in = one_pole_highpass(room_in, sr, float(cfg.get("room_highpass_hz", 72.0)))
    room_in = one_pole_lowpass(room_in, sr, float(cfg.get("room_lowpass_hz", 11800.0)))

    early = _stereo_taps(room_in, sr, [
        (0.012, 0.30, 0.78),
        (0.0185, 0.24, 0.28),
        (0.0267, 0.19, 0.70),
        (0.0375, 0.14, 0.34),
        (0.0490, 0.095, 0.76),
    ])
    mono = 0.5 * (room_in[:, 0] + room_in[:, 1])
    late = _fdn_room(mono, sr, cfg)
    late = one_pole_lowpass(late, sr, float(cfg.get("late_lowpass_hz", 9800.0)))
    room = float(cfg.get("early_mix", 0.72)) * early + float(cfg.get("late_mix", 0.54)) * late

    ambient = overhead_gain * overhead + room_gain * room
    ambient_comp, ambient_gain = _feedforward_compressor(
        ambient, sr,
        float(cfg.get("ambient_comp_threshold_db", -23.0)),
        float(cfg.get("ambient_comp_ratio", 2.4)),
        float(cfg.get("ambient_comp_attack_s", 0.006)),
        float(cfg.get("ambient_comp_release_s", 0.120)),
        float(cfg.get("ambient_comp_makeup_db", 2.2)),
    )

    # Close-mic body reinforcement is zero-delay and band-limited, so it adds
    # kick/snare weight without smearing the attack or creating another room tail.
    body = one_pole_highpass(dry, sr, float(cfg.get("body_highpass_hz", 45.0)))
    body = one_pole_lowpass(body, sr, float(cfg.get("body_lowpass_hz", 260.0)))
    body_comp, _body_gain = _feedforward_compressor(
        body, sr,
        float(cfg.get("body_comp_threshold_db", -15.0)),
        float(cfg.get("body_comp_ratio", 1.8)),
        float(cfg.get("body_comp_attack_s", 0.012)),
        float(cfg.get("body_comp_release_s", 0.100)),
        float(cfg.get("body_comp_makeup_db", 1.4)),
    )
    body_parallel_gain = max(0.0, min(0.5, float(cfg.get("body_parallel_gain", 0.10))))

    integrated = close_gain * dry + body_parallel_gain * body_comp + ambient_comp

    # Gentle parallel bus glue: the transient remains in the dry branch while a
    # denser parallel branch reinforces body and shared decay.
    parallel, bus_gain = _feedforward_compressor(
        integrated, sr,
        float(cfg.get("bus_threshold_db", -16.5)),
        float(cfg.get("bus_ratio", 2.1)),
        float(cfg.get("bus_attack_s", 0.010)),
        float(cfg.get("bus_release_s", 0.095)),
        float(cfg.get("bus_makeup_db", 1.8)),
    )
    parallel_mix = max(0.0, min(0.5, float(cfg.get("parallel_mix", 0.16))))
    integrated = integrated * (1.0 - parallel_mix) + parallel * parallel_mix
    integrated *= output_gain

    report = {
        "enabled": True,
        "input_rms": _rms(dry),
        "overhead_rms": _rms(overhead_gain * overhead),
        "room_rms": _rms(room_gain * room),
        "ambient_rms": _rms(ambient_comp),
        "body_rms": _rms(body_parallel_gain * body_comp),
        "room_excitation_mean": float(np.mean(exc)),
        "room_excitation_peak": float(np.max(exc)),
        "output_rms": _rms(integrated),
        "peak": float(np.max(np.abs(integrated))),
        "ambient_min_gain": float(np.min(ambient_gain)) if len(ambient_gain) else 1.0,
        "bus_min_gain": float(np.min(bus_gain)) if len(bus_gain) else 1.0,
    }
    return integrated, report


__all__ = ["integrate_drum_kit"]
