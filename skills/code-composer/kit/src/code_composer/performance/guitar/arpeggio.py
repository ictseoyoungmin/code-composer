"""AG05 authored multi-string arpeggio / fingerstyle coordination.

AG05 does not invent notes, chord voicings, string order, timing, or right-hand
methods. It validates Composer-authored per-note multi-string intent and records
how independent string states form one arpeggio/fingerstyle gesture.
"""
from __future__ import annotations

from copy import deepcopy


class GuitarArpeggioError(ValueError):
    pass


PLAYERS = ("thumb", "index", "middle", "ring", "pick")
VOICE_ROLES = ("bass", "inner", "treble")


def _integer(value, name: str, lo: int, hi: int) -> int:
    if isinstance(value, bool):
        raise GuitarArpeggioError(f"{name} must be integer")
    if isinstance(value, int):
        out = value
    elif isinstance(value, float) and value.is_integer():
        out = int(value)
    else:
        raise GuitarArpeggioError(f"{name} must be integer")
    if not lo <= out <= hi:
        raise GuitarArpeggioError(f"{name} outside [{lo},{hi}]")
    return out


def resolve_arpeggio(payload: dict, *, current_event: dict) -> dict:
    if not isinstance(payload, dict) or not payload:
        raise GuitarArpeggioError("arpeggio must be a non-empty object")

    unknown = set(payload) - {"gesture_id", "player", "voice", "sequence_index"}
    if unknown:
        raise GuitarArpeggioError(
            f"unsupported AG05 arpeggio field(s): {sorted(unknown)}"
        )

    gesture_id = payload.get("gesture_id")
    if not isinstance(gesture_id, str) or not gesture_id.strip():
        raise GuitarArpeggioError("arpeggio.gesture_id must be a non-empty string")

    player = str(payload.get("player", ""))
    if player not in PLAYERS:
        raise GuitarArpeggioError(
            f"arpeggio.player must be one of {list(PLAYERS)}"
        )

    voice = str(payload.get("voice", ""))
    if voice not in VOICE_ROLES:
        raise GuitarArpeggioError(
            f"arpeggio.voice must be one of {list(VOICE_ROLES)}"
        )

    sequence_index = _integer(
        payload.get("sequence_index"),
        "arpeggio.sequence_index",
        0,
        127,
    )

    perf = current_event.get("performance") or {}
    fingering = perf.get("guitar_realization")
    if not isinstance(fingering, dict):
        raise GuitarArpeggioError("AG05 requires resolved AG02 guitar fingering")
    string_number = int(fingering["string"])

    right = perf.get("right_hand_realization")
    if not isinstance(right, dict):
        raise GuitarArpeggioError(
            "AG05 requires explicit AG03 right_hand on every arpeggio note"
        )
    method = str(right.get("method", ""))

    if player == "thumb" and method != "thumb":
        raise GuitarArpeggioError("arpeggio thumb requires right_hand.method='thumb'")
    if player in {"index", "middle", "ring"} and method not in {"finger", "nail"}:
        raise GuitarArpeggioError(
            f"arpeggio {player} requires right_hand.method finger or nail"
        )
    if player == "pick" and method != "pick":
        raise GuitarArpeggioError("arpeggio pick requires right_hand.method='pick'")

    if voice == "bass" and string_number not in {4, 5, 6}:
        raise GuitarArpeggioError(
            f"arpeggio bass voice requires string 4..6; got string {string_number}"
        )
    if voice == "treble" and string_number not in {1, 2, 3}:
        raise GuitarArpeggioError(
            f"arpeggio treble voice requires string 1..3; got string {string_number}"
        )
    if voice == "inner" and string_number not in {2, 3, 4, 5}:
        raise GuitarArpeggioError(
            f"arpeggio inner voice requires string 2..5; got string {string_number}"
        )

    return {
        "gesture_id": gesture_id.strip(),
        "player": player,
        "voice": voice,
        "sequence_index": sequence_index,
        "string": string_number,
        "fret": int(fingering["fret"]),
        "right_hand_method": method,
        "authority": "authored_arpeggio",
    }


def _max_distinct_string_overlap(events: list[dict]) -> int:
    points = []
    for e in events:
        points.append((float(e["start_beat"]), 1, int(e["string"])))
        points.append((float(e["end_beat"]), -1, int(e["string"])))
    # End events first at equal time: a reattack at exact note-off is not overlap.
    points.sort(key=lambda x: (x[0], x[1]))
    active: dict[int, int] = {}
    best = 0
    for _, kind, string_number in points:
        if kind < 0:
            active[string_number] = max(0, active.get(string_number, 0) - 1)
            if active[string_number] == 0:
                active.pop(string_number, None)
        else:
            active[string_number] = active.get(string_number, 0) + 1
            best = max(best, len(active))
    return best


