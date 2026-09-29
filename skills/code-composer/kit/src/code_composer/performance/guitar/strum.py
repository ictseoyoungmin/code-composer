"""AG06 continuous chord-strum gesture realization.

A strum is represented as one authored gesture shared by a chord's note events.
The score keeps one nominal chord onset. AG06 derives render-local string contact
offsets and excitation from the common gesture; it does not rewrite authored
pitch, string/fret, duration, nominal onset, or velocity.
"""
from __future__ import annotations

from copy import deepcopy
import math


class GuitarStrumError(ValueError):
    pass


STRUM_DIRECTIONS = ("down", "up")
STRUM_STATES = ("sounding", "muted")
_STRUM_COMMON_FIELDS = (
    "stroke_id",
    "direction",
    "traversal_ms",
    "entry_strength",
    "acceleration",
    "pick_depth",
    "attack_angle_deg",
    "follow_through",
    "accent_position",
    "accent_amount",
    "from_string",
    "to_string",
)


def _finite(value, name: str, lo: float, hi: float) -> float:
    if isinstance(value, bool):
        raise GuitarStrumError(f"{name} must be numeric")
    try:
        out = float(value)
    except Exception as exc:
        raise GuitarStrumError(f"{name} must be numeric") from exc
    if not math.isfinite(out):
        raise GuitarStrumError(f"{name} must be finite")
    if not lo <= out <= hi:
        raise GuitarStrumError(f"{name} outside [{lo},{hi}]")
    return out


def _integer(value, name: str, lo: int, hi: int) -> int:
    if isinstance(value, bool):
        raise GuitarStrumError(f"{name} must be integer")
    if isinstance(value, int):
        out = value
    elif isinstance(value, float) and math.isfinite(value) and value.is_integer():
        out = int(value)
    else:
        raise GuitarStrumError(f"{name} must be integer")
    if not lo <= out <= hi:
        raise GuitarStrumError(f"{name} outside [{lo},{hi}]")
    return out


def _normalized_common(payload: dict) -> dict:
    stroke_id = payload.get("stroke_id")
    if not isinstance(stroke_id, str) or not stroke_id.strip():
        raise GuitarStrumError("strum.stroke_id must be a non-empty string")

    direction = str(payload.get("direction", ""))
    if direction not in STRUM_DIRECTIONS:
        raise GuitarStrumError(
            f"strum.direction must be one of {list(STRUM_DIRECTIONS)}"
        )

    from_string = _integer(payload.get("from_string"), "strum.from_string", 1, 6)
    to_string = _integer(payload.get("to_string"), "strum.to_string", 1, 6)
    if from_string == to_string:
        raise GuitarStrumError("strum traversal must span at least two strings")
    if direction == "down" and not from_string > to_string:
        raise GuitarStrumError(
            "downstroke requires from_string > to_string (low-E side toward high-E)"
        )
    if direction == "up" and not from_string < to_string:
        raise GuitarStrumError(
            "upstroke requires from_string < to_string (high-E side toward low-E)"
        )

    return {
        "stroke_id": stroke_id.strip(),
        "direction": direction,
        "traversal_ms": _finite(
            payload.get("traversal_ms", 34.0), "strum.traversal_ms", 6.0, 180.0
        ),
        "entry_strength": _finite(
            payload.get("entry_strength", 0.62), "strum.entry_strength", 0.15, 1.0
        ),
        "acceleration": _finite(
            payload.get("acceleration", 0.0), "strum.acceleration", -1.0, 1.0
        ),
        "pick_depth": _finite(
            payload.get("pick_depth", 0.55), "strum.pick_depth", 0.0, 1.0
        ),
        "attack_angle_deg": _finite(
            payload.get("attack_angle_deg", 45.0),
            "strum.attack_angle_deg",
            0.0,
            90.0,
        ),
        "follow_through": _finite(
            payload.get("follow_through", 0.70),
            "strum.follow_through",
            0.0,
            1.0,
        ),
        "accent_position": _finite(
            payload.get("accent_position", 0.50),
            "strum.accent_position",
            0.0,
            1.0,
        ),
        "accent_amount": _finite(
            payload.get("accent_amount", 0.0),
            "strum.accent_amount",
            0.0,
            0.75,
        ),
        "from_string": from_string,
        "to_string": to_string,
    }


