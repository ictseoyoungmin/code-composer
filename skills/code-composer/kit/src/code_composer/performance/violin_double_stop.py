from __future__ import annotations

from copy import deepcopy
from itertools import product


class ViolinDoubleStopError(ValueError):
    pass


def _gesture_groups(events: list[dict]) -> list[dict]:
    """Group pitched events into synchronous single/double-stop gestures.

    S4 deliberately supports block gestures only: at most two notes may begin
    together, the notes of a double stop must have equal duration, and a new
    onset may not enter while the previous gesture is still sounding.
    """
    pitched = [deepcopy(e) for e in events if e.get("event_type") != "drum" and "midi" in e]
    pitched.sort(key=lambda e: (float(e.get("start_beat", 0)), int(e["midi"])))
    if not pitched:
        return []

    groups: list[dict] = []
    for ev in pitched:
        start = float(ev.get("start_beat", 0))
        if groups and abs(start - groups[-1]["start_beat"]) < 1e-9:
            groups[-1]["events"].append(ev)
        else:
            groups.append({"start_beat": start, "events": [ev]})

    prev_end = None
    for gidx, group in enumerate(groups):
        members = group["events"]
        if len(members) > 2:
            raise ViolinDoubleStopError(
                f"gesture {gidx} has {len(members)} simultaneous pitches; S4 supports at most two"
            )
        if len({int(x["midi"]) for x in members}) != len(members):
            raise ViolinDoubleStopError(f"gesture {gidx} repeats the same pitch at one onset")

        durations = [float(x.get("duration_beats", 0)) for x in members]
        if any(x <= 0 for x in durations):
            raise ViolinDoubleStopError(f"gesture {gidx} has non-positive duration")
        if len(members) == 2 and abs(durations[0] - durations[1]) > 1e-9:
            raise ViolinDoubleStopError(
                f"gesture {gidx} double-stop notes must have equal duration in S4"
            )

        articulations = []
        for ev in members:
            perf = ev.get("performance") if isinstance(ev.get("performance"), dict) else {}
            articulations.append(str(perf.get("articulation", "neutral")))
        if len(set(articulations)) > 1:
            raise ViolinDoubleStopError(
                f"gesture {gidx} double-stop notes must share one articulation in S4"
            )

        duration = max(durations)
        end = float(group["start_beat"]) + duration
        if prev_end is not None and float(group["start_beat"]) < prev_end - 1e-9:
            raise ViolinDoubleStopError(
                "S4 double-stop planner supports synchronous block gestures only; overlapping different onsets are not supported"
            )
        group["duration_beats"] = duration
        group["articulation"] = articulations[0]
        group["velocity"] = max(float(x.get("velocity", .7)) for x in members)
        group["gesture_type"] = "double_stop" if len(members) == 2 else "single"
        prev_end = end
    return groups


def _frame_position(notes: list[dict]) -> float:
    positions = [int(n["left_hand"]["position"]) for n in notes if int(n["left_hand"]["position"]) > 0]
    if not positions:
        return 0.0
    return sum(positions) / len(positions)


def _single_states(event: dict) -> list[dict]:
    from .violin_mechanics import fingering_candidates, _candidate_local_cost

    states = []
    midi = int(event["midi"])
    for fingering in fingering_candidates(midi):
        notes = [{"midi": midi, "left_hand": fingering}]
        states.append({
            "gesture_type": "single",
            "notes": notes,
            "strings": [int(fingering["string_index"])],
            "frame_position": _frame_position(notes),
            "local_cost": _candidate_local_cost(fingering),
            "gesture_score": 0.0,
            "double_stop": None,
        })
    return states


