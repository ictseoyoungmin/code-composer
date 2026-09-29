from copy import deepcopy
import math

import numpy as np

from code_composer.audio.acoustic_guitar.stateful import (
    _sympathetic_transfer_plan,
    initialize_acoustic_guitar_state,
)
from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files
from code_composer.presets import materialize_preset


S3 = "acoustic_guitar.steel_stateful_body"
S4 = "acoustic_guitar.steel_stateful_sympathetic"
SR = 24000
BPM = 96


def _song(preset):
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG08 S4", "global_seed": 107},
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


def _note(eid, start, dur, midi, string, fret, method="finger", velocity=0.65):
    return {
        "id": eid,
        "type": "note",
        "start_beat": float(start),
        "duration_beats": float(dur),
        "midi": int(midi),
        "velocity": float(velocity),
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
        "meta": {"title": "AG08 S4"},
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


def _rms(x):
    x = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(x * x))) if x.size else 0.0


def test_s4_preset_activates_bounded_cross_string_coupling():
    patch = materialize_preset(S4)
    cfg = patch["acoustic_guitar_graph"]["stateful_coupling"]
    assert cfg["enabled"] is True
    assert cfg["same_string_memory"] == 0.32
    assert cfg["bridge_memory"] == 0.46
    assert cfg["action_body_memory"] == 0.52
    assert 0.0 < cfg["cross_string_coupling"] <= 0.98
    assert 0.0 < cfg["sympathetic_gain"] <= 0.98
    assert cfg["cross_string_coupling"] * cfg["sympathetic_gain"] <= 0.12


def test_s4_transfer_plan_is_passive_and_modal_compatibility_gated():
    patch = materialize_preset(S4)
    graph = patch["acoustic_guitar_graph"]
    cfg = graph["stateful_coupling"]
    state = initialize_acoustic_guitar_state(SR, graph)

    compatible = _sympathetic_transfer_plan(
        64, 0, state, SR, graph,
        cfg["cross_string_coupling"], cfg["sympathetic_gain"],
    )
    incompatible = _sympathetic_transfer_plan(
        65, 0, state, SR, graph,
        cfg["cross_string_coupling"], cfg["sympathetic_gain"],
    )

    assert compatible
    assert incompatible == []
    assert all(item["target_idx"] != 0 for item in compatible)
    assert any(item["target_idx"] == 5 for item in compatible)  # low E string
    eta = sum(item["eta"] for item in compatible)
    assert 0.0 < eta <= 0.12
    assert eta <= cfg["cross_string_coupling"] * cfg["sympathetic_gain"] + 1e-12
    source_keep = math.sqrt(1.0 - eta)
    assert source_keep * source_keep + eta <= 1.0 + 1e-12


def test_s4_incompatible_f4_is_sample_exact_with_s3(tmp_path):
    events = [_note("f4", 0.0, 0.70, 65, 1, 1)]
    a, ir_a = _render(tmp_path, S3, "f4_s3", events)
    b, ir_b = _render(tmp_path, S4, "f4_s4", events)
    assert np.array_equal(a, b)
    assert _events(ir_a) == _events(ir_b)


def test_s4_fully_authored_six_string_chord_does_not_double_excitation(tmp_path):
    events = [
        _note("s1", 0.0, 0.70, 64, 1, 0),
        _note("s2", 0.0, 0.70, 59, 2, 0),
        _note("s3", 0.0, 0.70, 56, 3, 1),
        _note("s4", 0.0, 0.70, 52, 4, 2),
        _note("s5", 0.0, 0.70, 47, 5, 2),
        _note("s6", 0.0, 0.70, 40, 6, 0),
    ]
    a, ir_a = _render(tmp_path, S3, "chord_s3", events)
    b, ir_b = _render(tmp_path, S4, "chord_s4", events)
    assert np.array_equal(a, b)
    assert _events(ir_a) == _events(ir_b)


def test_s4_compatible_e4_transfers_state_without_hidden_note(tmp_path):
    events = [_note("e4", 0.0, 0.70, 64, 1, 0)]
    a, ir_a = _render(tmp_path, S3, "e4_s3", events)
    b1, ir_b1 = _render(tmp_path, S4, "e4_s4_1", events)
    b2, ir_b2 = _render(tmp_path, S4, "e4_s4_2", events)

    assert not np.array_equal(a, b1)
    assert np.array_equal(b1, b2)
    assert _events(ir_a) == _events(ir_b1) == _events(ir_b2)
    assert len(_events(ir_b1)) == 1

    delta_ratio = _rms(b1 - a) / (_rms(a) + 1e-12)
    assert 0.001 < delta_ratio < 0.45
    assert float(np.max(np.abs(b1))) < 0.98
