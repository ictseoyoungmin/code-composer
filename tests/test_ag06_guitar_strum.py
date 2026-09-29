from copy import deepcopy

import numpy as np
import pytest

from code_composer.core.song import song_fingerprint
from code_composer.execution import (
    PerformanceBridgeError,
    compile_performance_score_to_render_ir,
    lower_song_to_execution_plan,
    realize_instrument_mechanics,
)
from code_composer.render import _guitar_events_with_strum_gesture


VOICINGS = {
    "C": [(48,5,3),(52,4,2),(55,3,0),(60,2,1),(64,1,0)],
    "F": [(41,6,1),(48,5,3),(53,4,3),(57,3,2),(60,2,1),(65,1,1)],
    "G": [(43,6,3),(47,5,2),(50,4,0),(55,3,0),(59,2,0),(67,1,3)],
    "Am": [(45,5,0),(52,4,2),(57,3,2),(60,2,1),(64,1,0)],
}


def _song():
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG06 Strum", "global_seed": 71},
        "transport": {"bpm": 96, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
        "tonal": {"root": "C", "scale": "major"},
        "sections": [{"id": "a", "bars": 1}],
        "instruments": [{
            "id": "guitar",
            "family": "acoustic_guitar",
            "variant": "steel-string",
            "render_lock": {
                "preset": "acoustic_guitar.steel_single_string",
                "preset_version": "1.0.0",
            },
        }],
        "tracks": [{"id": "g", "function": "strum", "instrument": "guitar"}],
        "materials": [{"id": "m", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": "part", "section": "a", "track": "g", "material": "m"}],
    }


def _common(stroke_id="s1", direction="down", traversal_ms=34.0, **overrides):
    cfg = {
        "stroke_id": stroke_id,
        "direction": direction,
        "traversal_ms": traversal_ms,
        "entry_strength": 0.62,
        "acceleration": 0.10,
        "pick_depth": 0.58,
        "attack_angle_deg": 42.0,
        "follow_through": 0.72,
        "accent_position": 0.50,
        "accent_amount": 0.0,
        "from_string": 6 if direction == "down" else 1,
        "to_string": 1 if direction == "down" else 6,
    }
    cfg.update(overrides)
    return cfg


def _chord(
    name,
    *,
    stroke_id="s1",
    direction="down",
    traversal_ms=34.0,
    method="pick",
    common_overrides=None,
    muted_strings=(),
):
    cfg = _common(
        stroke_id=stroke_id,
        direction=direction,
        traversal_ms=traversal_ms,
        **(common_overrides or {}),
    )
    events = []
    for i, (midi, string, fret) in enumerate(VOICINGS[name]):
        strum = dict(cfg)
        strum["state"] = "muted" if string in set(muted_strings) else "sounding"
        perf = {
            "string": string,
            "fret": fret,
            "right_hand": {"method": method},
            "strum": strum,
        }
        if string in set(muted_strings):
            perf["left_hand"] = {"technique": "dead_note"}
        events.append({
            "id": f"{stroke_id}_{i}",
            "type": "note",
            "start_beat": 0.0,
            "duration_beats": 1.25,
            "midi": midi,
            "velocity": 0.65,
            "instrument_performance": perf,
        })
    return events


def _score(events):
    song = _song()
    return song, {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(song),
        },
        "meta": {"title": "AG06 Strum"},
        "tracks": [{"id": "g", "events": deepcopy(events)}],
        "render": {
            "sample_rate": 24000,
            "tail_seconds": 0.1,
            "mix": {
                "tracks": [{"track": "g", "gain": 0.35, "pan": 0.0, "reverb_send": 0.0}],
                "music_bus_gain": 1.0,
                "room_return_gain": 0.0,
                "master_gain": 0.8,
            },
        },
    }


def _realized(events):
    song, score = _score(events)
    plan = lower_song_to_execution_plan(song)
    ir = compile_performance_score_to_render_ir(plan, score)
    return realize_instrument_mechanics(ir, plan)


def _stroke(out, stroke_id):
    return out["guitar_performance_report"]["tracks"]["g"]["strum_strokes"][stroke_id]


def test_real_voicings_preserve_authored_pitch_string_fret_and_nominal_onset():
    for name in ("C", "F", "G", "Am"):
        authored = _chord(name, stroke_id=name)
        out = _realized(authored)
        events = out["tracks"][0]["events"]
        got = [
            (
                e["midi"],
                e["performance"]["guitar_realization"]["string"],
                e["performance"]["guitar_realization"]["fret"],
                e["start_beat"],
                e["velocity"],
            )
            for e in events
        ]
        expected = [
            (midi, string, fret, 0.0, 0.65)
            for midi, string, fret in VOICINGS[name]
        ]
        assert got == expected


def test_down_and_up_reverse_contact_order_and_are_not_force_mirrors_only():
    down = _stroke(_realized(_chord("F", stroke_id="d", direction="down")), "d")
    up = _stroke(_realized(_chord("F", stroke_id="u", direction="up")), "u")

    assert [r["string"] for r in down["profile"]] == [6,5,4,3,2,1]
    assert [r["string"] for r in up["profile"]] == [1,2,3,4,5,6]
    assert down["profile"][0]["offset_ms"] == pytest.approx(0.0)
    assert up["profile"][0]["offset_ms"] == pytest.approx(0.0)

    down_by_string = {r["string"]: r["force"] for r in down["profile"]}
    up_by_string = {r["string"]: r["force"] for r in up["profile"]}
    # Direction changes hand geometry as well as traversal order.
    assert any(abs(down_by_string[s] - up_by_string[s]) > 1e-4 for s in range(1,7))


def test_per_string_force_is_correlated_deterministic_and_nonuniform():
    a = _stroke(_realized(_chord("F", stroke_id="x")), "x")
    b = _stroke(_realized(_chord("F", stroke_id="x")), "x")

    assert a["profile"] == b["profile"]
    assert a["random_humanize"] is False
    assert a["profile_authority"] == "deterministic_shared_gesture"
    forces = [row["force"] for row in a["profile"]]
    assert max(forces) - min(forces) > 0.01
    assert len({round(x, 6) for x in forces}) > 2


def test_slow_rake_changes_both_spacing_and_force_distribution():
    fast = _stroke(
        _realized(_chord("F", stroke_id="fast", traversal_ms=22.0)),
        "fast",
    )
    slow = _stroke(
        _realized(_chord("F", stroke_id="slow", traversal_ms=96.0)),
        "slow",
    )
    assert fast["profile"][-1]["offset_ms"] == pytest.approx(22.0)
    assert slow["profile"][-1]["offset_ms"] == pytest.approx(96.0)

    fast_forces = [r["force"] for r in fast["profile"]]
    slow_forces = [r["force"] for r in slow["profile"]]
    assert any(abs(a-b) > 1e-3 for a,b in zip(fast_forces, slow_forces))


def test_accent_is_local_not_uniform_scale():
    plain = _stroke(
        _realized(_chord("F", stroke_id="p", common_overrides={"accent_amount": 0.0})),
        "p",
    )
    accented = _stroke(
        _realized(_chord(
            "F",
            stroke_id="a",
            common_overrides={"accent_position": 0.60, "accent_amount": 0.40},
        )),
        "a",
    )
    p = np.array([r["force"] for r in plain["profile"]])
    a = np.array([r["force"] for r in accented["profile"]])
    ratio = a / p
    assert np.ptp(ratio) > 0.08
    assert int(np.argmax(ratio)) in {2,3,4}


def test_skipped_string_is_in_traversal_but_has_no_pitched_event():
    out = _realized(_chord("C", stroke_id="c", direction="down"))
    stroke = _stroke(out, "c")
    assert stroke["traversal_strings"] == [6,5,4,3,2,1]
    assert stroke["skipped_strings"] == [6]
    assert stroke["profile"][0]["string"] == 5
    assert stroke["profile"][0]["offset_ms"] > 0.0


def test_muted_string_requires_upstream_left_hand_mute():
    events = _chord("F", stroke_id="m", muted_strings=(6,))
    out = _realized(events)
    assert _stroke(out, "m")["muted_strings"] == [6]

    broken = _chord("F", stroke_id="bad", muted_strings=(6,))
    broken[0]["instrument_performance"].pop("left_hand")
    with pytest.raises(PerformanceBridgeError, match="requires AG04"):
        _realized(broken)


def test_strum_and_arpeggio_cannot_own_same_note():
    events = _chord("C", stroke_id="bad")
    events[0]["instrument_performance"]["arpeggio"] = {
        "gesture_id": "arp",
        "player": "pick",
        "voice": "bass",
        "sequence_index": 0,
    }
    song, score = _score(events)
    plan = lower_song_to_execution_plan(song)
    with pytest.raises(PerformanceBridgeError, match="cannot coexist"):
        compile_performance_score_to_render_ir(plan, score)


def test_shared_stroke_state_and_nominal_onset_must_match():
    events = _chord("F", stroke_id="bad")
    events[1]["instrument_performance"]["strum"]["traversal_ms"] = 70.0
    with pytest.raises(PerformanceBridgeError, match="inconsistent shared gesture"):
        _realized(events)

    events = _chord("F", stroke_id="bad2")
    events[1]["start_beat"] = 0.01
    with pytest.raises(PerformanceBridgeError, match="one nominal authored onset"):
        _realized(events)


def test_render_local_transform_changes_only_effective_contact_state():
    out = _realized(_chord("F", stroke_id="local"))
    events = out["tracks"][0]["events"]
    canonical = [
        (e["start_beat"], e["velocity"], e["midi"])
        for e in events
    ]
    rendered = _guitar_events_with_strum_gesture(events, beat_s=60.0/96.0)

    assert canonical == [(0.0, 0.65, midi) for midi,_,_ in VOICINGS["F"]]
    effective_starts = [e["start_beat"] for e in rendered]
    effective_velocities = [e["velocity"] for e in rendered]
    assert len(set(round(x, 8) for x in effective_starts)) == 6
    assert len(set(round(x, 8) for x in effective_velocities)) > 2

    # Canonical events were not mutated by render-local preparation.
    assert [
        (e["start_beat"], e["velocity"], e["midi"])
        for e in events
    ] == canonical


def test_invalid_direction_range_and_future_field_are_hard_errors():
    events = _chord("F", stroke_id="bad", direction="down")
    for e in events:
        e["instrument_performance"]["strum"]["from_string"] = 1
        e["instrument_performance"]["strum"]["to_string"] = 6
    with pytest.raises(PerformanceBridgeError, match="downstroke"):
        _realized(events)

    events = _chord("F", stroke_id="future")
    events[0]["instrument_performance"]["strum"]["future"] = 1
    song, score = _score(events)
    plan = lower_song_to_execution_plan(song)
    with pytest.raises(PerformanceBridgeError, match="unsupported AG06"):
        compile_performance_score_to_render_ir(plan, score)
