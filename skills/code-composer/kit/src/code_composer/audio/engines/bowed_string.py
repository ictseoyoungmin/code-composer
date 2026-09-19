from __future__ import annotations

import math
import numpy as np
from scipy.signal import iirpeak, lfilter

from .base import EngineCapabilities, InstrumentEngine, InstrumentEngineValidationError
from ...core.theory import midi_to_hz


def _num(v, name, lo, hi):
    try:
        x = float(v)
    except Exception as exc:
        raise InstrumentEngineValidationError(f"{name} must be numeric") from exc
    if not (lo <= x <= hi):
        raise InstrumentEngineValidationError(f"{name} outside [{lo},{hi}]")
    return x


def _graph(patch: dict) -> dict:
    g = patch.get("bowed_string_graph")
    if not isinstance(g, dict):
        raise InstrumentEngineValidationError("bowed_string_graph must be an object")
    return g


def _expression(performance: dict | None) -> dict:
    if not isinstance(performance, dict):
        return {}
    x = performance.get("instrument_expression", {})
    return x if isinstance(x, dict) else {}


def _articulation_scales(performance: dict | None) -> tuple[float, float, float]:
    articulation = (performance or {}).get("articulation", "neutral")
    # attack, release, bow-noise multipliers. These are execution semantics, not presets.
    return {
        "legato": (1.25, 1.25, .72),
        "tenuto": (1.00, 1.10, .88),
        "neutral": (1.00, 1.00, 1.00),
        "staccato": (.72, .46, 1.05),
        "accent": (.58, .82, 1.24),
        "marcato": (.48, .70, 1.42),
    }.get(str(articulation), (1.0, 1.0, 1.0))


