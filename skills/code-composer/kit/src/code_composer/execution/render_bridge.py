"""CR03 bridge from Execution Plan + authored Performance Score to render IR."""
from __future__ import annotations

from copy import deepcopy

from ..core.ir import validate_ir
from ..execution.plan import execution_plan_fingerprint, validate_execution_plan
from ..performance.violin import ViolinPerformanceError, realize_violin_performance
from ..validation_contracts import ContractValidationError, validate_runtime_extensions
from .performance_score import performance_score_fingerprint, validate_performance_score


class PerformanceBridgeError(ValueError):
    pass


def _timeline_end(plan: dict) -> float:
    return max(
        float(s["start_beat"]) + float(s["duration_beats"])
        for s in plan["sections"]
    )


def _section_id_at(plan: dict, beat: float) -> str:
    for section in plan["sections"]:
        start = float(section["start_beat"])
        end = start + float(section["duration_beats"])
        if start <= beat < end - 1e-12 or abs(beat - start) <= 1e-12:
            return section["id"]
    return plan["sections"][-1]["id"]


def _validate_score_against_plan(plan: dict, score: dict) -> None:
    validate_execution_plan(plan)
    validate_performance_score(score)

    if score["source_song"]["fingerprint"] != plan["source_song"]["fingerprint"]:
        raise PerformanceBridgeError("performance score source Song fingerprint does not match Execution Plan")

    plan_tracks = {x["id"]: x for x in plan["tracks"]}
    score_tracks = {x["id"]: x for x in score["tracks"]}
    if set(score_tracks) != set(plan_tracks):
        raise PerformanceBridgeError(
            f"performance score tracks must exactly match Execution Plan tracks; "
            f"score={sorted(score_tracks)} plan={sorted(plan_tracks)}"
        )

    instruments = {x["id"]: x for x in plan["instruments"]}
    end = _timeline_end(plan)

    for track_id, score_track in score_tracks.items():
        plan_track = plan_tracks[track_id]
        family = instruments[plan_track["instrument"]]["family"]
        pitched_onsets = {}
        control_ranges = []
        for event in score_track["events"]:
            start = float(event["start_beat"])
            duration = float(event["duration_beats"])
            if start + duration > end + 1e-9:
                raise PerformanceBridgeError(
                    f"track {track_id} event {event['id']} exceeds piece timeline"
                )
            if event["type"] == "sustain_pedal":
                if family != "piano":
                    raise PerformanceBridgeError(
                        f"track {track_id} sustain pedal requires piano family"
                    )
                control_ranges.append((start, start + duration, event["id"]))
                continue

            if family == "violin":
                key = round(start, 9)
                if key in pitched_onsets:
                    raise PerformanceBridgeError(
                        f"track {track_id}: CR03 violin bottleneck is monophonic; "
                        f"events {pitched_onsets[key]} and {event['id']} share onset {start:g}"
                    )
                pitched_onsets[key] = event["id"]
                if not 55 <= int(event["midi"]) <= 105:
                    raise PerformanceBridgeError(
                        f"track {track_id} event {event['id']} MIDI {event['midi']} outside violin range"
                    )

        control_ranges.sort()
        for (_, end0, id0), (start1, _, id1) in zip(control_ranges, control_ranges[1:]):
            if start1 < end0 - 1e-12:
                raise PerformanceBridgeError(
                    f"track {track_id}: sustain controls {id0} and {id1} overlap"
                )


def _legacy_event(event: dict, section_id: str) -> dict:
    if event["type"] == "sustain_pedal":
        return {
            "event_type": "piano_control",
            "control": "sustain_pedal",
            "start_beat": float(event["start_beat"]),
            "duration_beats": float(event["duration_beats"]),
            "points": deepcopy(event["points"]),
            "section_id": section_id,
        }

    perf = {}
    if "articulation" in event:
        perf["articulation"] = event["articulation"]
    if "expression" in event:
        perf["instrument_expression"] = deepcopy(event["expression"])
    if "piano_attack_offset_ms" in event:
        perf["piano_attack_offset_ms"] = float(event["piano_attack_offset_ms"])

    out = {
        "start_beat": float(event["start_beat"]),
        "duration_beats": float(event["duration_beats"]),
        "midi": int(event["midi"]),
        "velocity": float(event["velocity"]),
        "section_id": section_id,
    }
    if perf:
        out["performance"] = perf
    return out


