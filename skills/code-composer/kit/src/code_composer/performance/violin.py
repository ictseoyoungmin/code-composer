from __future__ import annotations

from copy import deepcopy
import math

from ..audio.engines import engine_for_patch
from ..composition.arrange import arrange_ir
from ..composition.resolve import resolve_ir
from ..composition.performance import realize_performance_ir
from ..core.ir import validate_ir
from ..validation_contracts import validate_runtime_extensions
from .violin_mechanics import (
    ViolinPerformanceError,
    STRINGS,
    DEFAULT_VIOLIN_CONFIG,
    fingering_candidates,
    _clamp,
    _merge_config,
    _candidate_local_cost,
    _transition_cost,
)


def _prepare_events(events: list[dict]) -> list[dict]:
    pitched = [dict(e) for e in events if e.get("event_type") != "drum" and "midi" in e]
    pitched.sort(key=lambda e: (float(e.get("start_beat", 0)), int(e["midi"])))
    for a, b in zip(pitched, pitched[1:]):
        if abs(float(a["start_beat"]) - float(b["start_beat"])) < 1e-9:
            raise ViolinPerformanceError("S3 violin planner supports monophonic material only")
    return pitched


def _choose_fingerings(events: list[dict], bpm: float, cfg: dict) -> tuple[list[dict], list[dict]]:
    if not events:
        return [], []
    lo, hi = cfg["range_midi"]
    candidate_sets = []
    for i, ev in enumerate(events):
        midi = int(ev["midi"])
        if not lo <= midi <= hi:
            raise ViolinPerformanceError(
                f"event {i} MIDI {midi} is outside configured violin range {lo}..{hi}"
            )
        candidates = fingering_candidates(midi)
        if not candidates:
            raise ViolinPerformanceError(f"event {i} MIDI {midi} has no supported violin fingering")
        candidate_sets.append(candidates)

    states = [{j: (_candidate_local_cost(c), None, None) for j, c in enumerate(candidate_sets[0])}]
    beat_s = 60.0 / float(bpm)
    for i in range(1, len(events)):
        now = {}
        delta_beats = max(0.0, float(events[i]["start_beat"]) - float(events[i-1]["start_beat"]))
        delta_s = delta_beats * beat_s
        for j, c in enumerate(candidate_sets[i]):
            best = None
            for k, prev in enumerate(candidate_sets[i-1]):
                prev_cost = states[-1][k][0]
                tcost, detail = _transition_cost(prev, c, delta_s)
                total = prev_cost + tcost + _candidate_local_cost(c)
                candidate = (total, k, detail)
                if best is None or candidate[0] < best[0] - 1e-12 or (
                    abs(candidate[0] - best[0]) < 1e-12 and k < best[1]
                ):
                    best = candidate
            now[j] = best
        states.append(now)

    last_idx = min(states[-1], key=lambda j: (states[-1][j][0], j))
    chosen = [None] * len(events)
    transitions = [None] * len(events)
    idx = last_idx
    for i in range(len(events) - 1, -1, -1):
        chosen[i] = deepcopy(candidate_sets[i][idx])
        total, prev_idx, detail = states[i][idx]
        chosen[i]["path_cost"] = round(float(total), 6)
        if i > 0:
            transitions[i] = detail
        idx = prev_idx if prev_idx is not None else 0
    transitions[0] = {
        "string_crossing": 0,
        "position_shift": 0,
        "transition_seconds": 0.0,
        "score": 0.0,
    }
    return chosen, transitions


def _articulation(ev: dict) -> str:
    perf = ev.get("performance", {}) if isinstance(ev.get("performance"), dict) else {}
    return str(perf.get("articulation", "neutral"))




