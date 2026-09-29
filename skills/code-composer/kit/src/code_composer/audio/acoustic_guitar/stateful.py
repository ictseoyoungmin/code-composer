"""AG08 reduced-order persistent acoustic-guitar state.

S1 establishes the state contract and a strict zero-coupling bypass.
S2 activates same-string continuity: one physical string cannot keep multiple
independent tails after it is re-attacked.

S3 adds shared bridge/body memory without inventing a second body resonator. The
actual accepted AG01/AG07 rendered residual waveform is the persistent body state:
later notes and AG07 actions enter the same track-owned state, while a bounded,
continuous loading curve models weak nonlinear re-excitation/contact interaction.
Cross-string sympathetic coupling remains blocked until S4.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
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
    """Create deterministic zero-energy AG08 state."""
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


def _event_type(event: dict) -> str:
    if "event_type" in event:
        return str(event["event_type"])
    if "type" in event:
        return str(event["type"])
    # Canonical pitched render-IR events intentionally omit an event_type tag;
    # presence of MIDI identifies the normal note path in render.py.
    if "midi" in event:
        return "note"
    return ""


def _resolved_string_fret(event: dict):
    perf = event.get("performance")
    if not isinstance(perf, dict):
        return None
    realization = perf.get("guitar_realization")
    if not isinstance(realization, dict):
        return None
    try:
        string_no = int(realization["string"])
        fret = int(realization["fret"])
    except (KeyError, TypeError, ValueError):
        return None
    if not 1 <= string_no <= 6 or not 0 <= fret <= 20:
        return None
    return string_no, fret


def _same_string_carry_tau_s(memory: float, residual_rms: float) -> float:
    """Bounded residual carry time for one re-attacked physical string.

    The previous waveform itself is the state carrier; this function only controls
    how quickly that already-existing state is damped after the next authored attack.
    No new oscillator, pitch, or hidden note is synthesized.
    """
    memory = max(0.0, min(0.98, float(memory)))
    residual_weight = max(0.0, min(1.0, float(residual_rms) / 0.08))
    return 0.006 + (0.110 * memory * (0.65 + 0.35 * residual_weight))


def _render_same_string_continuity(
    events,
    n: int,
    sr: int,
    patch: dict,
    beat_s: float,
    state: AcousticGuitarState,
    memory: float,
):
    """Render note-only S2 tracks with one persistent buffer per physical string.

    Before a new attack on a string, the prior contribution on that same string is
    continuous at the exact boundary (envelope starts at 1.0) and then decays with
    a bounded carry time. This prevents impossible indefinite overlap of independent
    same-string tails while retaining the accepted AG01-AG07 note renderer.
    """
    from .render import render_acoustic_guitar_note

    # S2 intentionally owns note-only, neutral-pan tracks. AG07 instrument actions
    # stay on the canonical event path until shared body/action state is introduced.
    for ev in events:
        if _event_type(ev) != "note":
            return None
        if abs(float(ev.get("pan", 0.0))) > 1e-12:
            return None
        if _resolved_string_fret(ev) is None:
            return None

    string_buffers = [
        np.zeros((int(n), 2), dtype=np.float64) for _ in range(6)
    ]
    last_start = np.full(6, -1, dtype=np.int64)

    for ev in events:
        start = int(float(ev["start_beat"]) * float(beat_s) * int(sr))
        if start < 0 or start >= int(n):
            continue

        resolved = _resolved_string_fret(ev)
        if resolved is None:
            return None
        string_no, fret = resolved
        idx = string_no - 1

        # Two simultaneous authored notes on one physical string cannot be resolved
        # safely by S2. Preserve AG07 behavior instead of inventing an ordering.
        if int(last_start[idx]) == start:
            return None

        target = string_buffers[idx]
        had_prior_state = int(state.active_fret[idx]) >= 0
        if had_prior_state:
            probe_n = min(int(n) - start, max(8, int(0.012 * int(sr))))
            if probe_n > 0:
                residual = target[start:start + probe_n]
                mono = 0.5 * (residual[:, 0] + residual[:, 1])
                residual_rms = float(
                    math.sqrt(float(np.mean(mono * mono)) + 1e-18)
                )
                state.string_energy[idx] = residual_rms
                state.string_phase_proxy[idx] = float(mono[0]) if len(mono) else 0.0

                tau_s = _same_string_carry_tau_s(memory, residual_rms)
                remain = int(n) - start
                t = np.arange(remain, dtype=np.float64) / float(sr)
                carry = np.exp(-t / max(1.0 / float(sr), tau_s))
                target[start:] *= carry[:, None]

        duration_s = float(ev["duration_beats"]) * float(beat_s)
        stereo = render_acoustic_guitar_note(
            int(ev["midi"]),
            duration_s,
            int(sr),
            patch,
            velocity=float(ev.get("velocity", 0.8)),
            performance=ev.get("performance"),
        )
        end = min(int(n), start + len(stereo))
        if end > start:
            target[start:end] += stereo[:end - start]
            attack_n = min(end - start, max(8, int(0.012 * int(sr))))
            attack = stereo[:attack_n]
            mono_attack = 0.5 * (attack[:, 0] + attack[:, 1])
            attack_rms = float(
                math.sqrt(float(np.mean(mono_attack * mono_attack)) + 1e-18)
            )
            state.string_energy[idx] = max(
                float(state.string_energy[idx]), attack_rms
            )
            if len(mono_attack):
                state.string_phase_proxy[idx] = float(mono_attack[-1])

        state.active_fret[idx] = int(fret)
        state.sample_index = max(int(state.sample_index), int(end))
        last_start[idx] = int(start)

    buf = np.zeros((int(n), 2), dtype=np.float64)
    for string_buf in string_buffers:
        buf += string_buf
    return buf


def _shared_body_loading_curve(memory: float, residual_rms: float, sr: int, remain: int):
    """Continuous bounded loading of an already-ringing shared guitar body.

    A linear resonator would simply superpose the old and new excitations. S3 keeps
    that behavior mostly intact and introduces only weak loading: the curve starts
    exactly at 1.0 at the authored event boundary and approaches a high retain
    factor. No new mode or pitch is synthesized.
    """
    memory = max(0.0, min(0.98, float(memory)))
    residual_weight = max(0.0, min(1.0, float(residual_rms) / 0.10))
    retain = 0.72 + 0.22 * memory + 0.03 * residual_weight
    retain = max(0.72, min(0.97, retain))
    tau_s = 0.018 + 0.120 * memory
    t = np.arange(int(remain), dtype=np.float64) / float(sr)
    return retain + (1.0 - retain) * np.exp(
        -t / max(1.0 / float(sr), tau_s)
    )


def _shared_residual_rms(buffers, start: int, sr: int) -> tuple[float, float]:
    probe_n = min(
        max(0, len(buffers[0]) - int(start)),
        max(8, int(0.012 * int(sr))),
    )
    if probe_n <= 0:
        return 0.0, 0.0
    residual = np.zeros((probe_n, 2), dtype=np.float64)
    for component in buffers:
        residual += component[start:start + probe_n]
    mono = 0.5 * (residual[:, 0] + residual[:, 1])
    rms = float(math.sqrt(float(np.mean(mono * mono)) + 1e-18))
    first = float(mono[0]) if len(mono) else 0.0
    return rms, first


def _render_shared_body_memory(
    events,
    n: int,
    sr: int,
    patch: dict,
    beat_s: float,
    state: AcousticGuitarState,
    *,
    same_string_memory: float,
    bridge_memory: float,
    action_body_memory: float,
):
    """S3 mixed note/action track renderer using actual residual audio as state.

    Six note component buffers retain physical-string identity for S2. A seventh
    component holds AG07 actions. At each new event onset, all already-ringing
    components participate in one shared body-loading transition. New events then
    excite that same state. This preserves accepted event renderers and AG07 seeds.
    """
    from .render import render_acoustic_guitar_note
    from .percussion import render_acoustic_guitar_action

    prepared = []
    for ordinal, ev in enumerate(events or []):
        kind = _event_type(ev)
        if kind not in {"note", "instrument_action"}:
            return None
        if abs(float(ev.get("pan", 0.0))) > 1e-12:
            return None
        if kind == "note" and _resolved_string_fret(ev) is None:
            return None
        if kind == "instrument_action" and "_ag_action_seed" not in ev:
            # Direct callers that do not pass render-local AG07 identity must use
            # the canonical event renderer rather than silently changing noise.
            return None
        start = int(float(ev["start_beat"]) * float(beat_s) * int(sr))
        if 0 <= start < int(n):
            prepared.append((start, ordinal, ev))

    if not prepared:
        return np.zeros((int(n), 2), dtype=np.float64)

    prepared.sort(key=lambda item: (item[0], item[1]))
    buffers = [np.zeros((int(n), 2), dtype=np.float64) for _ in range(7)]
    last_start = np.full(6, -1, dtype=np.int64)
    any_prior = False

    pos = 0
    while pos < len(prepared):
        start = prepared[pos][0]
        group = []
        while pos < len(prepared) and prepared[pos][0] == start:
            group.append(prepared[pos][2])
            pos += 1

        # One physical string cannot host two distinct simultaneous authored
        # notes in S3. Preserve the pre-AG08 path rather than inventing priority.
        group_strings = []
        for ev in group:
            if _event_type(ev) == "note":
                resolved = _resolved_string_fret(ev)
                if resolved is None:
                    return None
                group_strings.append(resolved[0])
        if len(set(group_strings)) != len(group_strings):
            return None

        has_note = any(_event_type(ev) == "note" for ev in group)
        has_action = any(_event_type(ev) == "instrument_action" for ev in group)
        body_memory = max(
            float(bridge_memory) if has_note else 0.0,
            float(action_body_memory) if has_action else 0.0,
        )

        if any_prior and body_memory > 1e-15:
            residual_rms, residual_first = _shared_residual_rms(buffers, start, sr)
            state.body_state[0] = residual_rms
            if len(state.body_state) > 1:
                state.body_state[1] = residual_first
            if residual_rms > 1e-12:
                remain = int(n) - start
                loading = _shared_body_loading_curve(
                    body_memory, residual_rms, sr, remain
                )
                for component in buffers:
                    component[start:] *= loading[:, None]

        for ev in group:
            kind = _event_type(ev)
            duration_s = float(ev["duration_beats"]) * float(beat_s)

            if kind == "note":
                string_no, fret = _resolved_string_fret(ev)
                idx = string_no - 1
                target = buffers[idx]

                if int(state.active_fret[idx]) >= 0 and same_string_memory > 1e-15:
                    probe_n = min(
                        int(n) - start, max(8, int(0.012 * int(sr)))
                    )
                    if probe_n > 0:
                        residual = target[start:start + probe_n]
                        mono = 0.5 * (residual[:, 0] + residual[:, 1])
                        residual_rms = float(
                            math.sqrt(float(np.mean(mono * mono)) + 1e-18)
                        )
                        state.string_energy[idx] = residual_rms
                        state.string_phase_proxy[idx] = (
                            float(mono[0]) if len(mono) else 0.0
                        )
                        if residual_rms > 1e-12:
                            tau_s = _same_string_carry_tau_s(
                                same_string_memory, residual_rms
                            )
                            remain = int(n) - start
                            t = np.arange(remain, dtype=np.float64) / float(sr)
                            carry = np.exp(
                                -t / max(1.0 / float(sr), tau_s)
                            )
                            target[start:] *= carry[:, None]

                stereo = render_acoustic_guitar_note(
                    int(ev["midi"]),
                    duration_s,
                    int(sr),
                    patch,
                    velocity=float(ev.get("velocity", 0.8)),
                    performance=ev.get("performance"),
                )
                state.active_fret[idx] = int(fret)
                last_start[idx] = int(start)
            else:
                target = buffers[6]
                stereo = render_acoustic_guitar_action(
                    str(ev["action"]),
                    duration_s,
                    int(sr),
                    patch,
                    parameters=ev.get("parameters") or {},
                    seed=int(ev["_ag_action_seed"]),
                )

            end = min(int(n), start + len(stereo))
            if end > start:
                target[start:end] += stereo[:end - start]
                attack_n = min(end - start, max(8, int(0.012 * int(sr))))
                attack = stereo[:attack_n]
                mono_attack = 0.5 * (attack[:, 0] + attack[:, 1])
                attack_rms = float(
                    math.sqrt(float(np.mean(mono_attack * mono_attack)) + 1e-18)
                )
                state.bridge_state[0] = attack_rms
                if len(state.bridge_state) > 1 and len(mono_attack):
                    state.bridge_state[1] = float(mono_attack[-1])
                if kind == "note":
                    state.string_energy[idx] = max(
                        float(state.string_energy[idx]), attack_rms
                    )
                    if len(mono_attack):
                        state.string_phase_proxy[idx] = float(mono_attack[-1])
                state.sample_index = max(int(state.sample_index), int(end))

        any_prior = True

    out = np.zeros((int(n), 2), dtype=np.float64)
    for component in buffers:
        out += component
    return out


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

    S1: all gains zero -> exact AG07 event renderer.
    S2: only same_string_memory -> note-only physical-string continuity.
    S3: bridge_memory/action_body_memory -> mixed note/action shared body state.
    S4+ cross-string/sympathetic coupling remains hard-blocked.
    """
    graph = patch.get("acoustic_guitar_graph", {}) if isinstance(patch, dict) else {}
    if not stateful_enabled(graph):
        return None

    state = initialize_acoustic_guitar_state(sr, graph)
    if state.model != STATE_MODEL or state.sample_rate != int(sr):
        raise ValueError("invalid AG08 acoustic-guitar state initialization")

    if coupling_is_zero(graph):
        return None

    cfg = stateful_config(graph)
    same_string_memory = float(cfg.get("same_string_memory", 0.0))
    bridge_memory = float(cfg.get("bridge_memory", 0.0))
    action_body_memory = float(cfg.get("action_body_memory", 0.0))

    unsupported = {
        key: float(cfg.get(key, 0.0))
        for key in ("cross_string_coupling", "sympathetic_gain")
        if abs(float(cfg.get(key, 0.0))) > 1e-15
    }
    if unsupported:
        raise NotImplementedError(
            "AG08 coupling beyond S3 shared body memory is not active: "
            + ", ".join(sorted(unsupported))
        )

    if bridge_memory > 1e-15 or action_body_memory > 1e-15:
        return _render_shared_body_memory(
            events,
            n,
            sr,
            patch,
            beat_s,
            state,
            same_string_memory=same_string_memory,
            bridge_memory=bridge_memory,
            action_body_memory=action_body_memory,
        )

    if same_string_memory <= 1e-15:
        return None

    return _render_same_string_continuity(
        events,
        n,
        sr,
        patch,
        beat_s,
        state,
        same_string_memory,
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
