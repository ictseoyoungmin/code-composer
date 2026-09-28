"""AG03 right-hand excitation authority for acoustic guitar.

Authored right-hand mechanics remain separate from AG02 string/fret authority.
No right-hand payload means no right-hand realization is attached, preserving the
AG02 canonical render path sample-exactly.
"""
from __future__ import annotations

from copy import deepcopy
import math


class GuitarRightHandError(ValueError):
    pass


RIGHT_HAND_METHODS = ("finger", "thumb", "nail", "pick")


def _finite_number(value, name: str, lo: float, hi: float) -> float:
    if isinstance(value, bool):
        raise GuitarRightHandError(f"{name} must be numeric")
    try:
        out = float(value)
    except Exception as exc:
        raise GuitarRightHandError(f"{name} must be numeric") from exc
    if not math.isfinite(out):
        raise GuitarRightHandError(f"{name} must be finite")
    if not lo <= out <= hi:
        raise GuitarRightHandError(f"{name} outside [{lo},{hi}]")
    return out


def resolve_right_hand(payload: dict, graph: dict) -> dict:
    if not isinstance(payload, dict) or not payload:
        raise GuitarRightHandError("right_hand must be a non-empty object")

    unknown = set(payload) - {
        "method",
        "pluck_position",
        "attack_angle_deg",
        "strength",
    }
    if unknown:
        raise GuitarRightHandError(
            f"unsupported AG03 right_hand field(s): {sorted(unknown)}"
        )

    method = payload.get("method")
    if method is not None:
        method = str(method)
        if method not in RIGHT_HAND_METHODS:
            raise GuitarRightHandError(
                f"right_hand.method must be one of {list(RIGHT_HAND_METHODS)}"
            )
    else:
        method = "neutral"

    base_pluck = float(graph.get("pluck_position", 0.14))
    pluck_position = (
        _finite_number(payload["pluck_position"], "right_hand.pluck_position", 0.03, 0.49)
        if "pluck_position" in payload
        else base_pluck
    )
    attack_angle = (
        _finite_number(payload["attack_angle_deg"], "right_hand.attack_angle_deg", 0.0, 90.0)
        if "attack_angle_deg" in payload
        else 45.0
    )
    strength = (
        _finite_number(payload["strength"], "right_hand.strength", 0.0, 1.0)
        if "strength" in payload
        else 0.5
    )

    return {
        "method": method,
        "method_authored": "method" in payload,
        "pluck_position": pluck_position,
        "pluck_position_authored": "pluck_position" in payload,
        "attack_angle_deg": attack_angle,
        "attack_angle_authored": "attack_angle_deg" in payload,
        "strength": strength,
        "strength_authored": "strength" in payload,
        "authority": "authored_right_hand",
    }


def realize_guitar_right_hand(ir: dict, track_id: str, plan_instrument: dict) -> dict:
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
        raise GuitarRightHandError(f"track not found: {track_id}")

    right_hand_events = []
    for event_index, ev in enumerate(track.get("events", [])):
        if "midi" not in ev:
            continue
        perf = deepcopy(ev.get("performance") or {})
        instrument = perf.get("instrument") if isinstance(perf.get("instrument"), dict) else {}
        authored = instrument.get("right_hand")
        if authored is None:
            continue
        realization = resolve_right_hand(authored, graph)
        perf["right_hand_realization"] = deepcopy(realization)
        ev["performance"] = perf
        right_hand_events.append({
            "event_index": event_index,
            "midi": int(ev["midi"]),
            "start_beat": float(ev["start_beat"]),
            "duration_beats": float(ev["duration_beats"]),
            "authored": deepcopy(authored),
            "resolved": deepcopy(realization),
        })

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
    track_report.setdefault("scope", {})["right_hand_excitation"] = bool(right_hand_events)
    track_report["right_hand_event_count"] = len(right_hand_events)
    track_report["right_hand_events"] = right_hand_events
    out["guitar_performance_report"] = report
    return out


__all__ = [
    "GuitarRightHandError",
    "RIGHT_HAND_METHODS",
    "resolve_right_hand",
    "realize_guitar_right_hand",
]
