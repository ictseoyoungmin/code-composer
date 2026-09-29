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
from scipy.signal import lfilter


STATE_MODEL = "ag08_reduced_order_state_v1"

# Conventional steel-string tuning, numbered in guitarist order: string 1 is
# high E and string 6 is low E. These are generic project-authored instrument
# coordinates, not measurements from a named guitar.
_OPEN_STRING_MIDI = np.asarray([64, 59, 55, 50, 45, 40], dtype=np.int16)


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



def _string_resonance_midi(state: AcousticGuitarState, idx: int) -> int:
    """Current resonant fundamental for a physical string.

    Untouched strings are open. Once an authored/sympathetic state establishes a
    fret, that fret remains the compact resonant-length proxy until a later
    authored event changes it.
    """
    fret = int(state.active_fret[int(idx)])
    return int(_OPEN_STRING_MIDI[int(idx)] + max(0, fret))


def _sympathetic_mode_candidates(
    source_midi: int,
    target_midi: int,
    sr: int,
    graph: dict,
):
    """Return target modes that are spectrally compatible with the source string.

    Compatibility is computed from near-coincident partial frequencies. It does
    not create a pitch event: the result only parameterizes a passive resonant
    projection driven by the already-existing source bridge force.
    """
    from ...core.theory import midi_to_hz

    source_f0 = float(midi_to_hz(int(source_midi)))
    target_f0 = float(midi_to_hz(int(target_midi)))
    inharmonicity = max(0.0, float(graph.get("string_inharmonicity", 0.000035)))
    nyquist = 0.47 * float(sr)
    sigma_cents = 18.0
    modes = []

    for target_h in range(1, 7):
        target_freq = target_f0 * target_h * math.sqrt(
            1.0 + inharmonicity * target_h * target_h
        )
        if target_freq >= nyquist:
            break

        best_weight = 0.0
        for source_h in range(1, 9):
            source_freq = source_f0 * source_h * math.sqrt(
                1.0 + inharmonicity * source_h * source_h
            )
            if source_freq >= nyquist:
                break
            cents = 1200.0 * math.log2(target_freq / source_freq)
            closeness = math.exp(-0.5 * (cents / sigma_cents) ** 2)
            weight = closeness / math.sqrt(float(source_h * target_h))
            best_weight = max(best_weight, weight)

        if best_weight >= 0.035:
            modes.append((target_h, target_freq, best_weight))

    return modes


def _sympathetic_transfer_plan(
    source_midi: int,
    source_idx: int,
    state: AcousticGuitarState,
    sr: int,
    graph: dict,
    cross_string_coupling: float,
    sympathetic_gain: float,
    *,
    blocked_target_indices=(),
):
    """Allocate a passive bridge-domain energy budget to compatible strings.

    eta is an energy fraction, not an amplitude gain. The sum of all returned
    eta values is bounded by cross_string_coupling * sympathetic_gain and by 0.12.
    """
    source_idx = int(source_idx)
    blocked = {int(x) for x in blocked_target_indices}
    base_budget = min(
        0.12,
        max(0.0, min(0.98, float(cross_string_coupling)))
        * max(0.0, min(0.98, float(sympathetic_gain))),
    )
    if base_budget <= 1e-15:
        return []

    candidates = []
    for target_idx in range(6):
        if target_idx == source_idx or target_idx in blocked:
            continue
        target_midi = _string_resonance_midi(state, target_idx)
        modes = _sympathetic_mode_candidates(
            int(source_midi), target_midi, int(sr), graph
        )
        if not modes:
            continue
        score = math.sqrt(sum(float(w) * float(w) for _, _, w in modes))
        if score >= 0.05:
            candidates.append((target_idx, target_midi, score, modes))

    if not candidates:
        return []

    max_score = max(item[2] for item in candidates)
    compatibility_gate = max(0.0, min(1.0, max_score / 0.55))
    budget = base_budget * compatibility_gate
    score_sum = sum(item[2] for item in candidates)
    if budget <= 1e-15 or score_sum <= 1e-15:
        return []

    return [
        {
            "target_idx": int(target_idx),
            "target_midi": int(target_midi),
            "compatibility": float(score),
            "eta": float(budget * score / score_sum),
            "modes": tuple(modes),
        }
        for target_idx, target_midi, score, modes in candidates
    ]