def compile_performance_score_to_render_ir(plan: dict, score: dict) -> dict:
    _validate_score_against_plan(plan, score)

    plan_tracks = {x["id"]: x for x in plan["tracks"]}
    plan_instruments = {x["id"]: x for x in plan["instruments"]}
    score_tracks = {x["id"]: x for x in score["tracks"]}

    instruments = {
        inst_id: deepcopy(item["patch"])
        for inst_id, item in plan_instruments.items()
    }

    tracks = []
    for track_id in [x["id"] for x in plan["tracks"]]:
        plan_track = plan_tracks[track_id]
        events = []
        for event in score_tracks[track_id]["events"]:
            events.append(_legacy_event(
                event,
                _section_id_at(plan, float(event["start_beat"])),
            ))
        tracks.append({
            "id": track_id,
            "instrument": plan_track["instrument"],
            "source": {"type": "resolved"},
            "events": events,
        })

    mix_cfg = score["render"]["mix"]
    routes = {}
    for item in mix_cfg["tracks"]:
        routes[item["track"]] = {
            "gain": float(item["gain"]),
            "pan": float(item["pan"]),
            "output": "music",
            "sends": {"room": float(item["reverb_send"])},
        }

    graph = {
        "tracks": routes,
        "buses": {
            "music": {
                "kind": "group",
                "gain": float(mix_cfg["music_bus_gain"]),
                "output": "master",
                "fx": [],
            },
            "room": {
                "kind": "return",
                "gain": float(mix_cfg["room_return_gain"]),
                "output": "master",
                "fx": [{"type": "reverb", "mix": 1.0}],
            },
        },
        "sidechains": [],
        "master": {
            "gain": float(mix_cfg["master_gain"]),
            "fx": [],
        },
    }

    if "tonal" not in plan:
        raise PerformanceBridgeError("CR03 pitched piano+violin render requires tonal Execution Plan")

    ir = {
        "meta": {
            "title": score["meta"]["title"],
            "version": "cr03",
            "sample_rate": int(score["render"]["sample_rate"]),
            "global_seed": int(plan["meta"]["global_seed"]),
            "composer_provenance": {
                "song_fingerprint": plan["source_song"]["fingerprint"],
                "execution_plan_fingerprint": execution_plan_fingerprint(plan),
                "performance_score_fingerprint": performance_score_fingerprint(score),
            },
        },
        "transport": {
            "bpm": float(plan["transport"]["bpm"]),
            "beats_per_bar": int(plan["transport"]["meter"]["beats_per_bar"]),
        },
        "tonal": deepcopy(plan["tonal"]),
        "form": [
            {
                "id": s["id"],
                "start_bar": int(s["start_bar"]),
                "bars": int(s["bars"]),
                **({"energy": float(s["energy"])} if "energy" in s else {}),
            }
            for s in plan["sections"]
        ],
        "materials": {"motifs": {}, "progressions": {}, "rhythms": {}},
        "instruments": instruments,
        "tracks": tracks,
        "mix": {
            "tail_seconds": float(score["render"]["tail_seconds"]),
            "graph": graph,
        },
    }

    try:
        validate_ir(ir)
        validate_runtime_extensions(ir)
    except (ValueError, ContractValidationError) as exc:
        raise PerformanceBridgeError(str(exc)) from exc
    return ir


def realize_instrument_mechanics(ir: dict, plan: dict) -> dict:
    """Attach physical performance realization without changing authored notes."""
    out = deepcopy(ir)
    instruments = {x["id"]: x for x in plan["instruments"]}
    track_map = {x["id"]: x for x in plan["tracks"]}

    before = {
        t["id"]: [
            (float(e["start_beat"]), float(e["duration_beats"]), int(e["midi"]))
            for e in t["events"] if "midi" in e
        ]
        for t in out["tracks"]
    }

    for track_id, track in track_map.items():
        family = instruments[track["instrument"]]["family"]
        if family == "violin":
            try:
                out = realize_violin_performance(
                    out,
                    track_id,
                    config={"strict_comfort": True},
                )
            except ViolinPerformanceError as exc:
                raise PerformanceBridgeError(str(exc)) from exc

    after = {
        t["id"]: [
            (float(e["start_beat"]), float(e["duration_beats"]), int(e["midi"]))
            for e in t["events"] if "midi" in e
        ]
        for t in out["tracks"]
    }
    if before != after:
        raise PerformanceBridgeError("instrument realization changed authored note pitch/timing")
    return out


__all__ = [
    "PerformanceBridgeError",
    "compile_performance_score_to_render_ir",
    "realize_instrument_mechanics",
]