def _double_states(group: dict, cfg: dict) -> list[dict]:
    from .violin_mechanics import fingering_candidates, _candidate_local_cost

    low, high = sorted(group["events"], key=lambda e: int(e["midi"]))
    low_midi, high_midi = int(low["midi"]), int(high["midi"])
    states = []
    for a, b in product(fingering_candidates(low_midi), fingering_candidates(high_midi)):
        # A bowed double stop must use adjacent strings. The lower pitch belongs
        # to the lower-pitched string in this intentionally conservative model.
        if int(b["string_index"]) - int(a["string_index"]) != 1:
            continue

        apos, bpos = int(a["position"]), int(b["position"])
        nonzero_positions = [p for p in (apos, bpos) if p > 0]
        position_gap = abs(apos - bpos) if apos > 0 and bpos > 0 else 0
        if position_gap > int(cfg["double_stop_max_position_gap"]):
            continue

        af, bf = int(a["finger"]), int(b["finger"])
        a_stop = int(a["stopped_semitones"])
        b_stop = int(b["stopped_semitones"])
        same_finger_fifth = False
        if af > 0 and af == bf:
            # One finger may flatten across adjacent strings for a stopped fifth,
            # but it cannot simultaneously stop two different longitudinal points.
            if a_stop != b_stop:
                continue
            same_finger_fifth = True
        elif af > 0 and bf > 0:
            # In this conservative hand-frame model finger order must agree with
            # longitudinal stop order.  Crossing finger numbers across strings is
            # possible only through much more detailed hand geometry, which S4
            # deliberately does not claim to model.
            if (af < bf and a_stop > b_stop) or (af > bf and a_stop < b_stop):
                continue

        if af > 0 and bf > 0:
            stretch = abs(a_stop - b_stop)
        else:
            # Open+stopped combinations do not require a two-finger span.
            stretch = 0
        if stretch > int(cfg["double_stop_max_stretch_semitones"]):
            continue

        frame_position = (sum(nonzero_positions) / len(nonzero_positions)) if nonzero_positions else 0.0
        gesture_score = (
            0.45
            + 0.16 * float(position_gap)
            + 0.18 * float(max(0, stretch - 4))
            + (0.55 if same_finger_fifth else 0.0)
            + (0.12 * max(0.0, frame_position - 7.0))
        )
        local_cost = _candidate_local_cost(a) + _candidate_local_cost(b) + gesture_score * .35
        string_pair = [str(a["string"]), str(b["string"])]
        notes = [
            {"midi": low_midi, "left_hand": a},
            {"midi": high_midi, "left_hand": b},
        ]
        states.append({
            "gesture_type": "double_stop",
            "notes": notes,
            "strings": [int(a["string_index"]), int(b["string_index"])],
            "frame_position": frame_position,
            "local_cost": local_cost,
            "gesture_score": gesture_score,
            "double_stop": {
                "string_pair": string_pair,
                "position_gap": position_gap,
                "stretch_semitones": stretch,
                "same_finger_fifth": same_finger_fifth,
                "hand_frame_position": round(frame_position, 6),
                "gesture_score": round(gesture_score, 6),
            },
        })

    states.sort(key=lambda s: (
        round(float(s["local_cost"]), 12),
        tuple(s["strings"]),
        tuple(int(n["left_hand"]["position"]) for n in s["notes"]),
        tuple(int(n["left_hand"]["finger"]) for n in s["notes"]),
    ))
    if not states:
        raise ViolinDoubleStopError(
            f"no supported adjacent-string double-stop fingering for MIDI {low_midi}+{high_midi} within S4 comfort scope"
        )
    return states


def double_stop_candidates(low_midi: int, high_midi: int, *, config: dict | None = None) -> list[dict]:
    """Public inspection helper for one synchronous two-note violin gesture."""
    from .violin_mechanics import _merge_config

    if int(low_midi) == int(high_midi):
        raise ViolinDoubleStopError("double-stop pitches must be distinct")
    group = {
        "events": [
            {"midi": int(low_midi), "duration_beats": 1.0, "velocity": .7},
            {"midi": int(high_midi), "duration_beats": 1.0, "velocity": .7},
        ]
    }
    return deepcopy(_double_states(group, _merge_config(config)))


def _gesture_transition(a: dict, b: dict, delta_s: float) -> tuple[float, dict]:
    from .violin_mechanics import _transition_cost

    if a["gesture_type"] == "single" and b["gesture_type"] == "single":
        return _transition_cost(a["notes"][0]["left_hand"], b["notes"][0]["left_hand"], delta_s)

    acenter = sum(a["strings"]) / len(a["strings"])
    bcenter = sum(b["strings"]) / len(b["strings"])
    crossing = abs(bcenter - acenter)
    apos = float(a["frame_position"])
    bpos = float(b["frame_position"])
    shift = 0.0 if apos == 0 or bpos == 0 else abs(bpos - apos)
    time_factor = 1.0 / max(.12, float(delta_s))
    score = crossing * .30 * time_factor + shift * .43 * time_factor
    if a["gesture_type"] != b["gesture_type"]:
        score += .18
    if b["gesture_type"] == "double_stop":
        score += min(1.5, float(b["gesture_score"]) * .20)
    return score, {
        "string_crossing": round(crossing, 6),
        "position_shift": round(shift, 6),
        "transition_seconds": round(float(delta_s), 6),
        "score": round(score, 6),
        "double_stop_transition": True,
    }


