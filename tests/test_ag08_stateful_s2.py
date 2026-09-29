from copy import deepcopy

import numpy as np

from code_composer.audio.acoustic_guitar.stateful import (
    render_stateful_acoustic_guitar_track,
)
from code_composer.audio.engines import engine_for_patch
from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files
from code_composer.presets import materialize_preset


BASE = "acoustic_guitar.steel_single_string"
S2 = "acoustic_guitar.steel_stateful_continuity"
SR = 24000
BPM = 96
BEAT_S = 60.0 / BPM


def _song(preset):
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG08 S2", "global_seed": 101},
        "transport": {"bpm": BPM, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
        "tonal": {"root": "E", "scale": "major"},
        "sections": [{"id": "a", "bars": 1}],
        "instruments": [{
            "id": "guitar",
            "family": "acoustic_guitar",
            "variant": "steel-string",
            "render_lock": {"preset": preset, "preset_version": "1.0.0"},
        }],
        "tracks": [{"id": "g", "function": "guitar", "instrument": "guitar"}],
        "materials": [{"id": "m", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": "part", "section": "a", "track": "g", "material": "m"}],
    }


def _note(eid, start, dur, midi, string, fret, method="finger"):
    return {
        "id": eid,
        "type": "note",
        "start_beat": float(start),
        "duration_beats": float(dur),
        "midi": int(midi),
        "velocity": 0.65,
        "instrument_performance": {
            "string": int(string),
            "fret": int(fret),
            "right_hand": {"method": method},
        },
    }


def _score(preset, events):
    song = _song(preset)
    return song, {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(song),
        },
        "meta": {"title": "AG08 S2"},
        "tracks": [{"id": "g", "events": deepcopy(events)}],
        "render": {
            "sample_rate": SR,
            "tail_seconds": 0.1,
            "mix": {
                "tracks": [{"track": "g", "gain": 0.32, "pan": 0.0, "reverb_send": 0.0}],
                "music_bus_gain": 1.0,
                "room_return_gain": 0.0,
                "master_gain": 0.8,
            },
        },
    }


def _render(tmp_path, preset, name, events):
    song, score = _score(preset, events)
    result = render_song_score_to_files(song, score, tmp_path / f"{name}.wav")
    return result["audio"], result["render_ir"]


def _events(ir):
    return ir["tracks"][0]["events"]


def test_s2_candidate_is_opt_in_and_only_activates_same_string_memory():
    patch = materialize_preset(S2)
    cfg = patch["acoustic_guitar_graph"]["stateful_coupling"]
    assert cfg["enabled"] is True
    assert 0.0 < cfg["same_string_memory"] <= 0.98
    assert cfg["bridge_memory"] == 0
    assert cfg["cross_string_coupling"] == 0
    assert cfg["sympathetic_gain"] == 0
    assert cfg["action_body_memory"] == 0
    assert engine_for_patch(patch).describe(patch)["track_rendering"] is True


def test_s2_is_sample_exact_for_one_isolated_note(tmp_path):
    events = [_note("e4", 0.0, 0.75, 64, 1, 0)]
    a, ir_a = _render(tmp_path, BASE, "single_a", events)
    b, ir_b = _render(tmp_path, S2, "single_b", events)
    assert np.array_equal(a, b)
    assert _events(ir_a) == _events(ir_b)


def test_s2_is_sample_exact_when_second_note_uses_different_physical_string(tmp_path):
    events = [
        _note("e4_s1", 0.0, 0.50, 64, 1, 0),
        _note("e4_s2", 0.5, 0.50, 64, 2, 5),
    ]
    a, ir_a = _render(tmp_path, BASE, "different_a", events)
    b, ir_b = _render(tmp_path, S2, "different_b", events)
    assert np.array_equal(a, b)
    assert _events(ir_a) == _events(ir_b)


def test_s2_reuses_same_string_residual_without_changing_authored_events(tmp_path):
    events = [
        _note("e4_1", 0.0, 0.50, 64, 1, 0),
        _note("e4_2", 0.5, 0.50, 64, 1, 0),
    ]
    a, ir_a = _render(tmp_path, BASE, "same_a", events)
    b, ir_b = _render(tmp_path, S2, "same_b", events)

    second = int(0.5 * BEAT_S * SR)
    assert np.array_equal(a[:second], b[:second])
    assert not np.array_equal(a[second:], b[second:])
    delta = b[second:] - a[second:]
    ratio = float(np.sqrt(np.mean(delta * delta))) / (
        float(np.sqrt(np.mean(a[second:] * a[second:]))) + 1e-12
    )
    assert 0.01 < ratio < 0.75
    assert _events(ir_a) == _events(ir_b)
    assert float(np.max(np.abs(b))) < 0.98


def test_s2_same_string_fret_change_keeps_boundary_finite_and_deterministic(tmp_path):
    events = [
        _note("d4", 0.0, 0.50, 62, 2, 3),
        _note("e4", 0.5, 0.50, 64, 2, 5),
    ]
    b1, ir1 = _render(tmp_path, S2, "fret_b1", events)
    b2, ir2 = _render(tmp_path, S2, "fret_b2", events)
    assert np.array_equal(b1, b2)
    assert _events(ir1) == _events(ir2)

    second = int(0.5 * BEAT_S * SR)
    mono = 0.5 * (b1[:, 0] + b1[:, 1])
    step = abs(float(mono[second] - mono[second - 1]))
    assert step < 0.25


def test_s2_delegates_tracks_with_ag07_actions_until_later_slice():
    patch = materialize_preset(S2)
    events = [{
        "event_type": "instrument_action",
        "start_beat": 0.0,
        "duration_beats": 0.08,
        "action": "top_slap",
        "parameters": {"strength": 0.5, "location": "soundboard"},
    }]
    assert render_stateful_acoustic_guitar_track(
        events, 4096, SR, patch, BEAT_S
    ) is None
