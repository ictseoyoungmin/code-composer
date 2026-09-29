from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from code_composer.audio.acoustic_guitar import render_acoustic_guitar_action
from code_composer.audio.engines import engine_for_patch
from code_composer.core.song import song_fingerprint
from code_composer.execution import (
    PerformanceBridgeError,
    compile_performance_score_to_render_ir,
    lower_song_to_execution_plan,
    realize_instrument_mechanics,
)
from code_composer.presets import materialize_preset
from code_composer.render import render


ACTIONS = (
    "body_tap",
    "top_slap",
    "bridge_hit",
    "string_slap",
    "muted_strum",
    "dead_strum",
    "nail_click",
)


def _song():
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG07 Percussive Guitar", "global_seed": 79},
        "transport": {"bpm": 96, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
        "tonal": {"root": "E", "scale": "minor"},
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
        "tracks": [{"id": "g", "function": "percussive-fingerstyle", "instrument": "guitar"}],
        "materials": [{"id": "m", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": "part", "section": "a", "track": "g", "material": "m"}],
    }


def _note(eid="n", start=0.0, midi=52):
    return {
        "id": eid,
        "type": "note",
        "start_beat": float(start),
        "duration_beats": 0.9,
        "midi": int(midi),
        "velocity": 0.62,
        "instrument_performance": {
            "string": 4,
            "fret": 2,
            "right_hand": {"method": "thumb"},
        },
    }


def _action(eid, action, start=0.0, **params):
    return {
        "id": eid,
        "type": "instrument_action",
        "start_beat": float(start),
        "duration_beats": 0.08,
        "action": action,
        "parameters": params or {"strength": 0.68},
    }


def _score(events, preset="acoustic_guitar.steel_single_string"):
    song = _song()
    song["instruments"][0]["render_lock"]["preset"] = preset
    return song, {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(song),
        },
        "meta": {"title": "AG07 Percussive Guitar"},
        "tracks": [{"id": "g", "events": deepcopy(events)}],
        "render": {
            "sample_rate": 24000,
            "tail_seconds": 0.1,
            "mix": {
                "tracks": [{"track": "g", "gain": 0.42, "pan": 0.0, "reverb_send": 0.0}],
                "music_bus_gain": 1.0,
                "room_return_gain": 0.0,
                "master_gain": 0.8,
            },
        },
    }


def _compiled(events, preset="acoustic_guitar.steel_single_string"):
    song, score = _score(events, preset=preset)
    plan = lower_song_to_execution_plan(song)
    ir = compile_performance_score_to_render_ir(plan, score)
    return plan, ir


def _rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, dtype=np.float64) ** 2)) + 1e-12)


def test_canonical_patch_advertises_actions_but_foundation_does_not():
    canonical = materialize_preset("acoustic_guitar.steel_single_string")
    foundation = materialize_preset("acoustic_guitar.steel_foundation")
    assert engine_for_patch(canonical).describe(canonical)["instrument_actions"] is True
    assert engine_for_patch(foundation).describe(foundation)["instrument_actions"] is False


@pytest.mark.parametrize("action", ACTIONS)
def test_all_ag07_actions_compile_on_canonical_patch(action):
    params = {"strength": 0.68}
    if action in {"muted_strum", "dead_strum"}:
        params.update({"direction": "down", "traversal_ms": 34.0, "string_count": 6})
    _, ir = _compiled([_action("a", action, **params)])
    event = ir["tracks"][0]["events"][0]
    assert event["event_type"] == "instrument_action"
    assert event["action"] == action
    assert event["start_beat"] == 0.0


def test_foundation_patch_rejects_ag07_action():
    with pytest.raises(PerformanceBridgeError, match="does not support instrument_action"):
        _compiled(
            [_action("a", "body_tap", strength=0.6)],
            preset="acoustic_guitar.steel_foundation",
        )