def _choose_states(groups: list[dict], bpm: float, cfg: dict) -> tuple[list[dict], list[dict]]:
    if not groups:
        return [], []
    candidate_sets = []
    lo, hi = cfg["range_midi"]
    for gidx, group in enumerate(groups):
        for ev in group["events"]:
            midi = int(ev["midi"])
            if not lo <= midi <= hi:
                raise ViolinDoubleStopError(
                    f"gesture {gidx} MIDI {midi} is outside configured violin range {lo}..{hi}"
                )
        states = _double_states(group, cfg) if group["gesture_type"] == "double_stop" else _single_states(group["events"][0])
        if not states:
            raise ViolinDoubleStopError(f"gesture {gidx} has no supported violin realization")
        candidate_sets.append(states)

    dp = [{j: (float(state["local_cost"]), None, None) for j, state in enumerate(candidate_sets[0])}]
    beat_s = 60.0 / float(bpm)
    for i in range(1, len(groups)):
        now = {}
        delta_s = max(0.0, float(groups[i]["start_beat"]) - float(groups[i-1]["start_beat"])) * beat_s
        for j, state in enumerate(candidate_sets[i]):
            best = None
            for k, prev in enumerate(candidate_sets[i-1]):
                tscore, detail = _gesture_transition(prev, state, delta_s)
                total = dp[-1][k][0] + tscore + float(state["local_cost"])
                cand = (total, k, detail)
                if best is None or cand[0] < best[0] - 1e-12 or (
                    abs(cand[0] - best[0]) < 1e-12 and k < best[1]
                ):
                    best = cand
            now[j] = best
        dp.append(now)

    idx = min(dp[-1], key=lambda j: (dp[-1][j][0], j))
    chosen = [None] * len(groups)
    transitions = [None] * len(groups)
    for i in range(len(groups) - 1, -1, -1):
        chosen[i] = deepcopy(candidate_sets[i][idx])
        total, prev_idx, detail = dp[i][idx]
        chosen[i]["path_cost"] = round(float(total), 6)
        if i > 0:
            transitions[i] = detail
        idx = prev_idx if prev_idx is not None else 0
    transitions[0] = {
        "string_crossing": 0,
        "position_shift": 0,
        "transition_seconds": 0.0,
        "score": 0.0,
        "double_stop_transition": False,
    }
    return chosen, transitions


def _bow_group_indices(groups: list[dict], bpm: float, cfg: dict) -> list[list[int]]:
    beat_s = 60.0 / float(bpm)
    out: list[list[int]] = []
    for i, gesture in enumerate(groups):
        if not out:
            out.append([i])
            continue
        prev = groups[out[-1][-1]]
        gap = float(gesture["start_beat"]) - (float(prev["start_beat"]) + float(prev["duration_beats"]))
        group_start = float(groups[out[-1][0]]["start_beat"])
        group_end = float(gesture["start_beat"]) + float(gesture["duration_beats"])
        duration_s = (group_end - group_start) * beat_s
        can_legato = (
            prev["articulation"] == "legato"
            and gesture["articulation"] == "legato"
            and gap <= cfg["legato_gap_beats"] + 1e-9
            and duration_s <= cfg["max_bow_duration_s"] + 1e-9
        )
        if can_legato:
            out[-1].append(i)
        else:
            out.append([i])
    return out


def _bowing(groups: list[dict], chosen: list[dict], bpm: float, cfg: dict) -> list[dict]:
    from .violin_mechanics import _clamp

    beat_s = 60.0 / float(bpm)
    result = [None] * len(groups)
    for bgidx, members in enumerate(_bow_group_indices(groups, bpm, cfg)):
        direction = "down" if bgidx % 2 == 0 else "up"
        gstart = float(groups[members[0]]["start_beat"])
        gend = max(float(groups[j]["start_beat"]) + float(groups[j]["duration_beats"]) for j in members)
        duration_s = max(.01, (gend - gstart) * beat_s)
        use = _clamp(duration_s / cfg["max_bow_duration_s"], .16, .92)
        bow_start = .94 if direction == "down" else .06
        bow_end = _clamp(bow_start - use if direction == "down" else bow_start + use, .02, .98)
        span = bow_end - bow_start
        for local_idx, gesture_index in enumerate(members):
            gesture = groups[gesture_index]
            state = chosen[gesture_index]
            e0 = max(0.0, (float(gesture["start_beat"]) - gstart) / max(1e-9, gend - gstart))
            e1 = max(e0, min(1.0, (
                float(gesture["start_beat"]) + float(gesture["duration_beats"]) - gstart
            ) / max(1e-9, gend - gstart)))
            velocity = max(.01, min(1.0, float(gesture["velocity"])))
            double = state["gesture_type"] == "double_stop"
            speed = _clamp(.30 + .40 * velocity + .10 * min(1.0, use) - (.03 if double else 0.0), .20, .90)
            force = _clamp(.26 + .48 * velocity + (.06 if double else 0.0), .20, .88)
            item = {
                "group_id": f"bow-{bgidx+1:03d}",
                "direction": direction,
                "group_note_index": local_idx,
                "group_note_count": len(members),
                "bow_start": round(bow_start + span * e0, 6),
                "bow_end": round(bow_start + span * e1, 6),
                "usage_fraction": round(use * max(0.0, e1 - e0), 6),
                "force_curve": [[0.0, round(force, 6)], [1.0, round(force, 6)]],
                "speed_curve": [[0.0, round(speed, 6)], [1.0, round(speed, 6)]],
                "contact_strings": [n["left_hand"]["string"] for n in state["notes"]],
            }
            if cfg["default_contact_point"] is not None:
                item["contact_point_curve"] = [
                    [0.0, round(cfg["default_contact_point"], 6)],
                    [1.0, round(cfg["default_contact_point"], 6)],
                ]
            result[gesture_index] = item
    return result


