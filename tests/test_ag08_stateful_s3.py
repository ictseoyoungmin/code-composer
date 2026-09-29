from copy import deepcopy

import numpy as np

from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files
from code_composer.presets import materialize_preset


BASE = "acoustic_guitar.steel_single_string"
S3 = "acoustic_guitar.steel_stateful_body"
SR = 24000
BPM = 96
BEAT_S = 60.0 / BPM


def _song(preset):
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG08 S3", "global_seed": 107},
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


def _action(eid, start, action, **parameters):
    return {
        "id": eid,
        "type": "instrument_action",
        "start_beat": float(start),
        "duration_beats": 0.08,
        "action": action,
        "parameters": parameters,
    }


def _score(preset, events):
    song = _song(preset)
    return song, {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(song),
        },
        "meta": {"title": "AG08 S3"},
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


def test_s3_preset_activates_only_shared_body_memory_before_s4():
    patch = materialize_preset(S3)
    cfg = patch["acoustic_guitar_graph"]["stateful_coupling"]
    assert cfg["enabled"] is True
    assert cfg["same_string_memory"] == 0.32
    assert 0.0 < cfg["bridge_memory"] <= 0.98
    assert 0.0 < cfg["action_body_memory"] <= 0.98
    assert cfg["cross_string_coupling"] == 0
    assert cfg["sympathetic_gain"] == 0


def test_s3_isolated_note_is_sample_exact_with_ag07(tmp_path):
    events = [_note("e4", 0.0, 0.75, 64, 1, 0)]
    a, ir_a = _render(tmp_path, BASE, "note_a", events)
    b, ir_b = _render(tmp_path, S3, "note_b", events)
    assert np.array_equal(a, b)
    assert _events(ir_a) == _events(ir_b)


def test_s3_isolated_action_preserves_ag07_action_identity_exactly(tmp_path):
    events = [
        _action("tap", 0.0, "body_tap", strength=0.55, location="lower_bout")
    ]
    a, ir_a = _render(tmp_path, BASE, "action_a", events)
    b, ir_b = _render(tmp_path, S3, "action_b", events)
    assert np.array_equal(a, b)
    assert _events(ir_a) == _events(ir_b)


def test_s3_simultaneous_note_action_is_exact_without_prior_body_state(tmp_path):
    events = [
        _note("bass", 0.0, 0.80, 52, 4, 2, method="thumb"),
        _action("slap", 0.0, "top_slap", strength=0.58, location="soundboard"),
    ]
    a, ir_a = _render(tmp_path, BASE, "sim_a", events)
    b, ir_b = _render(tmp_path, S3, "sim_b", events)
    assert np.array_equal(a, b)
    assert _events(ir_a) == _events(ir_b)


def test_s3_note_then_action_uses_shared_existing_body_state(tmp_path):
    events = [
        _note("e4", 0.0, 0.70, 64, 1, 0, method="finger"),
        _action("slap", 0.55, "top_slap", strength=0.54, location="soundboard"),
    ]
    a, ir_a = _render(tmp_path, BASE, "note_slap_a", events)
    b, ir_b = _render(tmp_path, S3, "note_slap_b", events)
    boundary = int(0.55 * BEAT_S * SR)

    assert np.array_equal(a[:boundary], b[:boundary])
    assert not np.array_equal(a[boundary:], b[boundary:])
    assert _events(ir_a) == _events(ir_b)

    ratio = _rms(b[boundary:] - a[boundary:]) / (_rms(a[boundary:]) + 1e-12)
    assert 0.001 < ratio < 0.40
    assert float(np.max(np.abs(b))) < 0.98


def test_s3_action_then_note_uses_same_shared_body_without_hidden_event(tmp_path):
    events = [
        _action("tap", 0.0, "body_tap", strength=0.48, location="lower_bout"),
        _note("e4", 0.20, 0.70, 64, 1, 0, method="finger"),
    ]
    a, ir_a = _render(tmp_path, BASE, "tap_note_a", events)
    b1, ir_b1 = _render(tmp_path, S3, "tap_note_b1", events)
    b2, ir_b2 = _render(tmp_path, S3, "tap_note_b2", events)
    boundary = int(0.20 * BEAT_S * SR)

    assert np.array_equal(a[:boundary], b1[:boundary])
    assert not np.array_equal(a[boundary:], b1[boundary:])
    ratio = _rms(b1[boundary:] - a[boundary:]) / (_rms(a[boundary:]) + 1e-12)
    assert 0.001 < ratio < 0.40
    assert np.array_equal(b1, b2)
    assert _events(ir_a) == _events(ir_b1) == _events(ir_b2)
    assert len(_events(ir_b1)) == 2


def test_s3_different_string_note_reexcites_body_without_cross_string_note_creation(tmp_path):
    events = [
        _note("e4_s1", 0.0, 0.55, 64, 1, 0),
        _note("e4_s2", 0.5, 0.55, 64, 2, 5),
    ]
    a, ir_a = _render(tmp_path, BASE, "body_a", events)
    b, ir_b = _render(tmp_path, S3, "body_b", events)
    boundary = int(0.5 * BEAT_S * SR)

    assert np.array_equal(a[:boundary], b[:boundary])
    assert not np.array_equal(a[boundary:], b[boundary:])
    assert _events(ir_a) == _events(ir_b)
    # S4 is still inactive: there are exactly the two authored note events.
    assert len(_events(ir_b)) == 2
