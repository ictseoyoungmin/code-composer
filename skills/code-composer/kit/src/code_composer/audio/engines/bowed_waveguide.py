from __future__ import annotations

"""Deterministic physically-inspired bowed-string waveguide engine.

This implementation is informed by established digital-waveguide bowed-string
literature. It intentionally does not replace the existing ``bowed_string``
additive/synthetic engine; old presets and renders remain stable.
"""

import math
import numpy as np
from scipy.signal import iirpeak, lfilter

from .base import EngineCapabilities, InstrumentEngine, InstrumentEngineValidationError
from ...core.theory import midi_to_hz
from ..bridge_admittance_fit import EraAdmittanceState, validate_era_profile, BridgeAdmittanceFitError


def _num(v, name, lo, hi):
    try:
        x = float(v)
    except Exception as exc:
        raise InstrumentEngineValidationError(f"{name} must be numeric") from exc
    if not (lo <= x <= hi):
        raise InstrumentEngineValidationError(f"{name} outside [{lo},{hi}]")
    return x


def _graph(patch: dict) -> dict:
    g = patch.get("bowed_waveguide_graph")
    if not isinstance(g, dict):
        raise InstrumentEngineValidationError("bowed_waveguide_graph must be an object")
    return g


def _expression(performance: dict | None) -> dict:
    if not isinstance(performance, dict):
        return {}
    x = performance.get("instrument_expression", {})
    return x if isinstance(x, dict) else {}