def _note_bridge_drive(event: dict, duration_s: float, sr: int, patch: dict):
    """Reconstruct the accepted AG01-AG04 bridge-force source for S4 coupling."""
    from .string import render_steel_string_bridge_drive

    graph = patch.get("acoustic_guitar_graph", {})
    gate_s = max(1e-5, float(duration_s))
    tail_s = max(0.0, float(graph.get("natural_tail_s", 2.20)))
    n = max(1, int((gate_s + tail_s) * int(sr)))
    active_n = min(n, max(1, int(gate_s * int(sr))))

    perf = event.get("performance")
    mechanics = None
    right_hand = None
    left_hand = None
    if isinstance(perf, dict):
        if isinstance(perf.get("guitar_realization"), dict):
            mechanics = perf["guitar_realization"]
        if isinstance(perf.get("right_hand_realization"), dict):
            right_hand = perf["right_hand_realization"]
        if isinstance(perf.get("left_hand_realization"), dict):
            left_hand = perf["left_hand_realization"]

    bridge = render_steel_string_bridge_drive(
        int(event["midi"]),
        n,
        int(sr),
        graph,
        velocity=float(event.get("velocity", 0.8)),
        mechanics=mechanics,
        right_hand=right_hand,
        left_hand=left_hand,
    )

    post_gate_decay = max(0.015, float(graph.get("post_gate_decay_s", 0.72)))
    if isinstance(left_hand, dict):
        post_gate_decay *= max(
            0.05, min(1.5, float(left_hand.get("decay_scale", 1.0)))
        )
    if active_n < n:
        rr = np.arange(n - active_n, dtype=np.float64) / float(sr)
        bridge[active_n:] *= np.exp(-rr / post_gate_decay)
    return bridge


def _sympathetic_bridge_projection(
    source_bridge,
    modes,
    sr: int,
    graph: dict,
):
    """Project source bridge force into compatible target-string modal state."""
    x = np.asarray(source_bridge, dtype=np.float64)
    if x.size == 0 or not modes:
        return np.zeros_like(x)

    base_decay = max(0.05, float(graph.get("base_decay_s", 2.25)))
    damping = max(0.0, float(graph.get("frequency_damping", 0.14)))
    damping_power = max(0.2, float(graph.get("damping_power", 1.30)))
    out = np.zeros_like(x)

    for harmonic, freq_hz, weight in modes:
        tau_s = (
            0.62
            * base_decay
            / (1.0 + damping * ((int(harmonic) - 1) ** damping_power))
        )
        tau_s = max(0.08, min(2.5, tau_s))
        radius = math.exp(-1.0 / max(1.0, tau_s * float(sr)))
        theta = 2.0 * math.pi * float(freq_hz) / float(sr)
        response = lfilter(
            [1.0 - radius],
            [1.0, -2.0 * radius * math.cos(theta), radius * radius],
            x,
        )
        out += response * float(weight)

    return out


def _radiate_sympathetic_bridge(bridge, target_midi: int, sr: int, patch: dict):
    """Radiate target-string bridge state through the same accepted guitar body."""
    from .body import radiate_acoustic_guitar_body

    graph = patch.get("acoustic_guitar_graph", {})
    stereo = radiate_acoustic_guitar_body(bridge, int(sr), graph)
    radiation_keytrack = float(graph.get("radiation_keytrack", 1.10))
    radiation_gain = 2.0 ** (
        radiation_keytrack * (int(target_midi) - 52) / 12.0
    )
    stereo *= radiation_gain
    stereo *= max(0.0, float(graph.get("output_gain", 0.82)))

    fade_n = min(
        len(stereo),
        max(1, int(float(graph.get("end_fade_s", 0.035)) * int(sr))),
    )
    if fade_n > 0:
        stereo[-fade_n:] *= np.linspace(1.0, 0.0, fade_n, endpoint=True)[:, None]
    return stereo


