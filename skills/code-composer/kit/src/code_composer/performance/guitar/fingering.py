"""AG02 standard-tuning acoustic-guitar string/fret authority.

String numbering follows common guitar convention:
1 = high E, 6 = low E.  The resolver only fills mechanics the Composer did not
author.  It never rewrites an explicit valid string/fret choice.
"""
from __future__ import annotations

from copy import deepcopy
import math


class GuitarFingeringError(ValueError):
    pass


STANDARD_TUNING = {
    1: {"name": "high_e", "open_midi": 64},
    2: {"name": "b", "open_midi": 59},
    3: {"name": "g", "open_midi": 55},
    4: {"name": "d", "open_midi": 50},
    5: {"name": "a", "open_midi": 45},
    6: {"name": "low_e", "open_midi": 40},
}
MAX_FRET = 20


def _integer(value, name: str, lo: int, hi: int) -> int:
    if isinstance(value, bool):
        raise GuitarFingeringError(f"{name} must be an integer")
    if isinstance(value, int):
        out = value
    elif isinstance(value, float) and math.isfinite(value) and value.is_integer():
        out = int(value)
    else:
        raise GuitarFingeringError(f"{name} must be an integer")
    if not lo <= out <= hi:
        raise GuitarFingeringError(f"{name} outside [{lo},{hi}]")
    return out


def fingering_candidates(midi: int) -> list[dict]:
    midi = int(midi)
    out = []
    for string_number, spec in STANDARD_TUNING.items():
        fret = midi - int(spec["open_midi"])
        if 0 <= fret <= MAX_FRET:
            out.append(_realization(string_number, fret, "candidate"))
    out.sort(key=lambda x: (int(x["fret"]), int(x["string"])))
    return out


def _realization(string_number: int, fret: int, authority: str) -> dict:
    spec = STANDARD_TUNING[int(string_number)]
    fret = int(fret)
    return {
        "string": int(string_number),
        "string_name": spec["name"],
        "open_midi": int(spec["open_midi"]),
        "fret": fret,
        "is_open": fret == 0,
        "effective_length_ratio": round(2.0 ** (-fret / 12.0), 9),
        "authority": str(authority),
    }


def resolve_fingering(midi: int, authored: dict | None = None) -> dict:
    """Resolve one note while preserving any explicit mechanics authority."""
    midi = int(midi)
    payload = deepcopy(authored) if isinstance(authored, dict) else {}
    has_string = "string" in payload
    has_fret = "fret" in payload

    if has_string:
        string_number = _integer(payload["string"], "string", 1, 6)
    else:
        string_number = None
    if has_fret:
        fret = _integer(payload["fret"], "fret", 0, MAX_FRET)
    else:
        fret = None

    if has_string and has_fret:
        expected = int(STANDARD_TUNING[string_number]["open_midi"]) + int(fret)
        if expected != midi:
            raise GuitarFingeringError(
                f"MIDI {midi} conflicts with authored string {string_number} / fret {fret}; "
                f"that position sounds MIDI {expected}"
            )
        return _realization(string_number, fret, "authored_string_fret")

    if has_string:
        fret = midi - int(STANDARD_TUNING[string_number]["open_midi"])
        if not 0 <= fret <= MAX_FRET:
            raise GuitarFingeringError(
                f"MIDI {midi} is not playable on authored string {string_number} "
                f"within frets 0..{MAX_FRET}"
            )
        return _realization(string_number, fret, "authored_string")

    if has_fret:
        matches = [
            string_no
            for string_no, spec in STANDARD_TUNING.items()
            if int(spec["open_midi"]) + int(fret) == midi
        ]
        if not matches:
            raise GuitarFingeringError(
                f"MIDI {midi} has no standard-tuning string at authored fret {fret}"
            )
        return _realization(matches[0], fret, "authored_fret")

    candidates = fingering_candidates(midi)
    if not candidates:
        raise GuitarFingeringError(
            f"MIDI {midi} has no standard-tuning acoustic-guitar fingering "
            f"within frets 0..{MAX_FRET}"
        )
    chosen = deepcopy(candidates[0])
    chosen["authority"] = "deterministic_resolver"
    return chosen


def realize_guitar_fingering(ir: dict, track_id: str, plan_instrument: dict) -> dict:
    """Attach string/fret realization without changing authored pitch or timing."""
    out = deepcopy(ir)
    plan_patch = plan_instrument.get("patch", {}) if isinstance(plan_instrument, dict) else {}
    graph = plan_patch.get("acoustic_guitar_graph", {}) if isinstance(plan_patch, dict) else {}
    if graph.get("physical_model") != "ag01_modal_bridge_body_v1":
        return out

    track = next((t for t in out.get("tracks", []) if t.get("id") == track_id), None)
    if track is None:
        raise GuitarFingeringError(f"track not found: {track_id}")

    report_events = []
    for event_index, ev in enumerate(track.get("events", [])):
        if "midi" not in ev:
            continue
        perf = deepcopy(ev.get("performance") or {})
        authored = perf.get("instrument") if isinstance(perf.get("instrument"), dict) else None
        realization = resolve_fingering(int(ev["midi"]), authored)
        perf["guitar_realization"] = deepcopy(realization)
        ev["performance"] = perf
        report_events.append({
            "event_index": event_index,
            "midi": int(ev["midi"]),
            "start_beat": float(ev["start_beat"]),
            "duration_beats": float(ev["duration_beats"]),
            "authored": deepcopy(authored) if authored is not None else None,
            "resolved": deepcopy(realization),
        })

    report = deepcopy(out.get("guitar_performance_report") or {
        "version": "1.0",
        "tuning": {
            "name": "standard",
            "string_1_to_6_open_midi": [64, 59, 55, 50, 45, 40],
            "max_fret": MAX_FRET,
        },
        "tracks": {},
    })
    tracks = report.setdefault("tracks", {})
    tracks[track_id] = {
        "instrument_id": track.get("instrument"),
        "event_count": len(report_events),
        "events": report_events,
        "scope": {
            "string_fret_authority": True,
            "right_hand_excitation": False,
            "left_hand_articulation": False,
            "strum": False,
            "percussion": False,
        },
    }
    out["guitar_performance_resolved"] = True
    out["guitar_performance_report"] = report
    return out


__all__ = [
    "GuitarFingeringError",
    "STANDARD_TUNING",
    "MAX_FRET",
    "fingering_candidates",
    "resolve_fingering",
    "realize_guitar_fingering",
]
