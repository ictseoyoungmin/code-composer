"""Evidence-only drummer limb/performance feasibility analysis.

S27-F deliberately does not rewrite or quantize authored drum events.  It maps
explicit percussion events onto a conservative four-limb drum-set model and
returns deterministic evidence for impossible or physically strained passages.

The model is intentionally modest: two stick hands, right foot on kick, left
foot on hi-hat pedal, and a one-dimensional kit-position proxy for hand travel.
Advanced techniques (rebound doubles, cross-handed playing, alternate cymbal
placement, double-kick pedals) can exceed these defaults, so rate/travel findings
are reported as strain evidence rather than automatic composition edits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


_EPS = 1e-12

# Drum-set position proxy.  These are not dimensions or MIDI pan values; they
# only encode relative reach from left-side hi-hat to right-side ride/floor tom.
_POSITION_OPTIONS = {
    "hat": (-1.00,),
    "snare": (-0.28,),
    "tom_high": (-0.02,),
    "tom_mid": (0.30,),
    "tom_floor": (0.88,),
    "ride": (0.96,),
    # A generic crash may be mounted on either side of a kit.  The assignment
    # chooses the side that requires less travel from the available hand.
    "crash": (-0.88, 0.88),
}


@dataclass(frozen=True)
class _HandState:
    time_s: float = -1e9
    position: float = -0.30
    drum: str = "rest"


def _drum_family(drum: str) -> str:
    name = str(drum or "")
    if name == "kick" or name.startswith("kick_"):
        return "kick"
    if name == "snare" or name.startswith("snare_"):
        return "snare"
    if name == "hat" or name.startswith("hat_"):
        return "hat"
    if name == "ride" or name.startswith("ride_"):
        return "ride"
    if name == "crash" or name.startswith("crash_"):
        return "crash"
    if name.startswith("tom_high"):
        return "tom_high"
    if name.startswith("tom_mid"):
        return "tom_mid"
    if name.startswith("tom_floor"):
        return "tom_floor"
    return name or "unknown"


def _limb_class(drum: str) -> str:
    family = _drum_family(drum)
    if family == "kick":
        return "right_foot"
    if drum in {"hat_pedal", "hat_foot_splash", "hat_pedal_control"}:
        return "left_foot"
    return "hand"


def _position_options(drum: str) -> tuple[float, ...]:
    return _POSITION_OPTIONS.get(_drum_family(drum), (0.0,))


def _drum_tracks(resolved_ir: dict) -> list[dict]:
    out = []
    for track in resolved_ir.get("tracks", []):
        events = [
            e for e in track.get("events", [])
            if e.get("event_type") == "drum"
            or (e.get("event_type") == "drum_control" and e.get("control") == "hi_hat_pedal_openness")
        ]
        if events:
            out.append({"track_id": track.get("id", "<unknown>"), "events": events})
    return out


def _event_rows(resolved_ir: dict) -> list[dict]:
    bpm = float(resolved_ir.get("transport", {}).get("bpm", 120.0))
    beat_s = 60.0 / max(bpm, _EPS)
    rows = []
    for track in _drum_tracks(resolved_ir):
        for idx, event in enumerate(track["events"]):
            beat = float(event.get("start_beat", 0.0))
            if event.get("event_type") == "drum_control":
                drum = "hat_pedal_control"
            else:
                drum = str(event.get("drum", ""))
            rows.append({
                "track_id": track["track_id"],
                "event_index": idx,
                "section_id": event.get("section_id"),
                "start_beat": beat,
                "time_s": beat * beat_s,
                "drum": drum,
                "family": _drum_family(drum),
                "limb_class": _limb_class(drum),
                "velocity": float(event.get("velocity", 0.0)),
            })
    rows.sort(key=lambda r: (r["time_s"], r["drum"], r["track_id"], r["event_index"]))
    return rows


def _issue(code: str, severity: str, message: str, **payload) -> dict:
    return {"code": code, "severity": severity, "message": message, **payload}


def _exact_capacity_issues(rows: list[dict], exact_window_s: float) -> list[dict]:
    issues = []
    if not rows:
        return issues

    i = 0
    while i < len(rows):
        t0 = rows[i]["time_s"]
        j = i + 1
        while j < len(rows) and rows[j]["time_s"] - t0 <= exact_window_s:
            j += 1
        group = rows[i:j]
        hands = [r for r in group if r["limb_class"] == "hand"]
        rf = [r for r in group if r["limb_class"] == "right_foot"]
        lf = [r for r in group if r["limb_class"] == "left_foot"]
        if len(hands) > 2:
            issues.append(_issue(
                "DRUM_HAND_CAPACITY", "high",
                "More than two stick-driven drum events require simultaneous hand strikes.",
                start_beat=min(r["start_beat"] for r in hands),
                drums=[r["drum"] for r in hands],
                required_hands=len(hands), available_hands=2,
            ))
        if len(rf) > 1:
            issues.append(_issue(
                "DRUM_RIGHT_FOOT_CAPACITY", "high",
                "Multiple kick-foot events occur at the same instant.",
                start_beat=min(r["start_beat"] for r in rf),
                drums=[r["drum"] for r in rf],
            ))
        if len(lf) > 1:
            issues.append(_issue(
                "DRUM_LEFT_FOOT_CAPACITY", "high",
                "Multiple hi-hat-foot events occur at the same instant.",
                start_beat=min(r["start_beat"] for r in lf),
                drums=[r["drum"] for r in lf],
            ))
        i = j
    return issues


def _near_simultaneous_bursts(rows: list[dict], window_s: float) -> list[dict]:
    issues = []
    hands = [r for r in rows if r["limb_class"] == "hand"]
    for i, first in enumerate(hands):
        j = i + 1
        while j < len(hands) and hands[j]["time_s"] - first["time_s"] <= window_s:
            j += 1
        group = hands[i:j]
        if len(group) > 2:
            issues.append(_issue(
                "DRUM_HAND_BURST_STRAIN", "medium",
                "Three or more stick attacks are packed into a very short hand window; verify intentional rudiment/rebound technique.",
                start_beat=first["start_beat"],
                window_ms=round(window_s * 1000.0, 3),
                drums=[r["drum"] for r in group],
                event_count=len(group),
            ))
    # Deduplicate overlapping sliding-window reports by (start, drums).
    unique = []
    seen = set()
    for issue in issues:
        key = (round(float(issue["start_beat"]), 6), tuple(issue["drums"]))
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    return unique


def _hand_cost(state: _HandState, time_s: float, position: float, side: str) -> float:
    dt = max(0.0, time_s - state.time_s)
    dx = abs(position - state.position)
    cost = dx * 0.45
    if dt < 0.035:
        cost += 100.0
    elif dt < 0.070:
        cost += (0.070 - dt) * 25.0
    if dt > 0:
        speed = dx / dt
        if speed > 16.0:
            cost += 20.0 + (speed - 16.0)
        elif speed > 8.0:
            cost += (speed - 8.0) * 0.45
    # Soft ergonomics preference only; crossing hands is legal.
    if side == "left" and position > 0.55:
        cost += 0.35
    if side == "right" and position < -0.55:
        cost += 0.35
    return cost


def _assign_hands(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    left = _HandState(position=-0.35)
    right = _HandState(position=0.35)
    assignments = []
    issues = []

    for row in [r for r in rows if r["limb_class"] == "hand"]:
        candidates = []
        for side, state in (("left_hand", left), ("right_hand", right)):
            short = "left" if side.startswith("left") else "right"
            for pos in _position_options(row["drum"]):
                candidates.append((_hand_cost(state, row["time_s"], pos, short), side, pos, state))
        candidates.sort(key=lambda x: (x[0], x[1], x[2]))
        _, side, pos, prev = candidates[0]
        interval_s = max(0.0, row["time_s"] - prev.time_s)
        travel = abs(pos - prev.position)
        interval_ms = interval_s * 1000.0

        if prev.time_s > -1e8:
            if interval_s < 0.035:
                issues.append(_issue(
                    "DRUM_HAND_RATE_EXTREME", "medium",
                    "Assigned hand repeats faster than the conservative S27-F extreme-rate threshold; verify rebound/rudiment intent.",
                    limb=side, start_beat=row["start_beat"], drum=row["drum"],
                    previous_drum=prev.drum, interval_ms=round(interval_ms, 3),
                ))
            elif interval_s < 0.070:
                issues.append(_issue(
                    "DRUM_HAND_RATE_STRAIN", "low",
                    "Assigned hand repeats at a demanding rate; keep as evidence rather than an automatic rejection.",
                    limb=side, start_beat=row["start_beat"], drum=row["drum"],
                    previous_drum=prev.drum, interval_ms=round(interval_ms, 3),
                ))
            if interval_s > 0 and travel >= 1.0:
                speed = travel / interval_s
                if speed > 16.0:
                    issues.append(_issue(
                        "DRUM_HAND_TRAVEL_STRAIN", "medium",
                        "Large kit-position move occurs in a very short interval; verify sticking/kit layout.",
                        limb=side, start_beat=row["start_beat"], drum=row["drum"],
                        previous_drum=prev.drum, interval_ms=round(interval_ms, 3),
                        travel=round(travel, 3), travel_rate=round(speed, 3),
                    ))
                elif speed > 8.0:
                    issues.append(_issue(
                        "DRUM_HAND_TRAVEL_STRAIN", "low",
                        "Fast cross-kit movement detected; verify sticking if the passage feels awkward.",
                        limb=side, start_beat=row["start_beat"], drum=row["drum"],
                        previous_drum=prev.drum, interval_ms=round(interval_ms, 3),
                        travel=round(travel, 3), travel_rate=round(speed, 3),
                    ))

        assigned = {**row, "limb": side, "position": round(pos, 3)}
        assignments.append(assigned)
        new_state = _HandState(row["time_s"], pos, row["drum"])
        if side == "left_hand":
            left = new_state
        else:
            right = new_state

    return assignments, issues


def _foot_evidence(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    assignments = []
    issues = []
    last = {"right_foot": None, "left_foot": None}
    for row in rows:
        limb = row["limb_class"]
        if limb not in last:
            continue
        prev = last[limb]
        if prev is not None:
            dt = row["time_s"] - prev["time_s"]
            ms = dt * 1000.0
            if dt < 0.045:
                issues.append(_issue(
                    "DRUM_FOOT_RATE_EXTREME", "medium",
                    "Same foot repeats extremely quickly; verify pedal technique or authored event duplication.",
                    limb=limb, start_beat=row["start_beat"], drum=row["drum"],
                    previous_drum=prev["drum"], interval_ms=round(ms, 3),
                ))
            elif dt < 0.090:
                issues.append(_issue(
                    "DRUM_FOOT_RATE_STRAIN", "low",
                    "Same foot repeats at a demanding rate; retained as non-blocking technique evidence.",
                    limb=limb, start_beat=row["start_beat"], drum=row["drum"],
                    previous_drum=prev["drum"], interval_ms=round(ms, 3),
                ))
        assignments.append({**row, "limb": limb})
        last[limb] = row
    return assignments, issues


def analyze_drummer_performance(
    resolved_ir: dict,
    *,
    exact_simultaneous_ms: float = 1.0,
    burst_window_ms: float = 18.0,
) -> dict:
    """Return deterministic four-limb feasibility evidence for authored drums.

    No events are altered.  ``playable`` means no structural HIGH-severity limb
    capacity contradiction was found; MEDIUM/LOW findings are technique/strain
    evidence for the Composer Agent to inspect rather than hard rejection.
    """
    rows = _event_rows(resolved_ir)
    bpm = float(resolved_ir.get("transport", {}).get("bpm", 120.0))
    issues = []
    issues.extend(_exact_capacity_issues(rows, max(0.0, exact_simultaneous_ms) / 1000.0))
    issues.extend(_near_simultaneous_bursts(rows, max(0.0, burst_window_ms) / 1000.0))
    hand_assignments, hand_issues = _assign_hands(rows)
    foot_assignments, foot_issues = _foot_evidence(rows)
    issues.extend(hand_issues)
    issues.extend(foot_issues)

    # Stable deterministic order for machine evidence / golden tests.
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    issues.sort(key=lambda x: (
        severity_rank.get(str(x.get("severity", "low")), 9),
        float(x.get("start_beat", -1.0)), str(x.get("code", "")), str(x.get("limb", "")),
    ))
    assignments = sorted(
        hand_assignments + foot_assignments,
        key=lambda x: (float(x.get("start_beat", 0.0)), str(x.get("limb", "")), str(x.get("drum", ""))),
    )
    counts = {"high": 0, "medium": 0, "low": 0}
    for issue in issues:
        sev = str(issue.get("severity", "low"))
        counts[sev] = counts.get(sev, 0) + 1

    hand_count = sum(1 for r in rows if r["limb_class"] == "hand")
    right_foot_count = sum(1 for r in rows if r["limb_class"] == "right_foot")
    left_foot_count = sum(1 for r in rows if r["limb_class"] == "left_foot")
    return {
        "version": "1.0.0",
        "semantics": "evidence_only_no_event_mutation",
        "bpm": bpm,
        "event_count": len(rows),
        "limb_event_counts": {
            "hands": hand_count,
            "right_foot": right_foot_count,
            "left_foot": left_foot_count,
        },
        "playable": counts.get("high", 0) == 0,
        "strained": (counts.get("medium", 0) + counts.get("low", 0)) > 0,
        "issue_count": len(issues),
        "issue_counts": counts,
        "issues": issues,
        "assignments": assignments,
        "thresholds": {
            "exact_simultaneous_ms": float(exact_simultaneous_ms),
            "burst_window_ms": float(burst_window_ms),
            "hand_extreme_repeat_ms": 35.0,
            "hand_strain_repeat_ms": 70.0,
            "foot_extreme_repeat_ms": 45.0,
            "foot_strain_repeat_ms": 90.0,
            "travel_medium_rate_units_per_s": 16.0,
        },
    }


__all__ = ["analyze_drummer_performance"]