def render_bowed_string_note(
    midi: int,
    duration_s: float,
    sr: int,
    patch: dict,
    *,
    velocity: float = 1.0,
    performance: dict | None = None,
):
    """Deterministic bowed-string family synthesis.

    The patch owns timbre. The engine only defines bowed-string mechanics and how
    explicit performance expression is consumed; it contains no named violin preset.
    """
    from ..generic_synth import _one_pole_highpass, _one_pole_lowpass, _normalize, _smoothstep01

    graph = _graph(patch)
    strings = graph.get("strings", {})
    bow = graph.get("bow", {})
    vib = graph.get("vibrato", {})
    body = graph.get("body", {})
    env_cfg = graph.get("envelope", {})
    expr = _expression(performance)

    attack_scale, release_scale, noise_scale = _articulation_scales(performance)
    attack_s = max(1e-4, float(expr.get("attack_s", env_cfg.get("attack_s", .055))) * attack_scale)
    release_s = max(1e-4, float(expr.get("release_s", env_cfg.get("release_s", .18))) * release_scale)
    active_n = max(1, int(max(1e-5, duration_s) * sr))
    n = max(1, int((max(1e-5, duration_s) + release_s) * sr))
    t = np.arange(n, dtype=np.float64) / sr

    base_hz = midi_to_hz(midi)
    max_partials = max(1, int(strings.get("max_partials", 14)))
    rolloff = float(strings.get("spectral_rolloff", 1.35))
    inharm = float(strings.get("inharmonicity", .00012))
    bow_position = float(expr.get("bow_position", bow.get("position", .18)))
    bow_pressure = float(expr.get("bow_pressure", bow.get("pressure", .52)))
    bow_speed = float(expr.get("bow_speed", bow.get("speed", .58)))
    width = max(0.0, min(1.0, float(graph.get("stereo_width", .22))))

    vib_rate = float(expr.get("vibrato_rate_hz", vib.get("rate_hz", 5.3)))
    vib_depth = float(expr.get("vibrato_depth_cents", vib.get("depth_cents", 14.0)))
    vib_onset = max(0.0, float(expr.get("vibrato_onset_s", vib.get("onset_s", .18))))
    vib_fade = max(1e-4, float(vib.get("fade_s", .16)))
    vib_gate = _smoothstep01((t - vib_onset) / vib_fade)
    vibrato_cents = np.sin(2 * np.pi * vib_rate * t) * vib_depth * vib_gate
    freq_ratio = 2.0 ** (vibrato_cents / 1200.0)

    left = np.zeros(n, dtype=np.float64)
    right = np.zeros(n, dtype=np.float64)
    brightness = .62 + .68 * max(0.0, min(1.0, float(velocity))) + .30 * bow_pressure
    for k in range(1, max_partials + 1):
        hz = base_hz * k * math.sqrt(1.0 + inharm * k * k)
        if hz >= sr * .46:
            break
        position_shape = .18 + .82 * abs(math.sin(math.pi * k * bow_position))
        pressure_shape = 1.0 + bow_pressure * min(1.0, k / 8.0) * .45
        amp = position_shape * pressure_shape / (k ** max(.35, rolloff / brightness))
        phase = 2 * np.pi * np.cumsum(hz * freq_ratio) / sr
        sig = np.sin(phase) * amp
        pan = ((-1.0 if k % 2 else 1.0) * width * min(.35, .06 * k))
        angle = (pan + 1.0) * math.pi / 4.0
        left += sig * math.cos(angle)
        right += sig * math.sin(angle)

    # Continuous bow energy envelope: attack into held excitation, explicit release.
    env = np.ones(n, dtype=np.float64)
    na = min(active_n, max(1, int(attack_s * sr)))
    env[:na] = _smoothstep01(np.linspace(0, 1, na, endpoint=True))
    if active_n < n:
        nr = n - active_n
        env[active_n:] = _smoothstep01(np.linspace(1, 0, nr, endpoint=True))
    env *= max(.01, min(1.0, float(velocity)))
    left *= env
    right *= env

    # Deterministic, band-limited bow friction. Seed is note-local, not random runtime state.
    noise_gain = max(0.0, float(expr.get("bow_noise_gain", bow.get("noise_gain", .018))))
    if noise_gain > 0:
        seed = int(bow.get("seed", 71)) + int(midi) * 1009 + active_n % 65521
        rng = np.random.default_rng(seed)
        noise = rng.standard_normal(n).astype(np.float64)
        low = float(bow.get("noise_low_hz", 850.0))
        high = float(bow.get("noise_high_hz", 7800.0))
        noise = _one_pole_highpass(noise, sr, low)
        noise = _one_pole_lowpass(noise, sr, high)
        rms = float(np.sqrt(np.mean(noise * noise)) + 1e-12)
        noise = noise / rms
        ng = noise_gain * noise_scale * (.45 + .75 * bow_speed) * (.55 + .75 * bow_pressure)
        noise = noise * env * ng
        left += noise * math.sqrt(.5)
        right += noise * math.sqrt(.5)

    stereo = np.stack([left, right], axis=1)

    # Optional body modes are explicit patch data; the engine does not embed an instrument body preset.
    modes = body.get("resonances_hz", [])
    gains = body.get("gains", [])
    q_values = body.get("q", [])
    if modes:
        mono = .5 * (stereo[:, 0] + stereo[:, 1])
        body_sig = np.zeros(n, dtype=np.float64)
        for i, hz in enumerate(modes):
            hz = float(hz)
            if not (20.0 < hz < sr * .45):
                continue
            gain = float(gains[i] if i < len(gains) else 0.0)
            q = float(q_values[i] if i < len(q_values) else 3.0)
            b, a = iirpeak(hz / (sr * .5), Q=max(.25, q))
            body_sig += lfilter(b, a, mono) * gain
        body_mix = max(0.0, min(1.0, float(body.get("mix", .18))))
        stereo = stereo * (1.0 - body_mix) + np.stack([body_sig, body_sig], axis=1) * body_mix

    output_gain = float(graph.get("output_gain", .55))
    stereo *= output_gain
    return _normalize(stereo)


