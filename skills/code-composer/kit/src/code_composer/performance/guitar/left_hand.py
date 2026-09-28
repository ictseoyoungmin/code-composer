"""AG04 left-hand articulation and damping for acoustic guitar.

AG04 never rewrites authored pitch/timing. Transition techniques consume the
already-resolved AG02 same-string fingering path and annotate the destination
note with physical transition intent. No left-hand payload attaches no AG04
realization, preserving AG03 sample-exactly.
"""
from __future__ import annotations

from copy import deepcopy
import math


class GuitarLeftHandError(ValueError):
    pass


LEFT_HAND_TECHNIQUES = (
    "palm_mute",
    "fretting_mute",
    "dead_note",
    "slide",
    "hammer_on",
    "pull_off",
    "natural_harmonic",
)
_TRANSITIONS = {"slide", "hammer_on", "pull_off"}


def _finite_number(value, name: str, lo: float, hi: float) -> float:
    if isinstance(value, bool):
        raise GuitarLeftHandError(f"{name} must be numeric")
    try:
        out = float(value)
    except Exception as exc:
        raise GuitarLeftHandError(f"{name} must be numeric") from exc
    if not math.isfinite(out):
        raise GuitarLeftHandError(f"{name} must be finite")
    if not lo <= out <= hi:
        raise GuitarLeftHandError(f"{name} outside [{lo},{hi}]")
    return out


def _integer(value, name: str, lo: int, hi: int) -> int:
    if isinstance(value, bool):
        raise GuitarLeftHandError(f"{name} must be integer")
    if isinstance(value, int):
        out = value
    elif isinstance(value, float) and math.isfinite(value) and value.is_integer():
        out = int(value)
    else:
        raise GuitarLeftHandError(f"{name} must be integer")
    if not lo <= out <= hi:
        raise GuitarLeftHandError(f"{name} outside [{lo},{hi}]")
    return out


def resolve_left_hand(
    payload: dict,
    *,
    current_event: dict,
    previous_event: dict | None,
) -> dict:
    if not isinstance(payload, dict) or not payload:
        raise GuitarLeftHandError("left_hand must be a non-empty object")

    unknown = set(payload) - {
        "technique",
        "amount",
        "transition_ms",
        "harmonic_order",
    }
    if unknown:
        raise GuitarLeftHandError(
            f"unsupported AG04 left_hand field(s): {sorted(unknown)}"
        )

    technique = str(payload.get("technique", ""))
    if technique not in LEFT_HAND_TECHNIQUES:
        raise GuitarLeftHandError(
            f"left_hand.technique must be one of {list(LEFT_HAND_TECHNIQUES)}"
        )

    amount = (
        _finite_number(payload["amount"], "left_hand.amount", 0.0, 1.0)
        if "amount" in payload
        else 0.72
    )
    harmonic_order = (
        _integer(payload["harmonic_order"], "left_hand.harmonic_order", 2, 5)
        if "harmonic_order" in payload
        else 2
    )

    current_perf = current_event.get("performance") or {}
    current_pos = current_perf.get("guitar_realization")
    if not isinstance(current_pos, dict):
        raise GuitarLeftHandError("AG04 requires resolved AG02 guitar fingering")

    out = {
        "technique": technique,
        "amount": amount,
        "authority": "authored_left_hand",
        "transition": False,
    }

    if technique == "natural_harmonic":
        out.update({
            "harmonic_order": harmonic_order,
            "tonal_scale": 0.88,
            "excitation_scale": 0.72,
            "decay_scale": 0.86,
            "damping_scale": 0.82,
        })
        return out

    if technique == "palm_mute":
        out.update({
            "decay_scale": 1.0 - 0.62 * amount,
            "damping_scale": 1.0 + 2.4 * amount,
            "tonal_scale": 1.0 - 0.28 * amount,
            "excitation_scale": 1.0,
        })
        return out

    if technique == "fretting_mute":
        out.update({
            "decay_scale": 1.0 - 0.78 * amount,
            "damping_scale": 1.0 + 3.6 * amount,
            "tonal_scale": 1.0 - 0.62 * amount,
            "excitation_scale": 0.82,
        })
        return out

    if technique == "dead_note":
        out.update({
            "decay_scale": 0.12,
            "damping_scale": 5.5,
            "tonal_scale": 0.12,
            "excitation_scale": 0.48,
            "contact_noise_scale": 2.4,
        })
        return out

    # Transition techniques require a preceding pitched note on the same resolved string.
    if previous_event is None or "midi" not in previous_event:
        raise GuitarLeftHandError(
            f"{technique} requires a preceding pitched guitar note"
        )
    prev_perf = previous_event.get("performance") or {}
    prev_pos = prev_perf.get("guitar_realization")
    if not isinstance(prev_pos, dict):
        raise GuitarLeftHandError(
            f"{technique} requires preceding AG02 fingering realization"
        )
    if int(prev_pos["string"]) != int(current_pos["string"]):
        raise GuitarLeftHandError(
            f"{technique} requires same-string transition; "
            f"got string {prev_pos['string']} -> {current_pos['string']}"
        )

    prev_midi = int(previous_event["midi"])
    curr_midi = int(current_event["midi"])
    if technique == "hammer_on" and curr_midi <= prev_midi:
        raise GuitarLeftHandError("hammer_on destination pitch must be above source")
    if technique == "pull_off" and curr_midi >= prev_midi:
        raise GuitarLeftHandError("pull_off destination pitch must be below source")

    default_ms = {
        "slide": 72.0,
        "hammer_on": 11.0,
        "pull_off": 14.0,
    }[technique]
    transition_ms = (
        _finite_number(payload["transition_ms"], "left_hand.transition_ms", 4.0, 240.0)
        if "transition_ms" in payload
        else default_ms
    )

    # A left-hand-only destination cannot simultaneously claim a new authored
    # right-hand strike. This is the central no-fake-pick invariant.
    instrument = current_perf.get("instrument") if isinstance(current_perf.get("instrument"), dict) else {}
    if instrument.get("right_hand") is not None:
        raise GuitarLeftHandError(
            f"{technique} destination must not author a new right_hand strike"
        )

    excitation_scale = {
        "slide": 0.10,
        "hammer_on": 0.035,
        "pull_off": 0.055,
    }[technique]
    contact_gain = {
        "slide": 0.08,
        "hammer_on": 0.22,
        "pull_off": 0.16,
    }[technique]

    out.update({
        "transition": True,
        "from_midi": prev_midi,
        "to_midi": curr_midi,
        "string": int(current_pos["string"]),
        "from_fret": int(prev_pos["fret"]),
        "to_fret": int(current_pos["fret"]),
        "transition_ms": transition_ms,
        "excitation_scale": excitation_scale,
        "fret_contact_gain": contact_gain,
        "decay_scale": 0.98,
        "damping_scale": 1.02,
        "tonal_scale": 1.0,
    })
    return out


