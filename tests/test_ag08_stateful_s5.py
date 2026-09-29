from copy import deepcopy

import numpy as np
import pytest

from code_composer.audio.acoustic_guitar.stateful import (
    _action_string_contact_schedule,
    _string_contact_loading_curve,
    _technique_carry_tau_scale,
)
from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files
from code_composer.presets import PresetError, materialize_preset


S4 = "acoustic_guitar.steel_stateful_sympathetic"
S5 = "acoustic_guitar.steel_stateful_performance"
SR = 24000
BPM = 96
BEAT_S = 60.0 / BPM


def _song(preset):
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG08 S5", "global_seed": 113},
        "transport": {"bpm": BPM, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
        "tonal": {"root": "E", "scale": "major"},
        "sections": [{"id": "a", "bars": 2}],
        "instruments": [{
            "id": "guitar",
            "family": "acoustic_guitar",
            "variant": "steel-string",
            "render_lock": {"preset": preset, "preset_version": "1.0.0"},
        }],
        "tracks": [{"id": "g", "function": "percussive-fingerstyle", "instrument": "guitar"}],
        "materials": [{"id": "m", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": "part", "section": "a", "track": "g", "material": "m"}],
    }


def _note(
    eid, start, dur, midi, string, fret, *,
    method="finger", arpeggio=None, strum=None, left_hand=None, velocity=0.65,
):
    perf = {"string": int(string), "fret": int(fret)}
    if method is not None:
        perf["right_hand"] = {"method": method}
    if arpeggio is not None:
        perf["arpeggio"] = deepcopy(arpeggio)
    if strum is not None:
        perf["strum"] = deepcopy(strum)
    if left_hand is not None:
        perf["left_hand"] = deepcopy(left_hand)
    return {
        "id": eid,
        "type": "note",
        "start_beat": float(start),
        "duration_beats": float(dur),
        "midi": int(midi),
        "velocity": float(velocity),
        "instrument_performance": perf,
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


def _strum_cfg(stroke_id):
    return {
        "stroke_id": stroke_id,
        "direction": "down",
        "traversal_ms": 34.0,
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


def _mixed_phrase():
    pre = "pre-arp"
    events = [
        _note(
            "arp-bass", 0.00, 0.20, 48, 5, 3, method="thumb",
            arpeggio={"gesture_id": pre, "player": "thumb", "voice": "bass", "sequence_index": 0},
        ),
        _note(
            "arp-inner", 0.25, 0.20, 55, 3, 0, method="finger",
            arpeggio={"gesture_id": pre, "player": "index", "voice": "inner", "sequence_index": 1},
        ),
    ]
    cfg = _strum_cfg("g-down")
    voicing = [(43, 6, 3), (47, 5, 2), (50, 4, 0), (55, 3, 0), (59, 2, 0), (67, 1, 3)]
    for i, (midi, string, fret) in enumerate(voicing):
        events.append(
            _note(
                f"strum-{i}", 0.65, 0.28, midi, string, fret,
                method="pick", strum=cfg,
            )
        )
    events += [
        _action(
            "mute", 1.15, "muted_strum",
            strength=0.72, direction="down", traversal_ms=38.0,
            string_count=6, location="strings",
        ),
        _action(
            "slap", 1.45, "top_slap",
            strength=0.58, location="soundboard",
        ),
        _note(
            "post-bass", 1.75, 0.22, 40, 6, 0, method="thumb",
            arpeggio={"gesture_id": "post-arp", "player": "thumb", "voice": "bass", "sequence_index": 0},
        ),
        _note(
            "post-treble", 2.00, 0.22, 59, 2, 0, method="finger",
            arpeggio={"gesture_id": "post-arp", "player": "middle", "voice": "treble", "sequence_index": 1},
        ),
    ]
    return events


def _score(preset, events):
    song = _song(preset)
    return song, {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(song),
        },
        "meta": {"title": "AG08 S5"},
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


def test_s5_preset_extends_s4_without_widening_passive_coupling():
    patch = materialize_preset(S5)
    cfg = patch["acoustic_guitar_graph"]["stateful_coupling"]
    assert cfg["same_string_memory"] == 0.32
    assert cfg["bridge_memory"] == 0.46
    assert cfg["action_body_memory"] == 0.52
    assert cfg["cross_string_coupling"] == 0.20
    assert cfg["sympathetic_gain"] == 0.18
    assert cfg["technique_transition_memory"] == 0.82
    assert cfg["cross_string_coupling"] * cfg["sympathetic_gain"] == pytest.approx(0.036)


def test_s5_transition_memory_validation_is_bounded():
    with pytest.raises(PresetError, match="technique_transition_memory"):
        materialize_preset(
            S5,
            patch_overrides={
                "acoustic_guitar_graph": {
                    "stateful_coupling": {"technique_transition_memory": 1.1}
                }
            },
        )


def test_s5_string_contact_schedule_uses_physical_traversal_order():
    down = _action_string_contact_schedule(
        "muted_strum",
        {"direction": "down", "traversal_ms": 40.0, "string_count": 6},
        SR,
    )
    up = _action_string_contact_schedule(
        "muted_strum",
        {"direction": "up", "traversal_ms": 40.0, "string_count": 6},
        SR,
    )
    assert [idx + 1 for idx, _ in down] == [6, 5, 4, 3, 2, 1]
    assert [idx + 1 for idx, _ in up] == [1, 2, 3, 4, 5, 6]
    assert down[0][1] == up[0][1] == 0
    assert down[-1][1] == up[-1][1] == int(round(0.040 * SR))
    assert all(b[1] > a[1] for a, b in zip(down, down[1:]))


def test_s5_dead_contact_removes_more_residual_energy_than_muted_contact():
    muted = _string_contact_loading_curve(0.82, "muted_strum", 0.72, 0.05, SR, 4096)
    dead = _string_contact_loading_curve(0.82, "dead_strum", 0.72, 0.05, SR, 4096)
    assert muted[0] == pytest.approx(1.0)
    assert dead[0] == pytest.approx(1.0)
    assert 0.0 < dead[-1] < muted[-1] < 1.0


def test_s5_legato_and_mute_scale_existing_residual_in_opposite_directions():
    base = {"performance": {"left_hand_realization": {"technique": ""}}}
    hammer = {"performance": {"left_hand_realization": {"technique": "hammer_on"}}}
    dead = {"performance": {"left_hand_realization": {"technique": "dead_note"}}}
    assert _technique_carry_tau_scale(base, 0.82) == 1.0
    assert _technique_carry_tau_scale(hammer, 0.82) > 1.0
    assert 0.0 < _technique_carry_tau_scale(dead, 0.82) < 1.0


def test_s5_isolated_note_without_technique_transition_is_sample_exact_with_s4(tmp_path):
    events = [_note("e4", 0.0, 0.70, 64, 1, 0, method="finger")]
    a, ir_a = _render(tmp_path, S4, "single_s4", events)
    b, ir_b = _render(tmp_path, S5, "single_s5", events)
    assert np.array_equal(a, b)
    assert _events(ir_a) == _events(ir_b)


def test_s5_mixed_performance_is_continuous_deterministic_and_event_exact(tmp_path):
    events = _mixed_phrase()
    a, ir_a = _render(tmp_path, S4, "mixed_s4", events)
    b1, ir_b1 = _render(tmp_path, S5, "mixed_s5_1", events)
    b2, ir_b2 = _render(tmp_path, S5, "mixed_s5_2", events)

    mute_boundary = int(1.15 * BEAT_S * SR)
    assert np.array_equal(a[:mute_boundary], b1[:mute_boundary])
    assert not np.array_equal(a[mute_boundary:], b1[mute_boundary:])
    assert np.array_equal(b1, b2)
    assert _events(ir_a) == _events(ir_b1) == _events(ir_b2)
    assert len(_events(ir_b1)) == len(events)

    delta_ratio = _rms(b1[mute_boundary:] - a[mute_boundary:]) / (
        _rms(a[mute_boundary:]) + 1e-12
    )
    assert 0.002 < delta_ratio < 0.55
    assert float(np.max(np.abs(b1))) < 0.98