class BowedStringEngine(InstrumentEngine):
    name = "bowed_string"
    aliases = ("bowed-string",)

    def render_note(self, midi, duration_s, sr, patch, *, velocity=1.0, performance=None):
        return render_bowed_string_note(
            midi, duration_s, sr, patch, velocity=velocity, performance=performance
        )

    def tail_seconds(self, patch):
        graph = _graph(patch)
        env = graph.get("envelope", {})
        return max(0.0, float(env.get("release_s", .18)))

    def _validate(self, subject, patch, *, authoring=False):
        if not isinstance(patch, dict):
            raise InstrumentEngineValidationError(
                f"sound_palette.{subject}.patch must be an object" if authoring
                else f"instrument {subject}: patch must be object"
            )
        if patch.get("kind") not in {"bowed_string", None}:
            raise InstrumentEngineValidationError(f"{subject}: bowed-string patch kind must be bowed_string")
        graph = patch.get("bowed_string_graph")
        if not isinstance(graph, dict):
            raise InstrumentEngineValidationError(f"{subject}: bowed_string_graph must be an object")
        strings = graph.get("strings", {})
        if authoring and not isinstance(strings, dict):
            raise InstrumentEngineValidationError(f"{subject}: bowed strings config must be an object")
        _num(strings.get("max_partials", 14), f"{subject}.bowed.strings.max_partials", 2, 32)
        _num(strings.get("spectral_rolloff", 1.35), f"{subject}.bowed.strings.spectral_rolloff", .4, 3.5)
        _num(strings.get("inharmonicity", .00012), f"{subject}.bowed.strings.inharmonicity", 0, .01)
        bow = graph.get("bow", {})
        _num(bow.get("position", .18), f"{subject}.bowed.bow.position", .02, .49)
        _num(bow.get("pressure", .52), f"{subject}.bowed.bow.pressure", 0, 1)
        _num(bow.get("speed", .58), f"{subject}.bowed.bow.speed", 0, 1)
        _num(bow.get("noise_gain", .018), f"{subject}.bowed.bow.noise_gain", 0, .2)
        low = _num(bow.get("noise_low_hz", 850), f"{subject}.bowed.bow.noise_low_hz", 20, 19000)
        high = _num(bow.get("noise_high_hz", 7800), f"{subject}.bowed.bow.noise_high_hz", 30, 20000)
        if low >= high:
            raise InstrumentEngineValidationError(
                f"{subject}: bowed bow noise_low_hz must be below noise_high_hz"
            )
        vib = graph.get("vibrato", {})
        _num(vib.get("rate_hz", 5.3), f"{subject}.bowed.vibrato.rate_hz", 0, 12)
        _num(vib.get("depth_cents", 14), f"{subject}.bowed.vibrato.depth_cents", 0, 100)
        _num(vib.get("onset_s", .18), f"{subject}.bowed.vibrato.onset_s", 0, 4)
        _num(vib.get("fade_s", .16), f"{subject}.bowed.vibrato.fade_s", .001, 4)
        env = graph.get("envelope", {})
        _num(env.get("attack_s", .055), f"{subject}.bowed.envelope.attack_s", .001, 2)
        _num(env.get("release_s", .18), f"{subject}.bowed.envelope.release_s", .001, 4)
        body = graph.get("body", {})
        modes = body.get("resonances_hz", [])
        gains = body.get("gains", [])
        q_values = body.get("q", [])
        if not isinstance(modes, list) or len(modes) > 16:
            raise InstrumentEngineValidationError(
                f"{subject}: bowed body resonances_hz must contain at most 16 values"
            )
        if gains and (not isinstance(gains, list) or len(gains) != len(modes)):
            raise InstrumentEngineValidationError(
                f"{subject}: bowed body gains must match resonances_hz"
            )
        if q_values and (not isinstance(q_values, list) or len(q_values) != len(modes)):
            raise InstrumentEngineValidationError(
                f"{subject}: bowed body q must match resonances_hz"
            )
        for i, hz in enumerate(modes):
            _num(hz, f"{subject}.bowed.body.resonances_hz[{i}]", 20, 19000)
        for i, gain in enumerate(gains):
            _num(gain, f"{subject}.bowed.body.gains[{i}]", 0, 2)
        for i, q in enumerate(q_values):
            _num(q, f"{subject}.bowed.body.q[{i}]", .25, 30)
        _num(body.get("mix", .18), f"{subject}.bowed.body.mix", 0, 1)
        _num(graph.get("stereo_width", .22), f"{subject}.bowed.stereo_width", 0, 1)
        _num(graph.get("output_gain", .55), f"{subject}.bowed.output_gain", 0, 2)

    def validate_ir_patch(self, subject, patch):
        self._validate(subject, patch, authoring=False)

    def validate_runtime_patch(self, subject, patch):
        self._validate(subject, patch, authoring=False)

    def validate_authoring_patch(self, role, patch):
        self._validate(role, patch, authoring=True)

    def capabilities(self):
        return EngineCapabilities(
            name=self.name,
            extended_tail=True,
            instrument_expression=(
                "bow_pressure", "bow_speed", "bow_position", "bow_noise_gain",
                "vibrato_rate_hz", "vibrato_depth_cents", "vibrato_onset_s",
                "attack_s", "release_s",
            ),
        )


__all__ = ["BowedStringEngine", "render_bowed_string_note"]