def resolve_strum(payload: dict, *, current_event: dict) -> dict:
    if not isinstance(payload, dict) or not payload:
        raise GuitarStrumError("strum must be a non-empty object")

    unknown = set(payload) - set(_STRUM_COMMON_FIELDS) - {"state"}
    if unknown:
        raise GuitarStrumError(
            f"unsupported AG06 strum field(s): {sorted(unknown)}"
        )

    common = _normalized_common(payload)
    state = str(payload.get("state", "sounding"))
    if state not in STRUM_STATES:
        raise GuitarStrumError(
            f"strum.state must be one of {list(STRUM_STATES)}"
        )

    perf = current_event.get("performance") or {}
    fingering = perf.get("guitar_realization")
    if not isinstance(fingering, dict):
        raise GuitarStrumError("AG06 requires resolved AG02 guitar fingering")
    string_number = int(fingering["string"])
    lo = min(common["from_string"], common["to_string"])
    hi = max(common["from_string"], common["to_string"])
    if not lo <= string_number <= hi:
        raise GuitarStrumError(
            f"string {string_number} outside authored strum traversal "
            f"{common['from_string']}->{common['to_string']}"
        )

    right = perf.get("right_hand_realization")
    if not isinstance(right, dict):
        raise GuitarStrumError(
            "AG06 requires explicit AG03 right_hand on every traversed note"
        )
    method = str(right.get("method", ""))
    if method not in {"pick", "finger", "nail"}:
        raise GuitarStrumError(
            "AG06 strum requires right_hand.method pick, finger, or nail"
        )

    if state == "muted":
        left = perf.get("left_hand_realization")
        technique = str(left.get("technique", "")) if isinstance(left, dict) else ""
        if technique not in {"fretting_mute", "dead_note"}:
            raise GuitarStrumError(
                "strum.state='muted' requires AG04 fretting_mute or dead_note"
            )

    return {
        **common,
        "state": state,
        "string": string_number,
        "fret": int(fingering["fret"]),
        "right_hand_method": method,
        "authority": "authored_strum",
    }


def _traversal_strings(common: dict) -> list[int]:
    step = -1 if common["direction"] == "down" else 1
    return list(range(common["from_string"], common["to_string"] + step, step))


def _force_at(x: float, common: dict) -> float:
    """Deterministic correlated force from one continuous gesture.

    This intentionally contains no per-string RNG. String differences emerge
    from where the contact lies along one shared trajectory.
    """
    entry = float(common["entry_strength"])
    accel = float(common["acceleration"])
    depth = float(common["pick_depth"])
    angle = math.radians(float(common["attack_angle_deg"]))
    follow = float(common["follow_through"])
    traversal_ms = float(common["traversal_ms"])

    # Entry/exit are naturally a little lighter than the middle of a sweep.
    arc = 0.90 + 0.13 * math.sin(math.pi * x)

    # Authored acceleration transfers energy toward the end/start of the sweep.
    accel_shape = 1.0 + 0.20 * accel * (2.0 * x - 1.0)

    # Faster strokes carry a small late-sweep bias; slow rakes are more deliberate
    # and slightly front-loaded. Thus speed changes force distribution, not only time.
    speed_state = max(-1.0, min(1.0, (42.0 - traversal_ms) / 72.0))
    speed_shape = 1.0 + 0.10 * speed_state * (2.0 * x - 1.0)

    # Depth, angle and follow-through are shared gesture states. Their local
    # consequences change continuously across the trajectory.
    depth_shape = 1.0 + 0.10 * (depth - 0.5) * (0.35 + 0.65 * x)
    angle_shape = 1.0 + 0.045 * math.cos(angle) * (x - 0.35)
    follow_shape = 1.0 + 0.13 * follow * (x - 0.5)

    # Direction is more than reversed order: hand geometry gives a bounded
    # direction-specific load tilt.
    direction_tilt = 0.070 if common["direction"] == "down" else -0.050
    direction_shape = 1.0 + direction_tilt * (x - 0.5)

    accent_pos = float(common["accent_position"])
    accent_amt = float(common["accent_amount"])
    accent_shape = 1.0 + accent_amt * math.exp(
        -0.5 * ((x - accent_pos) / 0.16) ** 2
    )

    force = (
        entry
        * arc
        * accel_shape
        * speed_shape
        * depth_shape
        * angle_shape
        * follow_shape
        * direction_shape
        * accent_shape
    )
    return max(0.15, min(1.0, force))