def _s13_technique(ev: dict, left_hand: dict) -> dict | None:
    """Return deterministic technique metadata for S13 special articulations.

    MIDI remains the sounding pitch. Harmonic metadata describes a plausible
    natural harmonic when one is near the authored pitch; otherwise an
    artificial fourth-touch harmonic is used where physically plausible.
    """
    art = _articulation(ev)
    if art == "pizzicato":
        return {
            "mode": "pizzicato",
            "right_hand": "finger_pluck",
            "bow_contact": False,
        }
    if art == "spiccato":
        return {
            "mode": "spiccato",
            "right_hand": "bouncing_bow",
            "bow_contact": "intermittent",
        }
    if art != "harmonic":
        return None

    midi = int(ev["midi"])
    natural = []
    for string_index, (name, open_midi, _max_offset) in enumerate(STRINGS):
        for partial in (2, 3, 4, 5, 6):
            sounding = open_midi + 12.0 * math.log2(partial)
            error = abs(float(midi) - sounding)
            if error <= 0.35:
                natural.append((error, string_index, name, open_midi, partial, sounding))
    if natural:
        error, string_index, name, open_midi, partial, sounding = min(natural)
        return {
            "mode": "harmonic",
            "harmonic_type": "natural",
            "string": name,
            "string_index": string_index,
            "open_midi": open_midi,
            "partial": partial,
            "touch_fraction": round(1.0 / partial, 6),
            "sounding_midi": midi,
            "tuning_error_semitones": round(float(midi) - sounding, 6),
        }

    fundamental = midi - 24
    if fundamental >= 55:
        candidates = fingering_candidates(fundamental)
        if candidates:
            base = candidates[0]
            return {
                "mode": "harmonic",
                "harmonic_type": "artificial_fourth",
                "fundamental_midi": fundamental,
                "touch_midi": fundamental + 5,
                "sounding_midi": midi,
                "string": base["string"],
                "string_index": base["string_index"],
                "base_position": base["position"],
            }
    return {
        "mode": "harmonic",
        "harmonic_type": "modeled_sounding_pitch",
        "sounding_midi": midi,
        "string": left_hand.get("string"),
        "string_index": left_hand.get("string_index"),
    }


def _bow_groups(events: list[dict], bpm: float, cfg: dict) -> list[list[int]]:
    beat_s = 60.0 / float(bpm)
    groups: list[list[int]] = []
    for i, ev in enumerate(events):
        if not groups:
            groups.append([i])
            continue
        prev_i = groups[-1][-1]
        prev = events[prev_i]
        gap = float(ev["start_beat"]) - (
            float(prev["start_beat"]) + float(prev["duration_beats"])
        )
        group_start = float(events[groups[-1][0]]["start_beat"])
        group_end = max(
            float(x["start_beat"]) + float(x["duration_beats"])
            for x in (events[j] for j in groups[-1] + [i])
        )
        duration_s = (group_end - group_start) * beat_s
        can_legato = (
            _articulation(prev) == "legato"
            and _articulation(ev) == "legato"
            and gap <= cfg["legato_gap_beats"] + 1e-9
            and duration_s <= cfg["max_bow_duration_s"] + 1e-9
        )
        if can_legato:
            groups[-1].append(i)
        else:
            groups.append([i])
    return groups


def _apply_bowing(events: list[dict], groups: list[list[int]], bpm: float, cfg: dict) -> list[dict]:
    beat_s = 60.0 / float(bpm)
    out = [None] * len(events)
    prev_direction = None
    prev_group_end = None
    for gidx, members in enumerate(groups):
        gstart = float(events[members[0]]["start_beat"])
        gend = max(float(events[j]["start_beat"]) + float(events[j]["duration_beats"]) for j in members)
        gap_beats = 0.0 if prev_group_end is None else max(0.0, gstart - prev_group_end)
        retake = bool(
            cfg.get("enable_bow_retakes", False)
            and prev_direction is not None
            and gap_beats + 1e-9 >= float(cfg.get("bow_retake_gap_beats", .18))
        )
        if prev_direction is None:
            direction = "down"
        elif retake:
            direction = prev_direction
        else:
            direction = "up" if prev_direction == "down" else "down"
        duration_s = max(.01, (gend - gstart) * beat_s)
        use = _clamp(duration_s / cfg["max_bow_duration_s"], .16, .92)
        bow_start = .94 if direction == "down" else .06
        bow_end = bow_start - use if direction == "down" else bow_start + use
        bow_end = _clamp(bow_end, .02, .98)
        span = bow_end - bow_start
        for local_idx, event_index in enumerate(members):
            ev = events[event_index]
            e0 = max(0.0, (float(ev["start_beat"]) - gstart) / max(1e-9, gend - gstart))
            e1 = max(e0, min(1.0, (
                float(ev["start_beat"]) + float(ev["duration_beats"]) - gstart
            ) / max(1e-9, gend - gstart)))
            velocity = _clamp(ev.get("velocity", .7), .01, 1.0)
            normalized_speed = _clamp(.30 + .40 * velocity + .10 * min(1.0, use), .20, .90)
            normalized_force = _clamp(.26 + .48 * velocity, .20, .88)
            item = {
                "group_id": f"bow-{gidx+1:03d}",
                "direction": direction,
                "group_note_index": local_idx,
                "group_note_count": len(members),
                "bow_start": round(bow_start + span * e0, 6),
                "bow_end": round(bow_start + span * e1, 6),
                "usage_fraction": round(use * max(0.0, e1 - e0), 6),
                "force_curve": [[0.0, round(normalized_force, 6)], [1.0, round(normalized_force, 6)]],
                "speed_curve": [[0.0, round(normalized_speed, 6)], [1.0, round(normalized_speed, 6)]],
            }
            if cfg.get("enable_bow_retakes", False):
                item["retake"] = bool(retake)
                item["preceding_gap_beats"] = round(float(gap_beats), 6)
            if cfg["default_contact_point"] is not None:
                item["contact_point_curve"] = [
                    [0.0, round(cfg["default_contact_point"], 6)],
                    [1.0, round(cfg["default_contact_point"], 6)],
                ]
            out[event_index] = item
        prev_direction = direction
        prev_group_end = gend
    return out


