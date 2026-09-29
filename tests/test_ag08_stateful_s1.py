from copy import deepcopy

import numpy as np
import pytest

from code_composer.audio.acoustic_guitar.stateful import (
    STATE_MODEL,
    coupling_is_zero,
    initialize_acoustic_guitar_state,
    render_stateful_acoustic_guitar_track,
    state_energy,
)
from code_composer.audio.engines import engine_for_patch
from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files
from code_composer.presets import PresetError, materialize_preset


BASE = "acoustic_guitar.steel_single_string"
STATEFUL = "acoustic_guitar.steel_stateful"


def _song(preset):
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG08 S1", "global_seed": 89},
        "transport": {"bpm": 96, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
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


def _note(eid, start, dur, midi, string, fret, *, method="finger", strum=None):
    perf = {
        "string": int(string),
        "fret": int(fret),
        "right_hand": {"method": method},
    }
    if strum is not None:
        perf["strum"] = deepcopy(strum)
    return {
        "id": eid,
        "type": "note",
        "start_beat": float(start),
        "duration_beats": float(dur),
        "midi": int(midi),
        "velocity": 0.65,
        "instrument_performance": perf,
    }


def _action(eid, start, kind, **params):
    return {
        "id": eid,
        "type": "instrument_action",
        "start_beat": float(start),
        "duration_beats": 0.08,
        "action": kind,
        "parameters": params,
    }


def _score(preset, events):
    song = _song(preset)
    return song, {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(song),
        },
        "meta": {"title": "AG08 S1"},
        "tracks": [{"id": "g", "events": deepcopy(events)}],
        "render": {
            "sample_rate": 24000,
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


def _f_strum():
    common = {
        "stroke_id": "f-down",
        "direction": "down",
        "traversal_ms": 30.0,
        "entry_strength": 0.62,
        "acceleration": 0.10,
        "pick_depth": 0.58,
        "attack_angle_deg": 42.0,
        "follow_through": 0.72,
        "accent_position": 0.50,
        "accent_amount": 0.08,
        "from_string": 6,
        "to_string": 1,
        "state": "sounding",
    }
    voicing = [(41,6,1),(48,5,3),(53,4,3),(57,3,2),(60,2,1),(65,1,1)]
    return [
        _note(f"f{i}", 0.0, 1.0, midi, string, fret, method="pick", strum=common)
        for i, (midi,string,fret) in enumerate(voicing)
    ]


def test_stateful_candidate_is_opt_in_and_canonical_baseline_is_untouched():
    base = materialize_preset(BASE)
    stateful = materialize_preset(STATEFUL)

    base_graph = base["acoustic_guitar_graph"]
    state_graph = stateful["acoustic_guitar_graph"]

    assert "stateful_coupling" not in base_graph
    assert state_graph["stateful_coupling"]["enabled"] is True
    assert state_graph["stateful_coupling"]["model"] == STATE_MODEL
    assert coupling_is_zero(state_graph)

    assert engine_for_patch(base).describe(base)["track_rendering"] is False
    assert engine_for_patch(stateful).describe(stateful)["track_rendering"] is True


def test_initial_state_is_deterministic_zero_energy():
    patch = materialize_preset(STATEFUL)
    graph = patch["acoustic_guitar_graph"]
    a = initialize_acoustic_guitar_state(24000, graph)
    b = initialize_acoustic_guitar_state(24000, graph)

    assert a.model == STATE_MODEL
    assert a.sample_rate == 24000
    assert a.sample_index == 0
    assert np.array_equal(a.string_energy, np.zeros(6))
    assert np.array_equal(a.string_phase_proxy, np.zeros(6))
    assert np.array_equal(a.bridge_state, np.zeros(2))
    assert np.array_equal(a.body_state, np.zeros(10))
    assert np.array_equal(a.active_fret, np.full(6, -1, dtype=np.int16))
    assert state_energy(a) == 0.0
    assert np.array_equal(a.string_energy, b.string_energy)
    assert np.array_equal(a.body_state, b.body_state)


def test_zero_coupling_track_entrypoint_strictly_delegates_to_legacy_path():
    patch = materialize_preset(STATEFUL)
    result = render_stateful_acoustic_guitar_track(
        [],
        1024,
        24000,
        patch,
        60.0 / 96.0,
        gain=1.0,
        pan=0.0,
    )
    assert result is None


@pytest.mark.parametrize("case", ["single", "strum", "note_action"])
def test_zero_coupling_candidate_is_sample_exact_with_ag07(tmp_path, case):
    if case == "single":
        events = [_note("e4", 0.0, 0.75, 64, 1, 0, method="finger")]
    elif case == "strum":
        events = _f_strum()
    else:
        events = [
            _note("bass", 0.0, 0.9, 52, 4, 2, method="thumb"),
            _action(
                "slap", 0.0, "top_slap",
                strength=0.58, location="soundboard",
            ),
            _action(
                "dead", 1.0, "dead_strum",
                strength=0.60, direction="down",
                traversal_ms=36.0, string_count=6, location="strings",
            ),
        ]

    a, ir_a = _render(tmp_path, BASE, f"{case}_a", events)
    b, ir_b = _render(tmp_path, STATEFUL, f"{case}_b", events)

    assert np.array_equal(a, b)
    assert a.dtype == b.dtype
    assert a.shape == b.shape

    # Authored event authority is identical; preset identity is allowed to differ.
    ea = ir_a["tracks"][0]["events"]
    eb = ir_b["tracks"][0]["events"]
    assert ea == eb


def test_nonzero_coupling_is_blocked_until_later_ag08_slice():
    patch = materialize_preset(
        STATEFUL,
        patch_overrides={
            "acoustic_guitar_graph": {
                "stateful_coupling": {"cross_string_coupling": 0.1}
            }
        },
    )
    with pytest.raises(NotImplementedError, match="beyond S3"):
        render_stateful_acoustic_guitar_track(
            [], 1024, 24000, patch, 60.0/96.0
        )


def test_stateful_config_validation_is_bounded():
    with pytest.raises(PresetError, match="cross_string_coupling"):
        materialize_preset(
            STATEFUL,
            patch_overrides={
                "acoustic_guitar_graph": {
                    "stateful_coupling": {"cross_string_coupling": 0.25}
                }
            },
        )

    with pytest.raises(PresetError, match="body_state_order"):
        materialize_preset(
            STATEFUL,
            patch_overrides={
                "acoustic_guitar_graph": {
                    "stateful_coupling": {"body_state_order": 1}
                }
            },
        )