def realize_guitar_strum(ir: dict, track_id: str, plan_instrument: dict) -> dict:
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
        raise GuitarStrumError(f"track not found: {track_id}")

    groups: dict[str, list[dict]] = {}
    for event_index, ev in enumerate(track.get("events", [])):
        if "midi" not in ev:
            continue
        perf = deepcopy(ev.get("performance") or {})
        instrument = perf.get("instrument") if isinstance(perf.get("instrument"), dict) else {}
        authored = instrument.get("strum")
        if authored is None:
            continue
        if instrument.get("arpeggio") is not None:
            raise GuitarStrumError(
                "AG05 arpeggio and AG06 strum cannot own the same note event"
            )

        resolved = resolve_strum(authored, current_event=ev)
        item = {
            "event_index": event_index,
            "event": ev,
            "performance": perf,
            "authored": deepcopy(authored),
            "resolved": resolved,
        }
        groups.setdefault(resolved["stroke_id"], []).append(item)

    stroke_reports = {}
    strum_events = []
    for stroke_id, items in groups.items():
        if len(items) < 2:
            raise GuitarStrumError(
                f"strum stroke {stroke_id!r} must contain at least two note events"
            )

        first = items[0]["resolved"]
        common = {key: first[key] for key in _STRUM_COMMON_FIELDS}
        for item in items[1:]:
            candidate = {key: item["resolved"][key] for key in _STRUM_COMMON_FIELDS}
            if candidate != common:
                raise GuitarStrumError(
                    f"strum stroke {stroke_id!r} has inconsistent shared gesture state"
                )

        starts = [float(item["event"]["start_beat"]) for item in items]
        if max(starts) - min(starts) > 1e-12:
            raise GuitarStrumError(
                f"strum stroke {stroke_id!r} notes must share one nominal authored onset"
            )

        strings = [int(item["resolved"]["string"]) for item in items]
        if len(strings) != len(set(strings)):
            raise GuitarStrumError(
                f"strum stroke {stroke_id!r} has duplicate note state on one string"
            )

        methods = {str(item["resolved"]["right_hand_method"]) for item in items}
        if len(methods) != 1:
            raise GuitarStrumError(
                f"strum stroke {stroke_id!r} must use one shared right-hand method"
            )

        traversal = _traversal_strings(common)
        position_of = {string_number: i for i, string_number in enumerate(traversal)}
        denom = max(1, len(traversal) - 1)
        represented = set(strings)
        skipped = [s for s in traversal if s not in represented]
        profile = []

        for item in items:
            resolved = item["resolved"]
            ev = item["event"]
            perf = item["performance"]
            string_number = int(resolved["string"])
            idx = position_of[string_number]
            x = idx / denom
            offset_ms = float(common["traversal_ms"]) * x
            force = _force_at(x, common)

            # Preserve authored velocity as the score authority. AG06 contributes
            # a bounded render-local scale derived solely from the shared gesture.
            velocity_scale = 0.72 + 0.55 * force
            authored_velocity = float(ev.get("velocity", 0.8))
            render_velocity = max(
                0.0, min(1.0, authored_velocity * velocity_scale)
            )

            realization = {
                **deepcopy(resolved),
                "traversal_index": idx,
                "traversal_count": len(traversal),
                "traversal_position": x,
                "offset_ms": offset_ms,
                "force": force,
                "velocity_scale": velocity_scale,
                "authored_velocity": authored_velocity,
                "render_velocity": render_velocity,
                "effective_start_beat_preserved_in_score": float(ev["start_beat"]),
            }
            perf["strum_realization"] = deepcopy(realization)
            ev["performance"] = perf

            row = {
                "event_index": item["event_index"],
                "midi": int(ev["midi"]),
                "string": string_number,
                "fret": int(resolved["fret"]),
                "state": resolved["state"],
                "offset_ms": offset_ms,
                "force": force,
                "velocity_scale": velocity_scale,
                "authored_velocity": authored_velocity,
                "render_velocity": render_velocity,
            }
            profile.append(row)
            strum_events.append({"stroke_id": stroke_id, **row})

        profile.sort(key=lambda row: row["offset_ms"])
        forces = [row["force"] for row in profile]
        if len(profile) >= 3 and max(forces) - min(forces) < 1e-4:
            raise GuitarStrumError(
                f"strum stroke {stroke_id!r} produced an invalid uniform per-string force profile"
            )

        muted = [row["string"] for row in profile if row["state"] == "muted"]
        stroke_reports[stroke_id] = {
            "direction": common["direction"],
            "from_string": common["from_string"],
            "to_string": common["to_string"],
            "traversal_strings": traversal,
            "traversal_ms": common["traversal_ms"],
            "right_hand_method": next(iter(methods)),
            "represented_strings": sorted(represented),
            "skipped_strings": skipped,
            "muted_strings": muted,
            "profile": profile,
            "force_min": min(forces),
            "force_max": max(forces),
            "force_span": max(forces) - min(forces),
            "profile_authority": "deterministic_shared_gesture",
            "random_humanize": False,
        }

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
    track_report.setdefault("scope", {})["chord_strum"] = bool(strum_events)
    track_report["strum_event_count"] = len(strum_events)
    track_report["strum_events"] = strum_events
    track_report["strum_strokes"] = stroke_reports
    out["guitar_performance_report"] = report
    return out


__all__ = [
    "GuitarStrumError",
    "STRUM_DIRECTIONS",
    "STRUM_STATES",
    "resolve_strum",
    "realize_guitar_strum",
]