def _smooth01(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def _hardening_config(graph: dict) -> dict | None:
    cfg = graph.get("expression_hardening", {})
    if not isinstance(cfg, dict) or not bool(cfg.get("enabled", False)):
        return None
    return cfg


def _realism_config(graph: dict) -> dict | None:
    """Return the S12 physical-technique layer when explicitly enabled."""
    cfg = graph.get("realism_hardening", {})
    if not isinstance(cfg, dict) or not bool(cfg.get("enabled", False)):
        return None
    return cfg


def _articulation_expansion_config(graph: dict) -> dict | None:
    """Return the S13 special-articulation layer when explicitly enabled."""
    cfg = graph.get("articulation_expansion", {})
    if not isinstance(cfg, dict) or not bool(cfg.get("enabled", False)):
        return None
    return cfg


def _expanded_articulation(performance: dict | None) -> str:
    art = str((performance or {}).get("articulation", "neutral"))
    return art if art in {"pizzicato", "harmonic", "spiccato"} else ""


def _deterministic_unit(seed: int, key: int, lane: int) -> float:
    """Stable pseudo-random value in [-1, 1] without mutable RNG state.

    S10 uses this only to vary player-control trajectories. It never creates
    notes, timing, pitch choices, or arrangement content.
    """
    x = math.sin((int(seed) * 0.017 + int(key) * 1.61803398875 + int(lane) * 2.41421356237) * 12.9898)
    frac = x * 43758.5453123
    frac = frac - math.floor(frac)
    return 2.0 * frac - 1.0


def _hardening_drift(cfg: dict, sample_index: int, sr: int, *, phase_key: int) -> tuple[float, float, float]:
    """Low-rate deterministic bow-control drift for S10 opt-in presets.

    Two incommensurate oscillators avoid a single obvious LFO while keeping the
    trajectory fully deterministic and reproducible.
    """
    seed = int(cfg.get("seed", 7331))
    t = float(sample_index) / float(sr)
    r1 = max(0.02, float(cfg.get("drift_rate_hz", 0.37)))
    r2 = max(0.02, float(cfg.get("drift_rate_secondary_hz", 0.61)))
    ph1 = math.pi * _deterministic_unit(seed, phase_key, 1)
    ph2 = math.pi * _deterministic_unit(seed, phase_key, 2)
    a = math.sin(2.0 * math.pi * r1 * t + ph1)
    b = math.sin(2.0 * math.pi * r2 * t + ph2)
    c = math.sin(2.0 * math.pi * (0.5 * (r1 + r2)) * t + 0.5 * (ph1 - ph2))
    return (0.72 * a + 0.28 * b, 0.65 * b + 0.35 * c, 0.6 * c + 0.4 * a)


def _hardening_transient(local_t: float, window_s: float) -> float:
    if window_s <= 0.0 or local_t < 0.0 or local_t >= window_s:
        return 0.0
    x = local_t / window_s
    return float((1.0 - x) * (1.0 - x))


def _hardened_controls(
    cfg: dict,
    sample_index: int,
    sr: int,
    *,
    phase_key: int,
    local_t: float,
    pressure: float,
    speed: float,
    beta: float,
    noise_gain: float,
    vib_phase: float,
    vib_gate: float,
    attack_weight: float,
    reversal_weight: float,
) -> tuple[float, float, float, float, float]:
    d_pressure, d_speed, d_position = _hardening_drift(
        cfg, sample_index, sr, phase_key=phase_key
    )
    seed = int(cfg.get("seed", 7331))
    event_amount = max(0.0, float(cfg.get("event_variation", 0.018)))
    ev_p = _deterministic_unit(seed, phase_key, 11)
    ev_s = _deterministic_unit(seed, phase_key, 12)
    ev_b = _deterministic_unit(seed, phase_key, 13)

    p = float(pressure)
    s = float(speed)
    b = float(beta)
    p += float(cfg.get("pressure_drift", 0.028)) * d_pressure + event_amount * ev_p
    s += float(cfg.get("speed_drift", 0.022)) * d_speed + 0.75 * event_amount * ev_s
    b += float(cfg.get("position_drift", 0.0045)) * d_position + 0.08 * event_amount * ev_b

    p += float(cfg.get("attack_pressure_overshoot", 0.045)) * float(attack_weight)
    p -= float(cfg.get("bow_change_pressure_dip", 0.035)) * float(reversal_weight)
    n = float(noise_gain) * (
        1.0
        + float(cfg.get("attack_noise_boost", 0.45)) * float(attack_weight)
        + float(cfg.get("bow_change_noise_boost", 0.35)) * float(reversal_weight)
    )

    excitation = 1.0 + float(cfg.get("vibrato_excitation_coupling", 0.024)) * float(vib_gate) * math.sin(vib_phase + 0.55)
    p += float(cfg.get("vibrato_pressure_coupling", 0.010)) * float(vib_gate) * math.sin(vib_phase + 1.15)

    return (
        max(0.0, min(1.0, p)),
        max(0.0, min(1.0, s)),
        max(0.035, min(0.45, b)),
        max(0.0, n),
        max(0.75, min(1.25, excitation)),
    )


class _FractionalDelay:
    """Linear-interpolating circular delay used by the two string segments."""
    def __init__(self, size: int):
        self.buf = np.zeros(max(16, int(size)), dtype=np.float64)
        self.pos = 0

    def read(self, delay: float) -> float:
        delay = max(1.0, min(float(delay), len(self.buf) - 3.0))
        idx = self.pos - delay
        i0 = math.floor(idx)
        frac = idx - i0
        a = self.buf[i0 % len(self.buf)]
        b = self.buf[(i0 + 1) % len(self.buf)]
        return a + (b - a) * frac

    def write(self, value: float) -> None:
        self.buf[self.pos] = value
        self.pos += 1
        if self.pos >= len(self.buf):
            self.pos = 0


class _WaveguideStringState:
    """Persistent bowed-string state for continuous phrase rendering."""

    def __init__(self, sr: int, graph: dict, *, seed: int):
        self.sr = int(sr)
        string = graph.get("string", {})
        bow = graph.get("bow", {})
        min_hz = max(40.0, float(string.get("minimum_hz", 150.0)))
        max_delay = int(self.sr / min_hz) + 16
        self.neck = _FractionalDelay(max_delay)
        self.bridge = _FractionalDelay(max_delay)
        self.loss = max(0.90, min(0.99995, float(string.get("loop_gain", 0.9974))))
        cutoff = max(300.0, min(self.sr * 0.45, float(string.get("loss_lowpass_hz", 6200.0))))
        self.lp_a = math.exp(-2.0 * math.pi * cutoff / self.sr)
        self.lp_state = 0.0
        self.nut_gain = max(0.90, min(1.0, float(string.get("nut_reflection", 0.998))))
        self.dispersion = max(0.0, min(0.01, float(string.get("dispersion", 0.00055))))
        self.delay_compensation = float(string.get("delay_compensation", 0.2))
        self.slope_lo = max(0.1, float(bow.get("friction_slope_high_pressure", 1.05)))
        self.slope_hi = max(self.slope_lo, float(bow.get("friction_slope_low_pressure", 4.8)))
        self.friction_offset = max(0.55, float(bow.get("friction_offset", 0.78)))
        self.min_rho = max(0.0, min(0.5, float(bow.get("minimum_reflection", 0.012))))
        self.max_rho = max(0.5, min(0.999, float(bow.get("maximum_reflection", 0.985))))
        self.rng = np.random.default_rng(int(seed))
        self.rough_state = 0.0
        self.rough_a = math.exp(-2.0 * math.pi * min(8500.0, self.sr * 0.4) / self.sr)

    def tick(
        self,
        freq_hz: float,
        *,
        bow_velocity: float,
        pressure: float,
        speed: float,
        beta: float,
        noise_gain: float,
        contact: bool,
        friction_noise_scale: float = 1.0,
        bridge_feedback: float = 0.0,
        finger_reflection_scale: float = 1.0,
    ) -> float:
        inst_hz = max(20.0, float(freq_hz))
        total_delay = max(4.0, self.sr / inst_hz - self.delay_compensation)
        total_delay *= 1.0 + self.dispersion * min(1.0, (inst_hz / 1600.0) ** 1.4)
        bridge_delay = max(1.25, total_delay * beta)
        neck_delay = max(1.25, total_delay - bridge_delay)

        bridge_out = self.bridge.read(bridge_delay)
        neck_out = self.neck.read(neck_delay)
        self.lp_state = (1.0 - self.lp_a) * bridge_out + self.lp_a * self.lp_state
        bridge_reflection = -self.loss * self.lp_state
        # S8 optional body/bridge admittance feedback. Older presets pass the
        # default zero and retain their exact reflection path.
        if bridge_feedback:
            bridge_reflection += float(bridge_feedback)
        finger_reflection = -self.nut_gain * neck_out * max(0.90, min(1.0, float(finger_reflection_scale)))
        string_velocity = bridge_reflection + finger_reflection
        injected = 0.0
        if contact:
            p = max(0.0, min(1.0, float(pressure)))
            friction_slope = self.slope_hi + (self.slope_lo - self.slope_hi) * p
            dv = float(bow_velocity) - string_velocity
            shaped = abs(dv) * friction_slope + self.friction_offset
            rho = min(self.max_rho, max(self.min_rho, shaped ** -4.0))
            injected = dv * rho
            if noise_gain > 0.0:
                rough = float(self.rng.standard_normal())
                self.rough_state = (1.0 - self.rough_a) * rough + self.rough_a * self.rough_state
                injected += (
                    self.rough_state * float(noise_gain) * float(friction_noise_scale)
                    * (0.25 + 0.75 * p) * (0.3 + 0.7 * max(0.0, min(1.0, float(speed))))
                )

        self.neck.write(bridge_reflection + injected)
        self.bridge.write(finger_reflection + injected)
        return float(bridge_out)



class _BridgeBodyAdmittanceState:
    """Small causal modal approximation of bridge admittance + body radiation.

    The same body modes are advanced sample-by-sample. Their radiated sum is the
    audible body response, while a separately weighted, tightly bounded modal sum
    is returned one sample later to the string bridge as a weak load velocity.
    This is intentionally conservative: it is an efficient deterministic
    approximation of measured bridge-admittance/radiativity workflows, not a
    fitted model of a named violin.
    """

    def __init__(self, sr: int, body: dict):
        self.sr = int(sr)
        modes = list(body.get("resonances_hz", []))
        gains = list(body.get("gains", []))
        qs = list(body.get("q", []))
        cfg = body.get("bridge_feedback", {}) if isinstance(body.get("bridge_feedback", {}), dict) else {}
        adm = list(cfg.get("admittance_gains", []))
        fitted = cfg.get("fitted_response") if isinstance(cfg.get("fitted_response"), dict) else None
        self.fitted_admittance = EraAdmittanceState.from_profile(fitted, self.sr) if fitted is not None else None
        self.feedback_gain = max(0.0, min(0.03, float(cfg.get("feedback_gain", 0.006))))
        self.feedback_limit = max(0.0, min(0.20, float(cfg.get("max_feedback_velocity", 0.028))))
        self.direct_mix = max(0.0, min(1.0, float(body.get("direct_mix", 0.22))))
        self.sections = []
        for i, hz0 in enumerate(modes):
            hz = float(hz0)
            if not (20.0 < hz < self.sr * 0.46):
                continue
            q = max(0.25, float(qs[i] if i < len(qs) else 4.0))
            b, a = iirpeak(hz / (self.sr * 0.5), Q=q)
            self.sections.append({
                "b0": float(b[0]), "b1": float(b[1]), "b2": float(b[2]),
                "a1": float(a[1]), "a2": float(a[2]),
                "x1": 0.0, "x2": 0.0, "y1": 0.0, "y2": 0.0,
                "radiation_gain": float(gains[i] if i < len(gains) else 0.0),
                "admittance_gain": float(adm[i] if i < len(adm) else 0.0),
            })
        hp_hz = max(5.0, float(body.get("highpass_hz", 70.0)))
        self.hp_a = math.exp(-2.0 * math.pi * hp_hz / self.sr)
        self.hp_prev_x = 0.0
        self.hp_prev_y = 0.0
        cutoff = max(300.0, min(self.sr * 0.45, float(body.get("high_cut_hz", 4600.0))))
        self.lp_a = math.exp(-2.0 * math.pi * cutoff / self.sr)
        self.lp_state = 0.0

    def tick(self, bridge_motion: float) -> tuple[float, float]:
        x = float(bridge_motion)
        # Radiation direct path is DC-safe, while modal sections are inherently
        # band-pass. The modal state is shared by radiation and admittance taps.
        hp = self.hp_a * (self.hp_prev_y + x - self.hp_prev_x)
        self.hp_prev_x, self.hp_prev_y = x, hp
        radiated = hp * self.direct_mix
        admittance = 0.0
        for sec in self.sections:
            y = (
                sec["b0"] * x + sec["b1"] * sec["x1"] + sec["b2"] * sec["x2"]
                - sec["a1"] * sec["y1"] - sec["a2"] * sec["y2"]
            )
            sec["x2"], sec["x1"] = sec["x1"], x
            sec["y2"], sec["y1"] = sec["y1"], y
            radiated += y * sec["radiation_gain"]
            admittance += y * sec["admittance_gain"]
        self.lp_state = (1.0 - self.lp_a) * radiated + self.lp_a * self.lp_state
        if self.fitted_admittance is not None:
            admittance = self.fitted_admittance.tick(x)
        feedback = self.feedback_gain * admittance
        if self.feedback_limit > 0.0:
            feedback = max(-self.feedback_limit, min(self.feedback_limit, feedback))
        return float(feedback), float(self.lp_state)

def _violin_stateful_event(ev: dict) -> dict | None:
    perf = ev.get("performance") if isinstance(ev.get("performance"), dict) else {}
    vr = perf.get("violin_realization") if isinstance(perf.get("violin_realization"), dict) else None
    if not isinstance(vr, dict) or vr.get("double_stop"):
        return None
    left = vr.get("left_hand") if isinstance(vr.get("left_hand"), dict) else {}
    bow = vr.get("bow") if isinstance(vr.get("bow"), dict) else {}
    string_name = left.get("string")
    direction = bow.get("direction")
    group_id = bow.get("group_id")
    if string_name not in {"G", "D", "A", "E"} or direction not in {"down", "up"} or not group_id:
        return None
    return {"performance": perf, "realization": vr, "left_hand": left, "bow": bow}



def _adjacent_violin_strings(a: str | None, b: str | None) -> bool:
    order = {"G": 0, "D": 1, "A": 2, "E": 3}
    return a in order and b in order and abs(order[a] - order[b]) == 1


def _render_bowed_waveguide_track_coupled(
    events, n: int, sr: int, patch: dict, beat_s: float, *, gain: float = 1.0, pan: float = 0.0
):
    """Render a monophonic violin phrase while retaining multiple physical-string states.

    S7 keeps the four violin strings as independent waveguide memories and sums their
    bridge motion into one body/radiativity stage. At adjacent-string crossings the
    modeled bow contact moves smoothly from the outgoing to the incoming string while
    the outgoing string remains free to decay through the common bridge/body path.
    This is intentionally a conservative coupling model: it preserves deterministic
    S5/S6 behavior in older presets and does not claim full finite-element body feedback.
    """
    graph = _graph(patch)
    hard_cfg = _hardening_config(graph)
    realism_cfg = _realism_config(graph)
    cont = graph.get("continuous", {})
    crossing = cont.get("string_crossing", {}) if isinstance(cont, dict) else {}
    if not isinstance(crossing, dict) or not bool(crossing.get("enabled", False)):
        return None

    pitched = [e for e in events if e.get("event_type") != "drum" and "midi" in e]
    if not pitched or len(pitched) != len(events):
        return None
    prepared = []
    for ev in sorted(pitched, key=lambda e: (float(e.get("start_beat", 0)), int(e.get("midi", 0)))):
        info = _violin_stateful_event(ev)
        if info is None:
            return None
        start = int(round(float(ev["start_beat"]) * beat_s * sr))
        end = int(round((float(ev["start_beat"]) + float(ev["duration_beats"])) * beat_s * sr))
        prepared.append((ev, info, start, max(start + 1, end)))
    for a, b in zip(prepared, prepared[1:]):
        if b[2] < a[3]:
            return None
    explicit_pans = {round(float(ev.get("pan", pan)), 9) for ev, *_ in prepared}
    if len(explicit_pans) > 1:
        return None
    pan_value = next(iter(explicit_pans)) if explicit_pans else float(pan)

    bow_cfg = graph.get("bow", {})
    vib_cfg = graph.get("vibrato", {})
    body = graph.get("body", {})
    feedback_cfg = body.get("bridge_feedback", {}) if isinstance(body, dict) else {}
    feedback_enabled = isinstance(feedback_cfg, dict) and bool(feedback_cfg.get("enabled", False))
    body_state = _BridgeBodyAdmittanceState(sr, body) if feedback_enabled else None
    body_feedback = 0.0
    body_radiated = np.zeros(int(n), dtype=np.float64) if feedback_enabled else None
    env_cfg = graph.get("envelope", {})
    attack_s = max(0.002, float(cont.get("initial_attack_s", env_cfg.get("attack_s", 0.055))))
    bow_change_s = max(0.002, min(0.12, float(cont.get("bow_change_s", 0.026))))
    control_slew_s = max(0.0005, min(0.08, float(cont.get("control_slew_s", 0.005))))
    pitch_slew_s = max(0.0001, min(0.05, float(cont.get("pitch_transition_s", 0.0035))))
    gap_limit_s = max(0.0, min(0.25, float(cont.get("state_gap_limit_s", 0.045))))
    crossing_s = max(0.001, min(0.12, float(crossing.get("contact_overlap_s", 0.018))))
    residual_s = max(0.01, min(1.0, float(crossing.get("residual_decay_s", 0.18))))
    residual_mix = max(0.0, min(1.0, float(crossing.get("residual_bridge_mix", 0.34))))
    adjacent_only = bool(crossing.get("adjacent_only", True))
    if realism_cfg is not None:
        open_vibrato_scale = max(0.0, min(1.0, float(realism_cfg.get("open_string_vibrato_scale", 0.08))))
        stopped_reflection_scale = max(0.90, min(1.0, float(realism_cfg.get("stopped_string_reflection_scale", 0.9965))))
        shift_base_s = max(0.001, min(0.05, float(realism_cfg.get("position_shift_base_s", 0.010))))
        shift_per_position_s = max(0.0, min(0.02, float(realism_cfg.get("position_shift_per_position_s", 0.0045))))
        shift_max_s = max(0.005, min(0.08, float(realism_cfg.get("position_shift_max_s", 0.038))))
        shift_pressure_dip = max(0.0, min(0.3, float(realism_cfg.get("position_shift_pressure_dip", 0.055))))
        shift_noise_boost = max(0.0, min(3.0, float(realism_cfg.get("position_shift_noise_boost", 0.30))))
        crossing_stopped_extra_s = max(0.0, min(0.05, float(realism_cfg.get("string_crossing_stopped_extra_s", 0.006))))
        crossing_force_preload = max(0.0, min(0.5, float(realism_cfg.get("string_crossing_force_preload", 0.18))))
        retake_contact_s = max(0.002, min(0.12, float(realism_cfg.get("bow_retake_contact_s", 0.020))))
        retake_pressure_dip = max(0.0, min(0.3, float(realism_cfg.get("bow_retake_pressure_dip", 0.10))))
        retake_noise_boost = max(0.0, min(3.0, float(realism_cfg.get("bow_retake_noise_boost", 0.55))))
    else:
        open_vibrato_scale = 1.0
        stopped_reflection_scale = 1.0
        shift_base_s = pitch_slew_s
        shift_per_position_s = 0.0
        shift_max_s = pitch_slew_s
        shift_pressure_dip = 0.0
        shift_noise_boost = 0.0
        crossing_stopped_extra_s = 0.0
        crossing_force_preload = 0.0
        retake_contact_s = 0.002
        retake_pressure_dip = 0.0
        retake_noise_boost = 0.0

    state_seed = int(bow_cfg.get("seed", 211)) + 19173
    states: dict[str, _WaveguideStringState] = {}
    state_freq: dict[str, float] = {}
    last_active_end: dict[str, int] = {}
    bridge_motion = np.zeros(int(n), dtype=np.float64)
    amplitude_mod = np.ones(int(n), dtype=np.float64) if hard_cfg is not None else None

    current_bow_velocity = 0.0
    current_pressure = float(bow_cfg.get("pressure", 0.55))
    current_beta = float(bow_cfg.get("position", 0.125))
    current_speed = float(bow_cfg.get("speed", 0.56))
    bow_alpha = 1.0 - math.exp(-1.0 / max(1.0, bow_change_s * sr))
    ctl_alpha = 1.0 - math.exp(-1.0 / max(1.0, control_slew_s * sr))
    pitch_alpha = 1.0 - math.exp(-1.0 / max(1.0, pitch_slew_s * sr))
    crossing_samples = max(1, int(round(crossing_s * sr)))
    prev_end = None
    prev_group = None
    prev_direction = None
    prev_string = None
    prev_left_hand = None

    def residual_weight(name: str, sample_index: int) -> float:
        last = last_active_end.get(name)
        if last is None:
            return 0.0
        idle = max(0.0, (sample_index - last) / float(sr))
        if idle >= residual_s:
            return 0.0
        # Smooth, deterministic bridge contribution from strings that have just been released.
        return residual_mix * float((1.0 - idle / residual_s) ** 2)

    def tick_gap(begin: int, finish: int) -> None:
        nonlocal bridge_motion, body_feedback
        if finish <= begin:
            return
        for i in range(max(0, begin), min(int(n), finish)):
            sample_sum = 0.0
            for name, st in states.items():
                out = st.tick(
                    state_freq[name], bow_velocity=0.0, pressure=current_pressure, speed=current_speed,
                    beta=current_beta, noise_gain=0.0, contact=False,
                    bridge_feedback=body_feedback,
                )
                sample_sum += out * residual_weight(name, i)
            bridge_motion[i] += sample_sum
            if body_state is not None:
                body_feedback, body_radiated[i] = body_state.tick(sample_sum)

    for ev_index, (ev, info, start, end) in enumerate(prepared):
        if start >= n:
            break
        end = min(int(n), end)
        expr = _expression(info["performance"])
        bow_plan = info["bow"]
        string_name = info["left_hand"]["string"]
        left_hand = info["left_hand"]
        is_open_string = int(left_hand.get("finger", 0)) == 0
        transition = info["realization"].get("transition", {}) if isinstance(info["realization"].get("transition"), dict) else {}
        shift_positions = max(0, int(transition.get("position_shift", 0)))
        retake = bool(bow_plan.get("retake", False)) if realism_cfg is not None else False
        direction = bow_plan["direction"]
        group_id = bow_plan["group_id"]
        gap_s = 0.0 if prev_end is None else max(0.0, (start - prev_end) / float(sr))
        if prev_end is not None and start > prev_end:
            tick_gap(prev_end, start)

        if string_name not in states or gap_s > residual_s:
            states[string_name] = _WaveguideStringState(
                sr, graph, seed=state_seed + ev_index * 1009 + int(ev["midi"]) * 31 + ord(string_name[0])
            )
            state_freq[string_name] = midi_to_hz(int(ev["midi"]))

        crossing_from = None
        if prev_string is not None and prev_string != string_name and gap_s <= gap_limit_s:
            if (not adjacent_only) or _adjacent_violin_strings(prev_string, string_name):
                crossing_from = prev_string
        stopped_crossing = bool(
            crossing_from is not None
            and (not is_open_string or (isinstance(prev_left_hand, dict) and int(prev_left_hand.get("finger", 0)) != 0))
        )
        crossing_s_event = crossing_s + (crossing_stopped_extra_s if stopped_crossing else 0.0)
        crossing_samples_event = max(1, int(round(crossing_s_event * sr)))
        shift_s_event = pitch_slew_s
        if realism_cfg is not None and shift_positions > 0 and prev_string == string_name:
            shift_s_event = min(shift_max_s, shift_base_s + shift_per_position_s * shift_positions)
        pitch_alpha_event = 1.0 - math.exp(-1.0 / max(1.0, shift_s_event * sr))
        if retake:
            current_bow_velocity = 0.0

        vel = max(0.0, min(1.0, float(ev.get("velocity", 0.8)) * float(gain)))
        pressure_target = max(0.0, min(1.0, float(expr.get("bow_pressure", bow_cfg.get("pressure", 0.55)))))
        speed_target = max(0.0, min(1.0, float(expr.get("bow_speed", bow_cfg.get("speed", 0.56)))))
        beta_target = max(0.035, min(0.45, float(expr.get("bow_position", bow_cfg.get("position", 0.125)))))
        noise_gain = max(0.0, float(expr.get("bow_noise_gain", bow_cfg.get("noise_gain", 0.0045))))
        sign = 1.0 if direction == "down" else -1.0
        target_bow_velocity = sign * (0.025 + 0.20 * speed_target) * (0.45 + 0.55 * vel)
        target_hz = midi_to_hz(int(ev["midi"]))
        vib_rate = max(0.0, float(expr.get("vibrato_rate_hz", vib_cfg.get("rate_hz", 5.4))))
        vib_depth = max(0.0, float(expr.get("vibrato_depth_cents", vib_cfg.get("depth_cents", 13.0))))
        if realism_cfg is not None and is_open_string:
            vib_depth *= open_vibrato_scale
        vib_onset = max(0.0, float(expr.get("vibrato_onset_s", vib_cfg.get("onset_s", 0.22))))
        vib_fade = max(1e-4, float(vib_cfg.get("fade_s", 0.17)))
        _, _, friction_noise_scale = _articulation(info["performance"])

        new_group = group_id != prev_group
        reversing = new_group and prev_direction is not None and direction != prev_direction
        phase_key = ev_index * 1009 + int(ev["midi"]) * 31 + ord(string_name[0])
        if hard_cfg is not None:
            seed = int(hard_cfg.get("seed", 7331))
            time_var = _deterministic_unit(seed, phase_key, 21)
            attack_scale = max(0.72, min(1.28, 1.0 + float(hard_cfg.get("attack_time_variation", 0.18)) * time_var))
            attack_s_event = attack_s * attack_scale
            bow_change_event = bow_change_s * attack_scale
            bow_alpha_event = 1.0 - math.exp(-1.0 / max(1.0, bow_change_event * sr))
            attack_window = max(0.002, float(hard_cfg.get("attack_window_s", 0.038)))
            reversal_window = max(0.002, float(hard_cfg.get("bow_change_window_s", 0.032)))
        else:
            attack_s_event = attack_s
            bow_alpha_event = bow_alpha
            attack_window = 0.0
            reversal_window = 0.0
        for i in range(start, end):
            local_t = (i - start) / float(sr)
            current_pressure += (pressure_target - current_pressure) * ctl_alpha
            current_speed += (speed_target - current_speed) * ctl_alpha
            current_beta += (beta_target - current_beta) * ctl_alpha
            active_freq = state_freq[string_name]
            active_freq += (target_hz - active_freq) * pitch_alpha_event
            state_freq[string_name] = active_freq
            vib_gate = float(_smooth01((local_t - vib_onset) / vib_fade))
            vib_phase = 2.0 * math.pi * vib_rate * local_t
            cents = math.sin(vib_phase) * vib_depth * vib_gate
            active_inst_freq = active_freq * (2.0 ** (cents / 1200.0))

            if prev_group is None and local_t < attack_s_event:
                attack = float(_smooth01(local_t / attack_s_event))
                bow_target = target_bow_velocity * attack
            else:
                bow_target = target_bow_velocity
            alpha = bow_alpha_event if reversing or new_group else ctl_alpha
            current_bow_velocity += (bow_target - current_bow_velocity) * alpha

            tick_pressure = current_pressure
            tick_speed = current_speed
            tick_beta = current_beta
            tick_noise_gain = noise_gain
            excitation = 1.0
            if hard_cfg is not None:
                attack_weight = _hardening_transient(local_t, attack_window) if new_group else 0.0
                reversal_weight = _hardening_transient(local_t, reversal_window) if reversing else 0.0
                tick_pressure, tick_speed, tick_beta, tick_noise_gain, excitation = _hardened_controls(
                    hard_cfg, i, sr, phase_key=phase_key, local_t=local_t,
                    pressure=current_pressure, speed=current_speed, beta=current_beta,
                    noise_gain=noise_gain, vib_phase=vib_phase, vib_gate=vib_gate,
                    attack_weight=attack_weight, reversal_weight=reversal_weight,
                )
                amp_coupling = max(0.0, min(0.35, float(vib_cfg.get("amplitude_coupling", 0.045))))
                amplitude_mod[i] = 1.0 + amp_coupling * math.sin(vib_phase + 0.55) * vib_gate
            if realism_cfg is not None and shift_positions > 0 and prev_string == string_name:
                shift_weight = _hardening_transient(local_t, shift_s_event)
                tick_pressure *= max(0.0, 1.0 - shift_pressure_dip * shift_weight)
                tick_noise_gain *= 1.0 + shift_noise_boost * shift_weight
            retake_gate = 1.0
            if retake and local_t < retake_contact_s:
                retake_gate = float(_smooth01(local_t / retake_contact_s))
                tick_pressure *= max(0.0, 1.0 - retake_pressure_dip * (1.0 - retake_gate))
                tick_noise_gain *= 1.0 + retake_noise_boost * (1.0 - retake_gate)
            effective_bow_velocity = current_bow_velocity * excitation * retake_gate

            if crossing_from is not None and i - start < crossing_samples_event:
                cross = float(_smooth01((i - start) / float(crossing_samples_event)))
                incoming_contact = cross
                outgoing_contact = 1.0 - cross
            else:
                incoming_contact = 1.0
                outgoing_contact = 0.0

            sample_sum = 0.0
            for name, st in states.items():
                if name == string_name:
                    preload = crossing_force_preload if crossing_from is not None else 0.0
                    contact = incoming_contact > 1e-5 or preload > 1e-5
                    reflection_scale = 1.0 if is_open_string else stopped_reflection_scale
                    out = st.tick(
                        active_inst_freq,
                        bow_velocity=effective_bow_velocity * incoming_contact,
                        pressure=tick_pressure * (preload + (1.0 - preload) * (0.35 + 0.65 * incoming_contact)),
                        speed=tick_speed,
                        beta=tick_beta,
                        noise_gain=tick_noise_gain * incoming_contact,
                        contact=contact,
                        friction_noise_scale=friction_noise_scale,
                        bridge_feedback=body_feedback,
                        finger_reflection_scale=reflection_scale,
                    )
                    mix = 1.0
                elif name == crossing_from and outgoing_contact > 1e-5:
                    out = st.tick(
                        state_freq[name],
                        bow_velocity=effective_bow_velocity * outgoing_contact,
                        pressure=tick_pressure * (0.35 + 0.65 * outgoing_contact),
                        speed=tick_speed,
                        beta=tick_beta,
                        noise_gain=tick_noise_gain * outgoing_contact * 0.65,
                        contact=True,
                        friction_noise_scale=friction_noise_scale,
                        bridge_feedback=body_feedback,
                        finger_reflection_scale=(1.0 if isinstance(prev_left_hand, dict) and int(prev_left_hand.get("finger", 0)) == 0 else stopped_reflection_scale),
                    )
                    mix = max(residual_weight(name, i), outgoing_contact)
                else:
                    out = st.tick(
                        state_freq[name], bow_velocity=0.0, pressure=tick_pressure, speed=tick_speed,
                        beta=tick_beta, noise_gain=0.0, contact=False,
                        bridge_feedback=body_feedback,
                    )
                    mix = residual_weight(name, i)
                sample_sum += out * mix
            bridge_motion[i] += sample_sum
            if body_state is not None:
                body_feedback, body_radiated[i] = body_state.tick(sample_sum)

        last_active_end[string_name] = end
        if crossing_from is not None:
            last_active_end[crossing_from] = max(last_active_end.get(crossing_from, 0), start)
        prev_end = end
        prev_group = group_id
        prev_direction = direction
        prev_string = string_name
        prev_left_hand = left_hand

    if prev_end is not None:
        release_s = max(max(0.004, float(env_cfg.get("release_s", 0.16))), residual_s)
        rel_end = min(int(n), prev_end + int(release_s * sr))
        tick_gap(prev_end, rel_end)

    if body_state is not None:
        radiated = body_radiated
    else:
        hp_hz = max(5.0, float(body.get("highpass_hz", 70.0)))
        hp_a = math.exp(-2.0 * math.pi * hp_hz / sr)
        hp = np.empty_like(bridge_motion)
        prev_x = prev_y = 0.0
        for i, x in enumerate(bridge_motion):
            y = hp_a * (prev_y + x - prev_x)
            hp[i] = y
            prev_x, prev_y = x, y
        radiated = _body_filter(hp, sr, body)
    if amplitude_mod is not None:
        radiated *= amplitude_mod
    width = max(0.0, min(1.0, float(graph.get("stereo_width", 0.09))))
    delay_samples = max(0, int(round(width * 9.0)))
    right = np.pad(radiated[:-delay_samples], (delay_samples, 0)) if delay_samples else radiated.copy()
    stereo = np.stack([radiated, right], axis=1)
    stereo *= max(0.0, float(graph.get("output_gain", 0.70)))
    if abs(pan_value) > 1e-9:
        mono = 0.5 * (stereo[:, 0] + stereo[:, 1])
        angle = (max(-1.0, min(1.0, pan_value)) + 1.0) * math.pi * 0.25
        stereo = np.stack([mono * math.cos(angle), mono * math.sin(angle)], axis=1)
    peak = float(np.max(np.abs(stereo))) if len(stereo) else 0.0
    if peak > 1.0:
        stereo /= peak
    return stereo


def render_bowed_waveguide_track(
    events, n: int, sr: int, patch: dict, beat_s: float, *, gain: float = 1.0, pan: float = 0.0
):
    """Render a monophonic violin track with persistent string state.

    This path activates only for patches with ``continuous.enabled`` and for events
    already carrying S3/S4 violin realization. Unsupported polyphony falls back to
    the legacy per-note renderer by returning ``None``.
    """
    graph = _graph(patch)
    art_cfg = _articulation_expansion_config(graph)
    if art_cfg is not None and any(
        _expanded_articulation(e.get("performance"))
        for e in events if isinstance(e, dict)
    ):
        special = _render_articulation_expansion_track(
            events, n, sr, patch, beat_s, gain=gain, pan=pan
        )
        if special is not None:
            return special
    cont = graph.get("continuous", {})
    if not isinstance(cont, dict) or not bool(cont.get("enabled", False)):
        return None
    crossing = cont.get("string_crossing", {})
    if isinstance(crossing, dict) and bool(crossing.get("enabled", False)):
        return _render_bowed_waveguide_track_coupled(
            events, n, sr, patch, beat_s, gain=gain, pan=pan
        )
    pitched = [e for e in events if e.get("event_type") != "drum" and "midi" in e]
    if not pitched or len(pitched) != len(events):
        return None
    prepared = []
    for ev in sorted(pitched, key=lambda e: (float(e.get("start_beat", 0)), int(e.get("midi", 0)))):
        info = _violin_stateful_event(ev)
        if info is None:
            return None
        start = int(round(float(ev["start_beat"]) * beat_s * sr))
        end = int(round((float(ev["start_beat"]) + float(ev["duration_beats"])) * beat_s * sr))
        prepared.append((ev, info, start, max(start + 1, end)))
    for a, b in zip(prepared, prepared[1:]):
        if b[2] < a[3]:
            return None
    explicit_pans = {round(float(ev.get("pan", pan)), 9) for ev, *_ in prepared}
    if len(explicit_pans) > 1:
        return None
    pan_value = next(iter(explicit_pans)) if explicit_pans else float(pan)

    bow_cfg = graph.get("bow", {})
    vib_cfg = graph.get("vibrato", {})
    body = graph.get("body", {})
    env_cfg = graph.get("envelope", {})
    attack_s = max(0.002, float(cont.get("initial_attack_s", env_cfg.get("attack_s", 0.055))))
    bow_change_s = max(0.002, min(0.12, float(cont.get("bow_change_s", 0.026))))
    control_slew_s = max(0.0005, min(0.08, float(cont.get("control_slew_s", 0.005))))
    pitch_slew_s = max(0.0001, min(0.05, float(cont.get("pitch_transition_s", 0.0035))))
    gap_limit_s = max(0.0, min(0.25, float(cont.get("state_gap_limit_s", 0.045))))
    state_seed = int(bow_cfg.get("seed", 211)) + 9173
    state = None
    current_string = None
    current_freq = None
    current_bow_velocity = 0.0
    current_pressure = float(bow_cfg.get("pressure", 0.55))
    current_beta = float(bow_cfg.get("position", 0.125))
    current_speed = float(bow_cfg.get("speed", 0.56))
    bridge_motion = np.zeros(int(n), dtype=np.float64)

    bow_alpha = 1.0 - math.exp(-1.0 / max(1.0, bow_change_s * sr))
    ctl_alpha = 1.0 - math.exp(-1.0 / max(1.0, control_slew_s * sr))
    pitch_alpha = 1.0 - math.exp(-1.0 / max(1.0, pitch_slew_s * sr))
    prev_end = None
    prev_group = None
    prev_direction = None

    for ev_index, (ev, info, start, end) in enumerate(prepared):
        if start >= n:
            break
        end = min(int(n), end)
        expr = _expression(info["performance"])
        vr = info["realization"]
        bow_plan = info["bow"]
        string_name = info["left_hand"]["string"]
        direction = bow_plan["direction"]
        group_id = bow_plan["group_id"]
        gap_s = 0.0 if prev_end is None else max(0.0, (start - prev_end) / float(sr))
        same_string_continuation = (
            state is not None and current_string == string_name and gap_s <= gap_limit_s
        )
        if not same_string_continuation:
            state = _WaveguideStringState(sr, graph, seed=state_seed + ev_index * 1009 + int(ev["midi"]) * 31)
            current_string = string_name
            current_freq = midi_to_hz(int(ev["midi"]))
            current_bow_velocity = 0.0
            prev_group = None
            prev_direction = None
        elif prev_end is not None and start > prev_end:
            # Let the same string decay naturally while the bow is off the string.
            for i in range(prev_end, min(start, n)):
                bridge_motion[i] += state.tick(
                    current_freq, bow_velocity=0.0, pressure=current_pressure, speed=current_speed,
                    beta=current_beta, noise_gain=0.0, contact=False
                )

        vel = max(0.0, min(1.0, float(ev.get("velocity", 0.8)) * float(gain)))
        pressure_target = max(0.0, min(1.0, float(expr.get("bow_pressure", bow_cfg.get("pressure", 0.55)))))
        speed_target = max(0.0, min(1.0, float(expr.get("bow_speed", bow_cfg.get("speed", 0.56)))))
        beta_target = max(0.035, min(0.45, float(expr.get("bow_position", bow_cfg.get("position", 0.125)))))
        noise_gain = max(0.0, float(expr.get("bow_noise_gain", bow_cfg.get("noise_gain", 0.0045))))
        sign = 1.0 if direction == "down" else -1.0
        target_bow_velocity = sign * (0.025 + 0.20 * speed_target) * (0.45 + 0.55 * vel)
        target_hz = midi_to_hz(int(ev["midi"]))
        vib_rate = max(0.0, float(expr.get("vibrato_rate_hz", vib_cfg.get("rate_hz", 5.4))))
        vib_depth = max(0.0, float(expr.get("vibrato_depth_cents", vib_cfg.get("depth_cents", 13.0))))
        vib_onset = max(0.0, float(expr.get("vibrato_onset_s", vib_cfg.get("onset_s", 0.22))))
        vib_fade = max(1e-4, float(vib_cfg.get("fade_s", 0.17)))
        _, _, friction_noise_scale = _articulation(info["performance"])

        new_group = group_id != prev_group
        reversing = new_group and prev_direction is not None and direction != prev_direction and same_string_continuation
        for i in range(start, end):
            local_t = (i - start) / float(sr)
            current_pressure += (pressure_target - current_pressure) * ctl_alpha
            current_speed += (speed_target - current_speed) * ctl_alpha
            current_beta += (beta_target - current_beta) * ctl_alpha
            current_freq += (target_hz - current_freq) * pitch_alpha
            vib_gate = float(_smooth01((local_t - vib_onset) / vib_fade))
            cents = math.sin(2.0 * math.pi * vib_rate * local_t) * vib_depth * vib_gate
            freq = current_freq * (2.0 ** (cents / 1200.0))

            if prev_group is None and local_t < attack_s:
                attack = float(_smooth01(local_t / attack_s))
                bow_target = target_bow_velocity * attack
            else:
                bow_target = target_bow_velocity
            alpha = bow_alpha if reversing or new_group else ctl_alpha
            current_bow_velocity += (bow_target - current_bow_velocity) * alpha
            bridge_motion[i] += state.tick(
                freq,
                bow_velocity=current_bow_velocity,
                pressure=current_pressure,
                speed=current_speed,
                beta=current_beta,
                noise_gain=noise_gain,
                contact=True,
                friction_noise_scale=friction_noise_scale,
            )
        prev_end = end
        prev_group = group_id
        prev_direction = direction

    if state is not None and prev_end is not None:
        release_s = max(0.004, float(env_cfg.get("release_s", 0.16)))
        rel_end = min(int(n), prev_end + int(release_s * sr))
        for i in range(prev_end, rel_end):
            current_bow_velocity += (0.0 - current_bow_velocity) * bow_alpha
            bridge_motion[i] += state.tick(
                current_freq, bow_velocity=current_bow_velocity, pressure=current_pressure,
                speed=current_speed, beta=current_beta, noise_gain=0.0, contact=abs(current_bow_velocity) > 1e-5
            )

    # The body/radiativity stage is applied once to the continuous bridge motion.
    hp_hz = max(5.0, float(body.get("highpass_hz", 70.0)))
    hp_a = math.exp(-2.0 * math.pi * hp_hz / sr)
    hp = np.empty_like(bridge_motion)
    prev_x = prev_y = 0.0
    for i, x in enumerate(bridge_motion):
        y = hp_a * (prev_y + x - prev_x)
        hp[i] = y
        prev_x, prev_y = x, y
    radiated = _body_filter(hp, sr, body)
    width = max(0.0, min(1.0, float(graph.get("stereo_width", 0.09))))
    delay_samples = max(0, int(round(width * 9.0)))
    right = np.pad(radiated[:-delay_samples], (delay_samples, 0)) if delay_samples else radiated.copy()
    stereo = np.stack([radiated, right], axis=1)
    stereo *= max(0.0, float(graph.get("output_gain", 0.70)))
    if abs(pan_value) > 1e-9:
        mono = 0.5 * (stereo[:, 0] + stereo[:, 1])
        angle = (max(-1.0, min(1.0, pan_value)) + 1.0) * math.pi * 0.25
        stereo = np.stack([mono * math.cos(angle), mono * math.sin(angle)], axis=1)
    peak = float(np.max(np.abs(stereo))) if len(stereo) else 0.0
    if peak > 1.0:
        stereo /= peak
    return stereo


def _body_filter(signal: np.ndarray, sr: int, body: dict) -> np.ndarray:
    modes = list(body.get("resonances_hz", []))
    gains = list(body.get("gains", []))
    qs = list(body.get("q", []))
    if not modes:
        return signal.copy()
    out = np.zeros_like(signal, dtype=np.float64)
    for i, hz0 in enumerate(modes):
        hz = float(hz0)
        if not (20.0 < hz < sr * 0.46):
            continue
        gain = float(gains[i] if i < len(gains) else 0.0)
        q = max(0.25, float(qs[i] if i < len(qs) else 4.0))
        b, a = iirpeak(hz / (sr * 0.5), Q=q)
        out += lfilter(b, a, signal) * gain
    direct = max(0.0, min(1.0, float(body.get("direct_mix", 0.22))))
    out = out + signal * direct
    cutoff = float(body.get("high_cut_hz", 4600.0))
    if cutoff > 0 and len(out):
        a = math.exp(-2.0 * math.pi * min(cutoff, sr * 0.45) / sr)
        y = np.empty_like(out)
        state = 0.0
        for i, x in enumerate(out):
            state = (1.0 - a) * x + a * state
            y[i] = state
        out = y
    return out


def _articulation(performance: dict | None) -> tuple[float, float, float]:
    art = str((performance or {}).get("articulation", "neutral"))
    return {
        "legato": (1.20, 1.18, 0.82),
        "tenuto": (1.00, 1.08, 0.92),
        "neutral": (1.00, 1.00, 1.00),
        "staccato": (0.72, 0.55, 1.06),
        "accent": (0.58, 0.82, 1.20),
        "marcato": (0.50, 0.72, 1.32),
        "harmonic": (0.82, 1.18, 0.62),
        "spiccato": (0.38, 0.80, 1.26),
        "pizzicato": (0.20, 1.35, 0.0),
    }.get(art, (1.0, 1.0, 1.0))



def _stereo_from_mono(signal: np.ndarray, graph: dict, *, pan: float = 0.0) -> np.ndarray:
    width = max(0.0, min(1.0, float(graph.get("stereo_width", 0.09))))
    delay_samples = max(0, int(round(width * 9.0)))
    right = np.pad(signal[:-delay_samples], (delay_samples, 0)) if delay_samples else signal.copy()
    stereo = np.stack([signal, right], axis=1)
    stereo *= max(0.0, float(graph.get("output_gain", 0.70)))
    if abs(float(pan)) > 1e-9:
        mono = 0.5 * (stereo[:, 0] + stereo[:, 1])
        angle = (max(-1.0, min(1.0, float(pan))) + 1.0) * math.pi * 0.25
        stereo = np.stack([mono * math.cos(angle), mono * math.sin(angle)], axis=1)
    peak = float(np.max(np.abs(stereo))) if len(stereo) else 0.0
    if peak > 1.0:
        stereo /= peak
    return stereo


def _render_pizzicato_note(
    midi: int,
    duration_s: float,
    sr: int,
    graph: dict,
    cfg: dict,
    *,
    velocity: float,
    performance: dict | None,
) -> np.ndarray:
    """Physically inspired violin pizzicato: pluck excitation + free decay."""
    body = graph.get("body", {})
    base_hz = midi_to_hz(int(midi))
    vel = max(0.0, min(1.0, float(velocity)))
    decay_s = max(0.08, min(3.0, float(cfg.get("pizzicato_decay_s", 1.05))))
    total_s = max(float(duration_s), decay_s)
    n = max(2, int(round(total_s * sr)))
    t = np.arange(n, dtype=np.float64) / float(sr)
    pluck_pos = max(0.04, min(0.48, float(cfg.get("pizzicato_pluck_position", 0.19))))
    rolloff = max(0.6, min(3.0, float(cfg.get("pizzicato_partial_rolloff", 1.28))))
    max_partial = max(1, min(28, int((sr * 0.45) // max(base_hz, 1e-6))))
    bridge = np.zeros(n, dtype=np.float64)
    vr = (performance or {}).get("violin_realization", {}) if isinstance(performance, dict) else {}
    left = vr.get("left_hand", {}) if isinstance(vr, dict) else {}
    stopped = int(left.get("finger", 0)) != 0 if isinstance(left, dict) else True
    damping_scale = 1.10 if stopped else 0.92
    for partial in range(1, max_partial + 1):
        position_gain = math.sin(math.pi * partial * pluck_pos)
        amp = position_gain / (partial ** rolloff)
        decay_rate = damping_scale * (1.25 + 0.22 * (partial ** 1.16)) / max(0.12, decay_s)
        phase = 0.17 * partial
        bridge += amp * np.sin(2.0 * math.pi * base_hz * partial * t + phase) * np.exp(-decay_rate * t)
    bridge *= 0.12 * (0.35 + 0.65 * vel)
    noise_gain = max(0.0, min(0.05, float(cfg.get("pizzicato_finger_noise_gain", 0.006))))
    if noise_gain > 0.0:
        seed = 4409 + int(midi) * 97 + n % 8191
        rng = np.random.default_rng(seed)
        burst_n = min(n, max(2, int(0.012 * sr)))
        burst = rng.standard_normal(burst_n).astype(np.float64)
        burst *= np.linspace(1.0, 0.0, burst_n) ** 2
        bridge[:burst_n] += burst * noise_gain * (0.25 + 0.75 * vel)
    radiated = _body_filter(bridge, sr, body)
    return _stereo_from_mono(radiated, graph)


def _render_articulation_expansion_track(
    events, n: int, sr: int, patch: dict, beat_s: float, *, gain: float = 1.0, pan: float = 0.0
):
    """Hybrid S13 renderer preserving continuous arco between special notes."""
    graph = _graph(patch)
    cfg = _articulation_expansion_config(graph)
    if cfg is None:
        return None
    pitched = [e for e in events if e.get("event_type") != "drum" and "midi" in e]
    if not pitched or len(pitched) != len(events):
        return None
    ordered = sorted(pitched, key=lambda e: (float(e.get("start_beat", 0)), int(e.get("midi", 0))))
    if not any(_expanded_articulation(e.get("performance")) for e in ordered):
        return None
    out = np.zeros((int(n), 2), dtype=np.float64)
    regular_segment = []

    def flush_segment():
        nonlocal regular_segment, out
        if not regular_segment:
            return
        seg = _render_bowed_waveguide_track_coupled(
            regular_segment, n, sr, patch, beat_s, gain=gain, pan=pan
        )
        if seg is None:
            for sev in regular_segment:
                start = int(round(float(sev["start_beat"]) * beat_s * sr))
                note = render_bowed_waveguide_note(
                    int(sev["midi"]), float(sev["duration_beats"]) * beat_s, sr, patch,
                    velocity=float(sev.get("velocity", 0.8)) * float(gain),
                    performance=sev.get("performance"),
                )
                end = min(int(n), start + len(note))
                if end > start:
                    out[start:end] += note[: end-start]
        else:
            out += seg
        regular_segment = []

    for ev in ordered:
        art = _expanded_articulation(ev.get("performance"))
        if not art:
            regular_segment.append(ev)
            continue
        flush_segment()
        start = int(round(float(ev["start_beat"]) * beat_s * sr))
        note = render_bowed_waveguide_note(
            int(ev["midi"]), float(ev["duration_beats"]) * beat_s, sr, patch,
            velocity=float(ev.get("velocity", 0.8)) * float(gain),
            performance=ev.get("performance"),
        )
        event_pan = float(ev.get("pan", pan))
        if abs(event_pan) > 1e-9 and len(note):
            mono = 0.5 * (note[:, 0] + note[:, 1])
            angle = (max(-1.0, min(1.0, event_pan)) + 1.0) * math.pi * 0.25
            note = np.stack([mono * math.cos(angle), mono * math.sin(angle)], axis=1)
        end = min(int(n), start + len(note))
        if end > start:
            out[start:end] += note[: end-start]
    flush_segment()
    peak = float(np.max(np.abs(out))) if len(out) else 0.0
    if peak > 1.0:
        out /= peak
    return out


def render_bowed_waveguide_note(
    midi: int,
    duration_s: float,
    sr: int,
    patch: dict,
    *,
    velocity: float = 1.0,
    performance: dict | None = None,
):
    """Render one modeled bowed-string note using a two-segment digital waveguide."""
    graph = _graph(patch)
    hard_cfg = _hardening_config(graph)
    art_cfg = _articulation_expansion_config(graph)
    special_art = _expanded_articulation(performance) if art_cfg is not None else ""
    if special_art == "pizzicato":
        return _render_pizzicato_note(
            midi, duration_s, sr, graph, art_cfg, velocity=velocity, performance=performance
        )
    string = graph.get("string", {})
    bow = graph.get("bow", {})
    vib = graph.get("vibrato", {})
    body = graph.get("body", {})
    env_cfg = graph.get("envelope", {})
    expr = _expression(performance)

    atk_scale, rel_scale, friction_noise_scale = _articulation(performance)
    attack_s = max(0.002, float(expr.get("attack_s", env_cfg.get("attack_s", 0.055))) * atk_scale)
    release_s = max(0.004, float(expr.get("release_s", env_cfg.get("release_s", 0.16))) * rel_scale)
    active_n = max(1, int(max(1e-5, float(duration_s)) * sr))
    hard_phase_key = int(midi) * 811 + active_n % 65521
    if hard_cfg is not None:
        hard_seed = int(hard_cfg.get("seed", 7331))
        attack_s *= max(0.72, min(1.28, 1.0 + float(hard_cfg.get("attack_time_variation", 0.18)) * _deterministic_unit(hard_seed, hard_phase_key, 21)))
    n = max(2, active_n + int(release_s * sr))
    t = np.arange(n, dtype=np.float64) / float(sr)

    vel = max(0.0, min(1.0, float(velocity)))
    base_hz = midi_to_hz(int(midi))
    pressure = max(0.0, min(1.0, float(expr.get("bow_pressure", bow.get("pressure", 0.55)))))
    speed = max(0.0, min(1.0, float(expr.get("bow_speed", bow.get("speed", 0.56)))))
    beta = max(0.035, min(0.45, float(expr.get("bow_position", bow.get("position", 0.125)))))
    if art_cfg is not None and special_art == "harmonic":
        pressure *= max(0.05, min(1.0, float(art_cfg.get("harmonic_pressure_scale", 0.52))))
        speed = max(0.0, min(1.0, speed * float(art_cfg.get("harmonic_speed_scale", 0.78))))
        beta = max(0.035, min(0.45, float(art_cfg.get("harmonic_bow_position", 0.085))))
    elif art_cfg is not None and special_art == "spiccato":
        pressure *= max(0.05, min(1.5, float(art_cfg.get("spiccato_pressure_scale", 0.78))))
        speed = max(0.0, min(1.0, speed * float(art_cfg.get("spiccato_speed_scale", 1.12))))

    vib_rate = max(0.0, float(expr.get("vibrato_rate_hz", vib.get("rate_hz", 5.4))))
    vib_depth = max(0.0, float(expr.get("vibrato_depth_cents", vib.get("depth_cents", 13.0))))
    if art_cfg is not None and special_art == "harmonic":
        vib_depth *= max(0.0, min(1.0, float(art_cfg.get("harmonic_vibrato_scale", 0.18))))
    vib_onset = max(0.0, float(expr.get("vibrato_onset_s", vib.get("onset_s", 0.22))))
    vib_fade = max(1e-4, float(vib.get("fade_s", 0.17)))
    vib_gate = _smooth01((t - vib_onset) / vib_fade)
    vibrato_cents = np.sin(2.0 * math.pi * vib_rate * t) * vib_depth * vib_gate
    freq_ratio = 2.0 ** (vibrato_cents / 1200.0)

    # This envelope drives bow velocity. Sustained string output comes from the
    # nonlinear feedback loop rather than an amplitude envelope on oscillators.
    env = np.ones(n, dtype=np.float64)
    na = min(active_n, max(2, int(attack_s * sr)))
    env[:na] = _smooth01(np.linspace(0.0, 1.0, na))
    if active_n < n:
        env[active_n:] = _smooth01(np.linspace(1.0, 0.0, n - active_n))

    min_hz = max(40.0, float(string.get("minimum_hz", 150.0)))
    max_delay = int(sr / min_hz) + 16
    neck = _FractionalDelay(max_delay)
    bridge = _FractionalDelay(max_delay)

    loss = max(0.90, min(0.99995, float(string.get("loop_gain", 0.9974))))
    loss_cutoff = max(300.0, min(sr * 0.45, float(string.get("loss_lowpass_hz", 6200.0))))
    lp_a = math.exp(-2.0 * math.pi * loss_cutoff / sr)
    lp_state = 0.0
    nut_gain = max(0.90, min(1.0, float(string.get("nut_reflection", 0.998))))
    dispersion = max(0.0, min(0.01, float(string.get("dispersion", 0.00055))))

    slope_lo = max(0.1, float(bow.get("friction_slope_high_pressure", 1.05)))
    slope_hi = max(slope_lo, float(bow.get("friction_slope_low_pressure", 4.8)))
    friction_slope = slope_hi + (slope_lo - slope_hi) * pressure
    friction_offset = max(0.55, float(bow.get("friction_offset", 0.78)))
    min_rho = max(0.0, min(0.5, float(bow.get("minimum_reflection", 0.012))))
    max_rho = max(0.5, min(0.999, float(bow.get("maximum_reflection", 0.985))))
    max_bow_velocity = (0.025 + 0.20 * speed) * (0.45 + 0.55 * vel)

    bridge_velocity = np.zeros(n, dtype=np.float64)
    noise_gain = max(0.0, float(expr.get("bow_noise_gain", bow.get("noise_gain", 0.0045))))
    spiccato_contact_n = active_n
    if art_cfg is not None and special_art == "spiccato":
        frac = max(0.05, min(0.9, float(art_cfg.get("spiccato_contact_fraction", 0.34))))
        contact_s = max(
            float(art_cfg.get("spiccato_contact_min_s", 0.025)),
            min(float(art_cfg.get("spiccato_contact_max_s", 0.085)), float(duration_s) * frac),
        )
        spiccato_contact_n = max(1, min(active_n, int(round(contact_s * sr))))
        noise_gain *= max(0.0, min(4.0, float(art_cfg.get("spiccato_noise_boost", 1.18))))
    seed = int(bow.get("seed", 211)) + int(midi) * 811 + active_n % 65521
    rng = np.random.default_rng(seed)
    rough = rng.standard_normal(n).astype(np.float64) if noise_gain > 0 else np.zeros(n)
    rough_state = 0.0
    hard_attack_window = max(0.002, float(hard_cfg.get("attack_window_s", 0.038))) if hard_cfg is not None else 0.0
    rough_a = math.exp(-2.0 * math.pi * min(8500.0, sr * 0.4) / sr)
    delay_compensation = float(string.get("delay_compensation", 0.2))

    for i in range(n):
        inst_hz = base_hz * float(freq_ratio[i])
        tick_pressure = pressure
        tick_speed = speed
        tick_beta = beta
        tick_noise_gain = noise_gain
        excitation = 1.0
        if hard_cfg is not None:
            local_t = float(t[i])
            vib_phase = 2.0 * math.pi * vib_rate * local_t
            attack_weight = _hardening_transient(local_t, hard_attack_window)
            tick_pressure, tick_speed, tick_beta, tick_noise_gain, excitation = _hardened_controls(
                hard_cfg, i, sr, phase_key=hard_phase_key, local_t=local_t,
                pressure=pressure, speed=speed, beta=beta, noise_gain=noise_gain,
                vib_phase=vib_phase, vib_gate=float(vib_gate[i]),
                attack_weight=attack_weight, reversal_weight=0.0,
            )
        total_delay = max(4.0, sr / inst_hz - delay_compensation)
        total_delay *= 1.0 + dispersion * min(1.0, (inst_hz / 1600.0) ** 1.4)
        bridge_delay = max(1.25, total_delay * tick_beta)
        neck_delay = max(1.25, total_delay - bridge_delay)

        bridge_out = bridge.read(bridge_delay)
        neck_out = neck.read(neck_delay)
        lp_state = (1.0 - lp_a) * bridge_out + lp_a * lp_state
        bridge_reflection = -loss * lp_state
        finger_reflection = -nut_gain * neck_out
        string_velocity = bridge_reflection + finger_reflection

        free_spiccato = special_art == "spiccato" and i >= spiccato_contact_n
        if hard_cfg is not None:
            local_max_bow_velocity = (0.025 + 0.20 * tick_speed) * (0.45 + 0.55 * vel)
            tick_friction_slope = slope_hi + (slope_lo - slope_hi) * tick_pressure
            bow_velocity = 0.0 if free_spiccato else local_max_bow_velocity * float(env[i]) * excitation
        else:
            tick_friction_slope = friction_slope
            bow_velocity = 0.0 if free_spiccato else max_bow_velocity * float(env[i])
        if free_spiccato:
            injected = 0.0
        else:
            dv = bow_velocity - string_velocity
            shaped = abs(dv) * tick_friction_slope + friction_offset
            rho = min(max_rho, max(min_rho, shaped ** -4.0))
            injected = dv * rho

        if (not free_spiccato) and tick_noise_gain > 0.0:
            rough_state = (1.0 - rough_a) * rough[i] + rough_a * rough_state
            injected += (
                rough_state * tick_noise_gain * friction_noise_scale * float(env[i])
                * (0.25 + 0.75 * tick_pressure) * (0.3 + 0.7 * tick_speed)
            )

        neck.write(bridge_reflection + injected)
        bridge.write(finger_reflection + injected)
        bridge_velocity[i] = bridge_out

    # Remove startup drift before the radiativity model.
    hp_hz = max(5.0, float(body.get("highpass_hz", 70.0)))
    hp_a = math.exp(-2.0 * math.pi * hp_hz / sr)
    hp = np.empty_like(bridge_velocity)
    prev_x = 0.0
    prev_y = 0.0
    for i, x in enumerate(bridge_velocity):
        y = hp_a * (prev_y + x - prev_x)
        hp[i] = y
        prev_x, prev_y = x, y

    radiated = _body_filter(hp, sr, body)
    if art_cfg is not None and special_art == "harmonic":
        cut = max(80.0, min(sr * 0.40, float(art_cfg.get("harmonic_low_cut_hz", 420.0))))
        a_h = math.exp(-2.0 * math.pi * cut / sr)
        shaped_h = np.empty_like(radiated)
        px = py = 0.0
        for j, x in enumerate(radiated):
            y = a_h * (py + x - px)
            shaped_h[j] = y
            px, py = x, y
        radiated = shaped_h
    amp_vib = max(0.0, min(0.35, float(vib.get("amplitude_coupling", 0.045))))
    if amp_vib > 0.0:
        radiated *= 1.0 + amp_vib * np.sin(2.0 * math.pi * vib_rate * t + 0.55) * vib_gate

    width = max(0.0, min(1.0, float(graph.get("stereo_width", 0.09))))
    delay_samples = max(0, int(round(width * 9.0)))
    right = np.pad(radiated[:-delay_samples], (delay_samples, 0)) if delay_samples else radiated.copy()
    stereo = np.stack([radiated, right], axis=1)
    stereo *= max(0.0, float(graph.get("output_gain", 0.70)))
    peak = float(np.max(np.abs(stereo))) if len(stereo) else 0.0
    if peak > 1.0:
        stereo /= peak
    return stereo


class BowedWaveguideEngine(InstrumentEngine):
    name = "bowed_waveguide"
    aliases = ("bowed-waveguide", "modeled_bowed_string")

    def render_note(self, midi, duration_s, sr, patch, *, velocity=1.0, performance=None):
        return render_bowed_waveguide_note(
            midi, duration_s, sr, patch, velocity=velocity, performance=performance
        )

    def render_track(self, events, n, sr, patch, beat_s, *, gain=1.0, pan=0.0):
        return render_bowed_waveguide_track(
            events, n, sr, patch, beat_s, gain=gain, pan=pan
        )

    def tail_seconds(self, patch):
        g = _graph(patch)
        env = g.get("envelope", {})
        tail = max(0.0, float(env.get("release_s", 0.16)))
        cont = g.get("continuous", {})
        if isinstance(cont, dict):
            crossing = cont.get("string_crossing", {})
            if isinstance(crossing, dict) and bool(crossing.get("enabled", False)):
                tail = max(tail, float(crossing.get("residual_decay_s", 0.18)))
        art = g.get("articulation_expansion", {})
        if isinstance(art, dict) and bool(art.get("enabled", False)):
            tail = max(tail, float(art.get("pizzicato_decay_s", 1.05)))
        return tail

    def _validate(self, subject, patch):
        if not isinstance(patch, dict):
            raise InstrumentEngineValidationError(f"{subject}: patch must be object")
        if patch.get("kind") not in {"bowed_waveguide", None}:
            raise InstrumentEngineValidationError(f"{subject}: modeled bowed patch kind must be bowed_waveguide")
        g = patch.get("bowed_waveguide_graph")
        if not isinstance(g, dict):
            raise InstrumentEngineValidationError(f"{subject}: bowed_waveguide_graph must be an object")

        string = g.get("string", {})
        _num(string.get("minimum_hz", 150), f"{subject}.waveguide.string.minimum_hz", 30, 400)
        _num(string.get("loop_gain", .9974), f"{subject}.waveguide.string.loop_gain", .90, .99995)
        _num(string.get("loss_lowpass_hz", 6200), f"{subject}.waveguide.string.loss_lowpass_hz", 300, 19000)
        _num(string.get("nut_reflection", .998), f"{subject}.waveguide.string.nut_reflection", .90, 1.0)
        _num(string.get("dispersion", .00055), f"{subject}.waveguide.string.dispersion", 0, .01)
        _num(string.get("delay_compensation", 0.2), f"{subject}.waveguide.string.delay_compensation", 0, 8)

        bow = g.get("bow", {})
        _num(bow.get("position", .125), f"{subject}.waveguide.bow.position", .035, .45)
        _num(bow.get("pressure", .55), f"{subject}.waveguide.bow.pressure", 0, 1)
        _num(bow.get("speed", .56), f"{subject}.waveguide.bow.speed", 0, 1)
        _num(bow.get("noise_gain", .0045), f"{subject}.waveguide.bow.noise_gain", 0, .08)
        lo = _num(bow.get("friction_slope_high_pressure", 1.05), f"{subject}.waveguide.bow.friction_slope_high_pressure", .1, 8)
        hi = _num(bow.get("friction_slope_low_pressure", 4.8), f"{subject}.waveguide.bow.friction_slope_low_pressure", .1, 12)
        if lo > hi:
            raise InstrumentEngineValidationError(f"{subject}: high-pressure friction slope must not exceed low-pressure slope")
        _num(bow.get("friction_offset", .78), f"{subject}.waveguide.bow.friction_offset", .55, 1.5)
        min_rho = _num(bow.get("minimum_reflection", .012), f"{subject}.waveguide.bow.minimum_reflection", 0, .5)
        max_rho = _num(bow.get("maximum_reflection", .985), f"{subject}.waveguide.bow.maximum_reflection", .5, .999)
        if min_rho >= max_rho:
            raise InstrumentEngineValidationError(f"{subject}: minimum_reflection must be below maximum_reflection")

        vib = g.get("vibrato", {})
        _num(vib.get("rate_hz", 5.4), f"{subject}.waveguide.vibrato.rate_hz", 0, 12)
        _num(vib.get("depth_cents", 13), f"{subject}.waveguide.vibrato.depth_cents", 0, 100)
        _num(vib.get("onset_s", .22), f"{subject}.waveguide.vibrato.onset_s", 0, 4)
        _num(vib.get("fade_s", .17), f"{subject}.waveguide.vibrato.fade_s", .001, 4)
        _num(vib.get("amplitude_coupling", .045), f"{subject}.waveguide.vibrato.amplitude_coupling", 0, .35)

        hardening = g.get("expression_hardening", {})
        if hardening and not isinstance(hardening, dict):
            raise InstrumentEngineValidationError(f"{subject}: expression_hardening must be an object")
        if isinstance(hardening, dict):
            if "enabled" in hardening and not isinstance(hardening.get("enabled"), bool):
                raise InstrumentEngineValidationError(f"{subject}: expression_hardening.enabled must be boolean")
            if "seed" in hardening and not isinstance(hardening.get("seed"), int):
                raise InstrumentEngineValidationError(f"{subject}: expression_hardening.seed must be integer")
            _num(hardening.get("drift_rate_hz", .37), f"{subject}.waveguide.expression_hardening.drift_rate_hz", .02, 4)
            _num(hardening.get("drift_rate_secondary_hz", .61), f"{subject}.waveguide.expression_hardening.drift_rate_secondary_hz", .02, 4)
            _num(hardening.get("pressure_drift", .028), f"{subject}.waveguide.expression_hardening.pressure_drift", 0, .12)
            _num(hardening.get("speed_drift", .022), f"{subject}.waveguide.expression_hardening.speed_drift", 0, .12)
            _num(hardening.get("position_drift", .0045), f"{subject}.waveguide.expression_hardening.position_drift", 0, .03)
            _num(hardening.get("event_variation", .018), f"{subject}.waveguide.expression_hardening.event_variation", 0, .08)
            _num(hardening.get("attack_time_variation", .18), f"{subject}.waveguide.expression_hardening.attack_time_variation", 0, .5)
            _num(hardening.get("attack_window_s", .038), f"{subject}.waveguide.expression_hardening.attack_window_s", .002, .15)
            _num(hardening.get("attack_pressure_overshoot", .045), f"{subject}.waveguide.expression_hardening.attack_pressure_overshoot", 0, .2)
            _num(hardening.get("attack_noise_boost", .45), f"{subject}.waveguide.expression_hardening.attack_noise_boost", 0, 3)
            _num(hardening.get("bow_change_window_s", .032), f"{subject}.waveguide.expression_hardening.bow_change_window_s", .002, .15)
            _num(hardening.get("bow_change_pressure_dip", .035), f"{subject}.waveguide.expression_hardening.bow_change_pressure_dip", 0, .2)
            _num(hardening.get("bow_change_noise_boost", .35), f"{subject}.waveguide.expression_hardening.bow_change_noise_boost", 0, 3)
            _num(hardening.get("vibrato_excitation_coupling", .024), f"{subject}.waveguide.expression_hardening.vibrato_excitation_coupling", 0, .15)
            _num(hardening.get("vibrato_pressure_coupling", .010), f"{subject}.waveguide.expression_hardening.vibrato_pressure_coupling", 0, .08)

        realism = g.get("realism_hardening", {})
        if realism and not isinstance(realism, dict):
            raise InstrumentEngineValidationError(f"{subject}: realism_hardening must be an object")
        if isinstance(realism, dict):
            if "enabled" in realism and not isinstance(realism.get("enabled"), bool):
                raise InstrumentEngineValidationError(f"{subject}: realism_hardening.enabled must be boolean")
            _num(realism.get("open_string_vibrato_scale", .08), f"{subject}.waveguide.realism_hardening.open_string_vibrato_scale", 0, 1)
            _num(realism.get("stopped_string_reflection_scale", .9965), f"{subject}.waveguide.realism_hardening.stopped_string_reflection_scale", .90, 1)
            _num(realism.get("position_shift_base_s", .010), f"{subject}.waveguide.realism_hardening.position_shift_base_s", .001, .05)
            _num(realism.get("position_shift_per_position_s", .0045), f"{subject}.waveguide.realism_hardening.position_shift_per_position_s", 0, .02)
            _num(realism.get("position_shift_max_s", .038), f"{subject}.waveguide.realism_hardening.position_shift_max_s", .005, .08)
            _num(realism.get("position_shift_pressure_dip", .055), f"{subject}.waveguide.realism_hardening.position_shift_pressure_dip", 0, .3)
            _num(realism.get("position_shift_noise_boost", .30), f"{subject}.waveguide.realism_hardening.position_shift_noise_boost", 0, 3)
            _num(realism.get("string_crossing_stopped_extra_s", .006), f"{subject}.waveguide.realism_hardening.string_crossing_stopped_extra_s", 0, .05)
            _num(realism.get("string_crossing_force_preload", .18), f"{subject}.waveguide.realism_hardening.string_crossing_force_preload", 0, .5)
            _num(realism.get("bow_retake_gap_beats", .18), f"{subject}.waveguide.realism_hardening.bow_retake_gap_beats", 0, 4)
            _num(realism.get("bow_retake_contact_s", .020), f"{subject}.waveguide.realism_hardening.bow_retake_contact_s", .002, .12)
            _num(realism.get("bow_retake_pressure_dip", .10), f"{subject}.waveguide.realism_hardening.bow_retake_pressure_dip", 0, .3)
            _num(realism.get("bow_retake_noise_boost", .55), f"{subject}.waveguide.realism_hardening.bow_retake_noise_boost", 0, 3)

        art = g.get("articulation_expansion", {})
        if art and not isinstance(art, dict):
            raise InstrumentEngineValidationError(f"{subject}: articulation_expansion must be an object")
        if isinstance(art, dict):
            if "enabled" in art and not isinstance(art.get("enabled"), bool):
                raise InstrumentEngineValidationError(f"{subject}: articulation_expansion.enabled must be boolean")
            _num(art.get("pizzicato_decay_s", 1.05), f"{subject}.waveguide.articulation_expansion.pizzicato_decay_s", .08, 3.0)
            _num(art.get("pizzicato_pluck_position", .19), f"{subject}.waveguide.articulation_expansion.pizzicato_pluck_position", .04, .48)
            _num(art.get("pizzicato_partial_rolloff", 1.28), f"{subject}.waveguide.articulation_expansion.pizzicato_partial_rolloff", .6, 3.0)
            _num(art.get("pizzicato_finger_noise_gain", .006), f"{subject}.waveguide.articulation_expansion.pizzicato_finger_noise_gain", 0, .05)
            _num(art.get("harmonic_pressure_scale", .52), f"{subject}.waveguide.articulation_expansion.harmonic_pressure_scale", .05, 1.0)
            _num(art.get("harmonic_speed_scale", .78), f"{subject}.waveguide.articulation_expansion.harmonic_speed_scale", .1, 2.0)
            _num(art.get("harmonic_vibrato_scale", .18), f"{subject}.waveguide.articulation_expansion.harmonic_vibrato_scale", 0, 1.0)
            _num(art.get("harmonic_bow_position", .085), f"{subject}.waveguide.articulation_expansion.harmonic_bow_position", .035, .45)
            _num(art.get("harmonic_low_cut_hz", 420.0), f"{subject}.waveguide.articulation_expansion.harmonic_low_cut_hz", 80, 8000)
            _num(art.get("spiccato_contact_fraction", .34), f"{subject}.waveguide.articulation_expansion.spiccato_contact_fraction", .05, .9)
            _num(art.get("spiccato_contact_min_s", .025), f"{subject}.waveguide.articulation_expansion.spiccato_contact_min_s", .005, .15)
            _num(art.get("spiccato_contact_max_s", .085), f"{subject}.waveguide.articulation_expansion.spiccato_contact_max_s", .01, .25)
            _num(art.get("spiccato_pressure_scale", .78), f"{subject}.waveguide.articulation_expansion.spiccato_pressure_scale", .05, 1.5)
            _num(art.get("spiccato_speed_scale", 1.12), f"{subject}.waveguide.articulation_expansion.spiccato_speed_scale", .1, 2.0)
            _num(art.get("spiccato_noise_boost", 1.18), f"{subject}.waveguide.articulation_expansion.spiccato_noise_boost", 0, 4.0)

        env = g.get("envelope", {})
        _num(env.get("attack_s", .055), f"{subject}.waveguide.envelope.attack_s", .002, 2)
        _num(env.get("release_s", .16), f"{subject}.waveguide.envelope.release_s", .004, 4)

        continuous = g.get("continuous", {})
        if continuous and not isinstance(continuous, dict):
            raise InstrumentEngineValidationError(f"{subject}: continuous must be an object")
        if isinstance(continuous, dict):
            _num(continuous.get("initial_attack_s", env.get("attack_s", .055)), f"{subject}.waveguide.continuous.initial_attack_s", .002, 2)
            _num(continuous.get("bow_change_s", .026), f"{subject}.waveguide.continuous.bow_change_s", .002, .12)
            _num(continuous.get("control_slew_s", .005), f"{subject}.waveguide.continuous.control_slew_s", .0005, .08)
            _num(continuous.get("pitch_transition_s", .0035), f"{subject}.waveguide.continuous.pitch_transition_s", .0001, .05)
            _num(continuous.get("state_gap_limit_s", .045), f"{subject}.waveguide.continuous.state_gap_limit_s", 0, .25)
            crossing = continuous.get("string_crossing", {})
            if crossing and not isinstance(crossing, dict):
                raise InstrumentEngineValidationError(f"{subject}: continuous.string_crossing must be an object")
            if isinstance(crossing, dict):
                _num(crossing.get("contact_overlap_s", .018), f"{subject}.waveguide.continuous.string_crossing.contact_overlap_s", .001, .12)
                _num(crossing.get("residual_decay_s", .18), f"{subject}.waveguide.continuous.string_crossing.residual_decay_s", .01, 1.0)
                _num(crossing.get("residual_bridge_mix", .34), f"{subject}.waveguide.continuous.string_crossing.residual_bridge_mix", 0, 1)
                if "adjacent_only" in crossing and not isinstance(crossing.get("adjacent_only"), bool):
                    raise InstrumentEngineValidationError(f"{subject}: continuous.string_crossing.adjacent_only must be boolean")

        body = g.get("body", {})
        modes = body.get("resonances_hz", [])
        gains = body.get("gains", [])
        qs = body.get("q", [])
        if not isinstance(modes, list) or not (1 <= len(modes) <= 20):
            raise InstrumentEngineValidationError(f"{subject}: body resonances_hz must contain 1..20 values")
        if not isinstance(gains, list) or len(gains) != len(modes):
            raise InstrumentEngineValidationError(f"{subject}: body gains must match resonances_hz")
        if not isinstance(qs, list) or len(qs) != len(modes):
            raise InstrumentEngineValidationError(f"{subject}: body q must match resonances_hz")
        for i, hz in enumerate(modes):
            _num(hz, f"{subject}.waveguide.body.resonances_hz[{i}]", 20, 19000)
            _num(gains[i], f"{subject}.waveguide.body.gains[{i}]", 0, 3)
            _num(qs[i], f"{subject}.waveguide.body.q[{i}]", .25, 40)
        _num(body.get("direct_mix", .22), f"{subject}.waveguide.body.direct_mix", 0, 1)
        _num(body.get("high_cut_hz", 4600), f"{subject}.waveguide.body.high_cut_hz", 300, 19000)
        _num(body.get("highpass_hz", 70), f"{subject}.waveguide.body.highpass_hz", 5, 400)
        feedback = body.get("bridge_feedback", {})
        if feedback and not isinstance(feedback, dict):
            raise InstrumentEngineValidationError(f"{subject}: body.bridge_feedback must be an object")
        if isinstance(feedback, dict):
            if "enabled" in feedback and not isinstance(feedback.get("enabled"), bool):
                raise InstrumentEngineValidationError(f"{subject}: body.bridge_feedback.enabled must be boolean")
            _num(feedback.get("feedback_gain", .006), f"{subject}.waveguide.body.bridge_feedback.feedback_gain", 0, .03)
            _num(feedback.get("max_feedback_velocity", .028), f"{subject}.waveguide.body.bridge_feedback.max_feedback_velocity", 0, .20)
            adm = feedback.get("admittance_gains", [0.0] * len(modes))
            if not isinstance(adm, list) or len(adm) != len(modes):
                raise InstrumentEngineValidationError(f"{subject}: body.bridge_feedback.admittance_gains must match resonances_hz")
            for i, gain in enumerate(adm):
                _num(gain, f"{subject}.waveguide.body.bridge_feedback.admittance_gains[{i}]", -3, 3)
            fitted = feedback.get("fitted_response")
            if fitted is not None:
                try:
                    validate_era_profile(fitted)
                except BridgeAdmittanceFitError as exc:
                    raise InstrumentEngineValidationError(f"{subject}: invalid fitted bridge-admittance response: {exc}") from exc

        _num(g.get("stereo_width", .09), f"{subject}.waveguide.stereo_width", 0, 1)
        _num(g.get("output_gain", .70), f"{subject}.waveguide.output_gain", 0, 3)

    def validate_ir_patch(self, subject, patch): self._validate(subject, patch)
    def validate_runtime_patch(self, subject, patch): self._validate(subject, patch)
    def validate_authoring_patch(self, role, patch): self._validate(role, patch)

    def capabilities(self):
        return EngineCapabilities(
            name=self.name,
            track_rendering=True,
            extended_tail=True,
            instrument_expression=(
                "bow_pressure", "bow_speed", "bow_position", "bow_noise_gain",
                "vibrato_rate_hz", "vibrato_depth_cents", "vibrato_onset_s",
                "attack_s", "release_s",
            ),
        )


__all__ = ["BowedWaveguideEngine", "render_bowed_waveguide_note", "render_bowed_waveguide_track"]