@pytest.mark.parametrize("action", ACTIONS)
def test_actions_are_deterministic_and_headroom_safe(action):
    patch = materialize_preset("acoustic_guitar.steel_single_string")
    params = {"strength": 0.68}
    if action in {"muted_strum", "dead_strum"}:
        params.update({"direction": "down", "traversal_ms": 34.0, "string_count": 6})
    a = render_acoustic_guitar_action(
        action, 0.05, 24000, patch, parameters=params, seed=1234
    )
    b = render_acoustic_guitar_action(
        action, 0.05, 24000, patch, parameters=params, seed=1234
    )
    assert np.array_equal(a, b)
    assert _rms(a) > 1e-5
    assert float(np.max(np.abs(a))) < 0.98


def test_contact_locations_are_distinct_but_share_same_body_path():
    patch = materialize_preset("acoustic_guitar.steel_single_string")
    rendered = {}
    for location in ("lower_bout", "upper_bout", "soundboard", "bridge"):
        rendered[location] = render_acoustic_guitar_action(
            "body_tap",
            0.05,
            24000,
            patch,
            parameters={"strength": 0.65, "location": location},
            seed=222,
        )
    for a, b in (
        ("lower_bout", "upper_bout"),
        ("lower_bout", "bridge"),
        ("soundboard", "bridge"),
    ):
        assert not np.array_equal(rendered[a], rendered[b])
        ratio = _rms(rendered[a]) / _rms(rendered[b])
        assert 0.20 < ratio < 5.0


def test_muted_and_dead_strum_direction_and_character_are_distinct():
    patch = materialize_preset("acoustic_guitar.steel_single_string")
    down = render_acoustic_guitar_action(
        "muted_strum",
        0.06,
        24000,
        patch,
        parameters={"strength": 0.68, "direction": "down", "traversal_ms": 42, "string_count": 6},
        seed=333,
    )
    up = render_acoustic_guitar_action(
        "muted_strum",
        0.06,
        24000,
        patch,
        parameters={"strength": 0.68, "direction": "up", "traversal_ms": 42, "string_count": 6},
        seed=333,
    )
    dead = render_acoustic_guitar_action(
        "dead_strum",
        0.06,
        24000,
        patch,
        parameters={"strength": 0.68, "direction": "down", "traversal_ms": 42, "string_count": 6},
        seed=333,
    )
    assert not np.array_equal(down, up)
    assert not np.array_equal(down, dead)


def test_note_and_body_action_can_share_onset_without_note_rewrite():
    plan, ir = _compiled([
        _note("bass", 0.0, 52),
        _action("slap", "top_slap", 0.0, strength=0.60, location="soundboard"),
    ])
    realized = realize_instrument_mechanics(ir, plan)
    note = next(e for e in realized["tracks"][0]["events"] if "midi" in e)
    action = next(e for e in realized["tracks"][0]["events"] if e.get("event_type") == "instrument_action")
    assert note["midi"] == 52
    assert note["start_beat"] == 0.0
    assert note["duration_beats"] == 0.9
    assert action["start_beat"] == 0.0
    assert action["action"] == "top_slap"


def test_actual_renderer_combines_note_and_action_without_dropping_either(tmp_path):
    plan, ir = _compiled([
        _note("bass", 0.0, 52),
        _action("slap", "top_slap", 0.0, strength=0.60, location="soundboard"),
    ])
    realized = realize_instrument_mechanics(ir, plan)
    out = tmp_path / "combined.wav"
    audio, sr, _ = render(realized, str(out))
    assert sr == 24000
    assert out.exists()
    assert _rms(audio) > 1e-4
    assert float(np.max(np.abs(audio))) < 0.98


def test_invalid_action_and_parameters_fail_loudly():
    with pytest.raises(PerformanceBridgeError, match="unsupported AG07"):
        _compiled([_action("a", "kick", strength=0.7)])

    with pytest.raises(PerformanceBridgeError, match="location unsupported"):
        _compiled([_action("a", "body_tap", strength=0.7, location="neck_joint")])

    with pytest.raises(PerformanceBridgeError, match="does not accept"):
        _compiled([_action("a", "body_tap", direction="down")])

    with pytest.raises(PerformanceBridgeError, match="string_count"):
        _compiled([_action(
            "a", "dead_strum",
            strength=0.7, direction="down", traversal_ms=32.0, string_count=1
        )])
