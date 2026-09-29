from copy import deepcopy

import numpy as np
import pytest

from code_composer.audio.acoustic_guitar import render_acoustic_guitar_note
from code_composer.core.song import song_fingerprint
from code_composer.execution import (
    PerformanceBridgeError,
    compile_performance_score_to_render_ir,
    lower_song_to_execution_plan,
    realize_instrument_mechanics,
)
from code_composer.presets import materialize_preset


def _song():
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG05 Arpeggio", "global_seed": 59},
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
        "tracks": [{"id": "g", "function": "fingerstyle", "instrument": "guitar"}],
        "materials": [{"id": "m", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": "part", "section": "a", "track": "g", "material": "m"}],
    }


def _note(
    event_id,
    start,
    duration,
    midi,
    string,
    fret,
    *,
    right_method,
    gesture=None,
    player=None,
    voice=None,
    sequence_index=None,
):
    perf = {
        "string": int(string),
        "fret": int(fret),
        "right_hand": {"method": right_method},
    }
    if gesture is not None:
        perf["arpeggio"] = {
            "gesture_id": gesture,
            "player": player,
            "voice": voice,
            "sequence_index": sequence_index,
        }
    return {
        "id": event_id,
        "type": "note",
        "start_beat": float(start),
        "duration_beats": float(duration),
        "midi": int(midi),
        "velocity": 0.65,
        "instrument_performance": perf,
    }


def _c_fingerstyle(gesture="c1"):
    return [
        _note("c0", 0.00, 1.50, 48, 5, 3, right_method="thumb", gesture=gesture, player="thumb", voice="bass", sequence_index=0),
        _note("c1", 0.25, 1.25, 52, 4, 2, right_method="thumb", gesture=gesture, player="thumb", voice="bass", sequence_index=1),
        _note("c2", 0.50, 1.00, 55, 3, 0, right_method="finger", gesture=gesture, player="index", voice="inner", sequence_index=2),
        _note("c3", 0.75, 0.50, 60, 2, 1, right_method="finger", gesture=gesture, player="middle", voice="treble", sequence_index=3),
        _note("c4", 1.00, 0.80, 64, 1, 0, right_method="finger", gesture=gesture, player="ring", voice="treble", sequence_index=4),
        _note("c5", 1.25, 0.70, 60, 2, 1, right_method="finger", gesture=gesture, player="middle", voice="treble", sequence_index=5),
        _note("c6", 1.50, 0.80, 55, 3, 0, right_method="finger", gesture=gesture, player="index", voice="inner", sequence_index=6),
        _note("c7", 1.75, 0.80, 52, 4, 2, right_method="thumb", gesture=gesture, player="thumb", voice="bass", sequence_index=7),
    ]


def _score(events):
    song = _song()
    return song, {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(song),
        },
        "meta": {"title": "AG05 Arpeggio"},
        "tracks": [{"id": "g", "events": deepcopy(events)}],
        "render": {
            "sample_rate": 24000,
            "tail_seconds": 0.1,
            "mix": {
                "tracks": [{"track": "g", "gain": 0.55, "pan": 0.0, "reverb_send": 0.0}],
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


def _render_note(midi, performance):
    patch = materialize_preset("acoustic_guitar.steel_single_string")
    return render_acoustic_guitar_note(
        midi, 0.45, 24000, patch, velocity=0.65, performance=performance
    )


def test_fingerstyle_gesture_preserves_authored_pattern_and_reports_overlap():
    out = _realized(_c_fingerstyle())
    events = out["tracks"][0]["events"]
    before = [(e["midi"], e["start_beat"], e["duration_beats"]) for e in events]
    expected = [(e["midi"], e["start_beat"], e["duration_beats"]) for e in _c_fingerstyle()]
    assert before == expected

    report = out["guitar_performance_report"]["tracks"]["g"]
    assert report["scope"]["arpeggio_fingerstyle"] is True
    assert report["arpeggio_event_count"] == 8
    gesture = report["arpeggio_gestures"]["c1"]
    assert gesture["distinct_strings"] == [1, 2, 3, 4, 5]
    assert gesture["max_distinct_string_overlap"] >= 4
    assert gesture["bass_upper_overlap_count"] > 0
    assert gesture["pattern_authority"] == "composer_authored"
    assert gesture["players"] == [
        "thumb", "thumb", "index", "middle", "ring", "middle", "index", "thumb"
    ]


def test_picked_arpeggio_uses_explicit_pick_on_every_authored_note():
    events = []
    for ev in _c_fingerstyle("cpick"):
        item = deepcopy(ev)
        perf = item["instrument_performance"]
        perf["right_hand"] = {"method": "pick"}
        perf["arpeggio"]["player"] = "pick"
        events.append(item)
    out = _realized(events)
    report = out["guitar_performance_report"]["tracks"]["g"]["arpeggio_gestures"]["cpick"]
    assert report["players"] == ["pick"] * 8
    for ev in out["tracks"][0]["events"]:
        assert ev["performance"]["right_hand_realization"]["method"] == "pick"


def test_ag05_metadata_is_acoustically_inert_for_same_single_note_state():
    event = _c_fingerstyle()[2]
    without = deepcopy(event)
    without["instrument_performance"].pop("arpeggio")
    a = _realized([without])["tracks"][0]["events"][0]["performance"]

    # One-note AG05 gestures are intentionally invalid, so compare renderer states
    # after resolving a valid multi-note gesture.
    realized = _realized(_c_fingerstyle())
    b = realized["tracks"][0]["events"][2]["performance"]
    b_without_metadata = deepcopy(b)
    b_without_metadata.pop("arpeggio_realization")
    assert np.array_equal(
        _render_note(55, b_without_metadata),
        _render_note(55, b),
    )


@pytest.mark.parametrize(
    "player,method",
    [
        ("thumb", "finger"),
        ("index", "pick"),
        ("middle", "thumb"),
        ("ring", "pick"),
        ("pick", "finger"),
    ],
)
def test_player_and_ag03_right_hand_must_match(player, method):
    events = _c_fingerstyle()
    events[0]["instrument_performance"]["arpeggio"]["player"] = player
    events[0]["instrument_performance"]["right_hand"]["method"] = method
    with pytest.raises(PerformanceBridgeError, match="arpeggio"):
        _realized(events)


def test_sequence_index_must_follow_authored_onset_order():
    events = _c_fingerstyle()
    events[2]["instrument_performance"]["arpeggio"]["sequence_index"] = 6
    events[6]["instrument_performance"]["arpeggio"]["sequence_index"] = 2
    with pytest.raises(PerformanceBridgeError, match="sequence order"):
        _realized(events)


def test_same_string_independent_state_overlap_is_rejected():
    events = _c_fingerstyle()
    # String 3 first note now rings through the second string-3 attack.
    events[2]["duration_beats"] = 1.25
    with pytest.raises(PerformanceBridgeError, match="overlaps independent notes"):
        _realized(events)


def test_gesture_must_span_multiple_strings():
    events = [
        _note("a", 0.0, 0.25, 64, 1, 0, right_method="finger", gesture="one", player="index", voice="treble", sequence_index=0),
        _note("b", 0.3, 0.25, 64, 1, 0, right_method="finger", gesture="one", player="middle", voice="treble", sequence_index=1),
    ]
    with pytest.raises(PerformanceBridgeError, match="at least two strings"):
        _realized(events)


def test_voice_role_must_match_string_region():
    events = _c_fingerstyle()
    events[0]["instrument_performance"]["arpeggio"]["voice"] = "treble"
    with pytest.raises(PerformanceBridgeError, match="treble voice"):
        _realized(events)


def test_invalid_future_ag05_field_is_hard_error():
    events = _c_fingerstyle()
    events[0]["instrument_performance"]["arpeggio"]["future"] = 1
    song, score = _score(events)
    plan = lower_song_to_execution_plan(song)
    with pytest.raises(PerformanceBridgeError, match="unsupported AG05"):
        compile_performance_score_to_render_ir(plan, score)