def realize_guitar_arpeggio(ir: dict, track_id: str, plan_instrument: dict) -> dict:
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
        raise GuitarArpeggioError(f"track not found: {track_id}")

    groups: dict[str, list[dict]] = {}
    arpeggio_events = []
    for event_index, ev in enumerate(track.get("events", [])):
        if "midi" not in ev:
            continue
        perf = deepcopy(ev.get("performance") or {})
        instrument = perf.get("instrument") if isinstance(perf.get("instrument"), dict) else {}
        authored = instrument.get("arpeggio")
        if authored is None:
            continue

        realization = resolve_arpeggio(authored, current_event=ev)
        perf["arpeggio_realization"] = deepcopy(realization)
        ev["performance"] = perf

        item = {
            "event_index": event_index,
            "midi": int(ev["midi"]),
            "start_beat": float(ev["start_beat"]),
            "duration_beats": float(ev["duration_beats"]),
            "end_beat": float(ev["start_beat"]) + float(ev["duration_beats"]),
            **deepcopy(realization),
        }
        arpeggio_events.append(item)
        groups.setdefault(realization["gesture_id"], []).append(item)

    gesture_reports = {}
    for gesture_id, events in groups.items():
        if len(events) < 2:
            raise GuitarArpeggioError(
                f"arpeggio gesture {gesture_id!r} must contain at least two notes"
            )

        by_sequence = sorted(events, key=lambda x: x["sequence_index"])
        sequence_ids = [e["sequence_index"] for e in by_sequence]
        if len(sequence_ids) != len(set(sequence_ids)):
            raise GuitarArpeggioError(
                f"arpeggio gesture {gesture_id!r} has duplicate sequence_index"
            )
        starts = [e["start_beat"] for e in by_sequence]
        if any(b <= a + 1e-12 for a, b in zip(starts, starts[1:])):
            raise GuitarArpeggioError(
                f"arpeggio gesture {gesture_id!r} sequence order must match strictly increasing authored onsets"
            )

        strings = {e["string"] for e in events}
        if len(strings) < 2:
            raise GuitarArpeggioError(
                f"arpeggio gesture {gesture_id!r} must span at least two strings"
            )

        for string_number in sorted(strings):
            same = sorted(
                (e for e in events if e["string"] == string_number),
                key=lambda x: x["start_beat"],
            )
            for prev, nxt in zip(same, same[1:]):
                if nxt["start_beat"] < prev["end_beat"] - 1e-12:
                    raise GuitarArpeggioError(
                        f"arpeggio gesture {gesture_id!r} overlaps independent notes "
                        f"on string {string_number}; AG05 does not stack two states on one string"
                    )

        bass = [e for e in events if e["voice"] == "bass"]
        upper = [e for e in events if e["voice"] in {"inner", "treble"}]
        bass_upper_overlap = sum(
            1
            for b in bass
            for u in upper
            if b["start_beat"] < u["start_beat"] < b["end_beat"] - 1e-12
        )

        players = [e["player"] for e in by_sequence]
        repeated_finger_steps = sum(
            1
            for a, b in zip(players, players[1:])
            if a == b and a in {"index", "middle", "ring"}
        )

        gesture_reports[gesture_id] = {
            "event_count": len(events),
            "distinct_strings": sorted(strings),
            "sequence_indexes": sequence_ids,
            "players": players,
            "voices": [e["voice"] for e in by_sequence],
            "max_distinct_string_overlap": _max_distinct_string_overlap(events),
            "bass_upper_overlap_count": bass_upper_overlap,
            "repeated_finger_steps": repeated_finger_steps,
            "pattern_authority": "composer_authored",
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
    track_report.setdefault("scope", {})["arpeggio_fingerstyle"] = bool(arpeggio_events)
    track_report["arpeggio_event_count"] = len(arpeggio_events)
    track_report["arpeggio_events"] = arpeggio_events
    track_report["arpeggio_gestures"] = gesture_reports
    out["guitar_performance_report"] = report
    return out


__all__ = [
    "GuitarArpeggioError",
    "PLAYERS",
    "VOICE_ROLES",
    "resolve_arpeggio",
    "realize_guitar_arpeggio",
]