def _cross_string_sympathetic_transfer(
    event: dict,
    source_stereo,
    source_idx: int,
    state: AcousticGuitarState,
    sr: int,
    patch: dict,
    duration_s: float,
    cross_string_coupling: float,
    sympathetic_gain: float,
    *,
    blocked_target_indices=(),
):
    """Energy-bounded S4 source-string -> bridge -> target-string transfer."""
    graph = patch.get("acoustic_guitar_graph", {})
    plan = _sympathetic_transfer_plan(
        int(event["midi"]),
        int(source_idx),
        state,
        int(sr),
        graph,
        cross_string_coupling,
        sympathetic_gain,
        blocked_target_indices=blocked_target_indices,
    )
    if not plan:
        return source_stereo, [], 0.0

    source_bridge = _note_bridge_drive(event, duration_s, int(sr), patch)
    source_norm = float(np.linalg.norm(source_bridge))
    if source_norm <= 1e-15:
        return source_stereo, [], 0.0

    transfers = []
    realized_eta = 0.0
    for item in plan:
        projected = _sympathetic_bridge_projection(
            source_bridge, item["modes"], int(sr), graph
        )
        projected_norm = float(np.linalg.norm(projected))
        if projected_norm <= 1e-15:
            continue

        eta = max(0.0, min(0.12, float(item["eta"])))
        # Normalize the resonant projection in the bridge domain, then allocate
        # sqrt(eta) amplitude so its quadratic energy is eta of the source.
        projected *= (source_norm / projected_norm) * math.sqrt(eta)
        sympathetic = _radiate_sympathetic_bridge(
            projected, int(item["target_midi"]), int(sr), patch
        )
        transfers.append((int(item["target_idx"]), sympathetic, eta))
        realized_eta += eta

    realized_eta = min(0.12, max(0.0, realized_eta))
    source_keep = math.sqrt(max(0.0, 1.0 - realized_eta))
    return np.asarray(source_stereo) * source_keep, transfers, realized_eta


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
    cross_string_coupling: float,
    sympathetic_gain: float,
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
        group_string_indices = {int(x) - 1 for x in group_strings}

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

                if (
                    cross_string_coupling > 1e-15
                    and sympathetic_gain > 1e-15
                ):
                    stereo, transfers, transfer_fraction = (
                        _cross_string_sympathetic_transfer(
                            ev,
                            stereo,
                            idx,
                            state,
                            int(sr),
                            patch,
                            duration_s,
                            cross_string_coupling,
                            sympathetic_gain,
                            blocked_target_indices=group_string_indices,
                        )
                    )
                    for target_idx, sympathetic, eta in transfers:
                        target_end = min(int(n), start + len(sympathetic))
                        if target_end <= start:
                            continue
                        buffers[target_idx][start:target_end] += sympathetic[
                            : target_end - start
                        ]
                        probe_n = min(
                            target_end - start, max(8, int(0.012 * int(sr)))
                        )
                        mono_sym = 0.5 * (
                            sympathetic[:probe_n, 0]
                            + sympathetic[:probe_n, 1]
                        )
                        sym_rms = float(
                            math.sqrt(float(np.mean(mono_sym * mono_sym)) + 1e-18)
                        )
                        state.string_energy[target_idx] = max(
                            float(state.string_energy[target_idx]), sym_rms
                        )
                        if len(mono_sym):
                            state.string_phase_proxy[target_idx] = float(
                                mono_sym[-1]
                            )
                        if int(state.active_fret[target_idx]) < 0:
                            state.active_fret[target_idx] = 0
                    if len(state.bridge_state) > 1:
                        state.bridge_state[1] = float(transfer_fraction)

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
    S4: bounded bridge-mediated sympathetic transfer between physical strings.
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

    cross_string_coupling = max(
        0.0, min(0.98, float(cfg.get("cross_string_coupling", 0.0)))
    )
    sympathetic_gain = max(
        0.0, min(0.98, float(cfg.get("sympathetic_gain", 0.0)))
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
            cross_string_coupling=cross_string_coupling,
            sympathetic_gain=sympathetic_gain,
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