def plan_double_stop_track(events: list[dict], *, bpm: float, cfg: dict) -> dict:
    groups = _gesture_groups(events)
    if not groups:
        return {
            "version": "1.0",
            "events": [],
            "playability": {"classification": "empty", "max_transition_score": 0.0, "max_gesture_score": 0.0, "max_difficulty_score": 0.0, "warning_count": 0, "warnings": []},
            "config": deepcopy(cfg),
        }

    chosen, transitions = _choose_states(groups, bpm, cfg)
    bows = _bowing(groups, chosen, bpm, cfg)
    planned = []
    warnings = []
    max_transition = 0.0
    max_gesture = 0.0

    for gidx, (group, state, transition, bow) in enumerate(zip(groups, chosen, transitions, bows)):
        tscore = float(transition["score"])
        gscore = float(state["gesture_score"])
        max_transition = max(max_transition, tscore)
        max_gesture = max(max_gesture, gscore)
        if tscore > cfg["comfortable_transition_score"]:
            warnings.append({
                "gesture_index": gidx,
                "type": "transition_difficulty",
                "score": round(tscore, 6),
                "midis": [int(x["midi"]) for x in group["events"]],
            })
        if gscore > cfg["comfortable_transition_score"]:
            warnings.append({
                "gesture_index": gidx,
                "type": "double_stop_difficulty",
                "score": round(gscore, 6),
                "midis": [int(x["midi"]) for x in group["events"]],
            })

        gesture_id = f"gesture-{gidx+1:03d}"
        note_by_midi = {int(x["midi"]): x for x in state["notes"]}
        for ev in sorted(group["events"], key=lambda e: int(e["midi"])):
            midi = int(ev["midi"])
            note = note_by_midi[midi]
            item = {
                "event_index": len(planned),
                "gesture_id": gesture_id,
                "gesture_type": state["gesture_type"],
                "midi": midi,
                "start_beat": float(ev["start_beat"]),
                "duration_beats": float(ev["duration_beats"]),
                "left_hand": deepcopy(note["left_hand"]),
                "transition": deepcopy(transition),
                "bow": deepcopy(bow),
            }
            if state["gesture_type"] == "double_stop":
                partner = next(int(x["midi"]) for x in group["events"] if int(x["midi"]) != midi)
                item["double_stop"] = {
                    **deepcopy(state["double_stop"]),
                    "partner_midi": partner,
                }
            planned.append(item)

    hardest = max(max_transition, max_gesture)
    if hardest <= cfg["comfortable_transition_score"]:
        classification = "comfortable"
    elif hardest <= cfg["challenging_transition_score"]:
        classification = "challenging"
    else:
        classification = "impractical"
    if cfg["strict_comfort"] and classification != "comfortable":
        raise ViolinDoubleStopError(
            f"violin line is {classification}; max difficulty score {hardest:.3f} exceeds comfortable threshold {cfg['comfortable_transition_score']:.3f}"
        )

    return {
        "version": "1.0",
        "events": planned,
        "playability": {
            "classification": classification,
            "max_transition_score": round(max_transition, 6),
            "max_gesture_score": round(max_gesture, 6),
            "max_difficulty_score": round(hardest, 6),
            "warning_count": len(warnings),
            "warnings": warnings,
        },
        "config": deepcopy(cfg),
    }


__all__ = ["ViolinDoubleStopError", "double_stop_candidates", "plan_double_stop_track"]