def plan_violin_track(events: list[dict], *, bpm: float, config: dict | None = None) -> dict:
    cfg = _merge_config(config)
    pitched_probe = [e for e in events if e.get("event_type") != "drum" and "midi" in e]
    starts = [round(float(e.get("start_beat", 0)), 9) for e in pitched_probe]
    if len(starts) != len(set(starts)):
        from .violin_double_stop import ViolinDoubleStopError, plan_double_stop_track
        try:
            return plan_double_stop_track(events, bpm=bpm, cfg=cfg)
        except ViolinDoubleStopError as exc:
            raise ViolinPerformanceError(str(exc)) from exc
    pitched = _prepare_events(events)
    if not pitched:
        return {
            "version": "1.0",
            "events": [],
            "playability": {"classification": "empty", "max_transition_score": 0.0, "warning_count": 0, "warnings": []},
            "config": cfg,
        }
    chosen, transitions = _choose_fingerings(pitched, bpm, cfg)
    groups = _bow_groups(pitched, bpm, cfg)
    bowing = _apply_bowing(pitched, groups, bpm, cfg)

    planned = []
    warnings = []
    max_score = 0.0
    for i, (ev, fingering, transition, bow) in enumerate(zip(pitched, chosen, transitions, bowing)):
        score = float(transition["score"])
        max_score = max(max_score, score)
        if score > cfg["comfortable_transition_score"]:
            warnings.append({
                "event_index": i,
                "type": "transition_difficulty",
                "score": round(score, 6),
                "midi": int(ev["midi"]),
            })
        item = {
            "event_index": i,
            "midi": int(ev["midi"]),
            "start_beat": float(ev["start_beat"]),
            "duration_beats": float(ev["duration_beats"]),
            "left_hand": fingering,
            "transition": transition,
            "bow": bow,
        }
        technique = _s13_technique(ev, fingering)
        if technique is not None:
            item["technique"] = technique
        planned.append(item)

    if max_score <= cfg["comfortable_transition_score"]:
        classification = "comfortable"
    elif max_score <= cfg["challenging_transition_score"]:
        classification = "challenging"
    else:
        classification = "impractical"
    if cfg["strict_comfort"] and classification != "comfortable":
        raise ViolinPerformanceError(
            f"violin line is {classification}; max transition score {max_score:.3f} exceeds comfortable threshold {cfg['comfortable_transition_score']:.3f}"
        )
    return {
        "version": "1.0",
        "events": planned,
        "playability": {
            "classification": classification,
            "max_transition_score": round(max_score, 6),
            "warning_count": len(warnings),
            "warnings": warnings,
        },
        "config": cfg,
    }


def _prepare_ir(ir: dict) -> dict:
    validate_ir(ir)
    validate_runtime_extensions(ir)
    out = deepcopy(ir)
    if out.get("arrangement") and not out.get("arrangement_resolved"):
        out = arrange_ir(out)
    out = resolve_ir(out)
    if out.get("performance_ir") and not out.get("performance_resolved"):
        out = realize_performance_ir(out)
    return out