def realize_guitar_left_hand(ir: dict, track_id: str, plan_instrument: dict) -> dict:
    out = deepcopy(ir)
    plan_patch = plan_instrument.get("patch", {}) if isinstance(plan_instrument, dict) else {}
    graph = plan_patch.get("acoustic_guitar_graph", {}) if isinstance(plan_patch, dict) else {}
    if not (
        graph.get("physical_model") == "ag01_modal_bridge_body_v2"
        and graph.get("string_source_model") == "triangular_pluck_bridge_force_v2"
    ):
        return out

    track = next((t for t in out.get("tracks", []) if t.get("id") == track_id), None)
    if track is None:
        raise GuitarLeftHandError(f"track not found: {track_id}")

    events = track.get("events", [])
    left_events = []
    previous_pitched = None
    for event_index, ev in enumerate(events):
        if "midi" not in ev:
            continue
        perf = deepcopy(ev.get("performance") or {})
        instrument = perf.get("instrument") if isinstance(perf.get("instrument"), dict) else {}
        authored = instrument.get("left_hand")
        if authored is not None:
            realization = resolve_left_hand(
                authored,
                current_event=ev,
                previous_event=previous_pitched,
            )
            perf["left_hand_realization"] = deepcopy(realization)
            ev["performance"] = perf
            left_events.append({
                "event_index": event_index,
                "midi": int(ev["midi"]),
                "start_beat": float(ev["start_beat"]),
                "duration_beats": float(ev["duration_beats"]),
                "authored": deepcopy(authored),
                "resolved": deepcopy(realization),
            })
        previous_pitched = ev

    report = deepcopy(out.get("guitar_performance_report") or {
        "version": "1.0",
        "tracks": {},
    })
    track_report = report.setdefault("tracks", {}).setdefault(track_id, {
        "instrument_id": track.get("instrument"),
        "event_count": 0,
        "events": [],
        "scope": {},
    })
    track_report.setdefault("scope", {})["left_hand_articulation"] = bool(left_events)
    track_report["left_hand_event_count"] = len(left_events)
    track_report["left_hand_events"] = left_events
    out["guitar_performance_report"] = report
    return out


__all__ = [
    "GuitarLeftHandError",
    "LEFT_HAND_TECHNIQUES",
    "resolve_left_hand",
    "realize_guitar_left_hand",
]