def realize_violin_performance(
    ir: dict,
    track_id: str,
    *,
    config: dict | None = None,
) -> dict:
    """Attach violin physical realization to one resolved bowed-string track.

    The planner adds mechanical realization only. It does not invent melodies,
    rhythms, vibrato style, or a factory sound. Existing authored instrument
    expression is preserved; bow force/speed are filled only when absent.
    """
    out = _prepare_ir(ir)
    track = next((t for t in out.get("tracks", []) if t.get("id") == track_id), None)
    if track is None:
        raise ViolinPerformanceError(f"track not found: {track_id}")
    instrument_id = track.get("instrument")
    patch = out.get("instruments", {}).get(instrument_id)
    if not isinstance(patch, dict):
        raise ViolinPerformanceError(f"track {track_id} has no valid instrument patch")
    engine = engine_for_patch(patch)
    if engine.name not in {"bowed_string", "bowed_waveguide"} or patch.get("family") != "violin":
        raise ViolinPerformanceError(
            f"track {track_id} must use a supported bowed violin engine with family=violin"
        )

    effective_config = deepcopy(config) if isinstance(config, dict) else {}
    realism = patch.get("bowed_waveguide_graph", {}).get("realism_hardening", {}) if isinstance(patch.get("bowed_waveguide_graph"), dict) else {}
    if isinstance(realism, dict) and bool(realism.get("enabled", False)):
        effective_config.setdefault("enable_bow_retakes", True)
        effective_config.setdefault("bow_retake_gap_beats", float(realism.get("bow_retake_gap_beats", .18)))
    plan = plan_violin_track(
        track.get("events", []),
        bpm=float(out["transport"]["bpm"]),
        config=effective_config if effective_config else None,
    )
    plan_by_key = {
        (round(float(x["start_beat"]), 9), int(x["midi"])): x
        for x in plan["events"]
    }
    realized_count = 0
    for ev in track.get("events", []):
        if ev.get("event_type") == "drum" or "midi" not in ev:
            continue
        key = (round(float(ev["start_beat"]), 9), int(ev["midi"]))
        item = plan_by_key.get(key)
        if item is None:
            raise ViolinPerformanceError(f"internal violin-plan mismatch at {key}")
        perf = ev.get("performance") if isinstance(ev.get("performance"), dict) else {}
        perf = deepcopy(perf)
        expr = perf.get("instrument_expression") if isinstance(perf.get("instrument_expression"), dict) else {}
        expr = deepcopy(expr)
        force = float(item["bow"]["force_curve"][0][1])
        speed = float(item["bow"]["speed_curve"][0][1])
        expr.setdefault("bow_pressure", force)
        expr.setdefault("bow_speed", speed)
        if "contact_point_curve" in item["bow"]:
            expr.setdefault("bow_position", float(item["bow"]["contact_point_curve"][0][1]))
        perf["instrument_expression"] = expr
        realization = {
            "left_hand": deepcopy(item["left_hand"]),
            "transition": deepcopy(item["transition"]),
            "bow": deepcopy(item["bow"]),
        }
        for extra_key in ("gesture_id", "gesture_type", "double_stop", "technique"):
            if extra_key in item:
                realization[extra_key] = deepcopy(item[extra_key])
        perf["violin_realization"] = realization
        ev["performance"] = perf
        realized_count += 1

    out["violin_performance_resolved"] = True
    out["violin_performance_report"] = {
        "version": "1.0",
        "track_id": track_id,
        "instrument_id": instrument_id,
        "family": "violin",
        "event_count": realized_count,
        "playability": deepcopy(plan["playability"]),
        "config": deepcopy(plan["config"]),
        "events": deepcopy(plan["events"]),
        "scope": {
            "monophonic_only": False,
            "double_stops": "synchronous_adjacent_strings",
            "harmonics": "natural-or-artificial-sounding-pitch",
            "pizzicato": True,
            "spiccato": True,
            "scordatura": False,
            "musicxml": False,
        },
    }
    return out


__all__ = [
    "ViolinPerformanceError",
    "STRINGS",
    "DEFAULT_VIOLIN_CONFIG",
    "fingering_candidates",
    "plan_violin_track",
    "realize_violin_performance",
]
