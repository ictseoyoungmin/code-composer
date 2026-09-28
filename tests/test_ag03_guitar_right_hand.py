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
from code_composer.performance.guitar import resolve_fingering, resolve_right_hand
from code_composer.presets import materialize_preset


PITCHES = (40, 52, 64)
METHODS = ("finger", "thumb", "nail", "pick")


def _song():
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG03 Right Hand", "global_seed": 31},
        "transport": {"bpm": 96, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
        "tonal": {"root": "E", "scale": "major"},
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
        "tracks": [{"id": "g", "function": "single-note", "instrument": "guitar"}],
        "materials": [{"id": "m", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": "part", "section": "a", "track": "g", "material": "m"}],
    }


def _score(payload=None, midi=64):
    song = _song()
    event = {
        "id": "n1",
        "type": "note",
        "start_beat": 0.0,
        "duration_beats": 0.5,
        "midi": midi,
        "velocity": 0.65,
    }
    if payload is not None:
        event["instrument_performance"] = deepcopy(payload)
    return song, {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(song),
        },
        "meta": {"title": "AG03 Right Hand"},
        "tracks": [{"id": "g", "events": [event]}],
        "render": {
            "sample_rate": 24000,
            "tail_seconds": 0.1,
            "mix": {
                "tracks": [{"track": "g", "gain": 0.5, "pan": 0.0, "reverb_send": 0.0}],
                "music_bus_gain": 1.0,
                "room_return_gain": 0.0,
                "master_gain": 0.8,
            },
        },
    }


def _realized(payload=None, midi=64):
    song, score = _score(payload, midi)
    plan = lower_song_to_execution_plan(song)
    ir = compile_performance_score_to_render_ir(plan, score)
    return realize_instrument_mechanics(ir, plan)


def _render(midi, performance=None, velocity=0.65):
    patch = materialize_preset("acoustic_guitar.steel_single_string")
    return render_acoustic_guitar_note(
        midi, 0.45, 24000, patch, velocity=velocity, performance=performance
    )


def _rms(x):
    return float(np.sqrt(np.mean(x * x)) + 1e-12)


def test_no_right_hand_preserves_ag02_canonical_sample_exact_across_e2_e4():
    for midi in PITCHES:
        canonical = _render(midi)
        realized = _realized(None, midi)
        perf = realized["tracks"][0]["events"][0]["performance"]
        assert "right_hand_realization" not in perf
        assert np.array_equal(canonical, _render(midi, perf))


def test_neutral_right_hand_reference_is_sample_exact():
    patch = materialize_preset("acoustic_guitar.steel_single_string")
    graph = patch["acoustic_guitar_graph"]
    fingering = resolve_fingering(64)
    right = resolve_right_hand({"pluck_position": graph["pluck_position"]}, graph)
    assert right["method"] == "neutral"
    canonical = _render(
        64, {"guitar_realization": fingering}
    )
    explicit_reference = _render(
        64,
        {
            "guitar_realization": fingering,
            "right_hand_realization": right,
        },
    )
    assert np.array_equal(canonical, explicit_reference)


@pytest.mark.parametrize("method", METHODS)
def test_authored_method_is_preserved_in_provenance(method):
    out = _realized(
        {"string": 1, "fret": 0, "right_hand": {"method": method}},
        64,
    )
    ev = out["tracks"][0]["events"][0]
    assert ev["performance"]["instrument"]["right_hand"]["method"] == method
    assert ev["performance"]["right_hand_realization"]["method"] == method
    report = out["guitar_performance_report"]["tracks"]["g"]
    assert report["right_hand_event_count"] == 1
    assert report["right_hand_events"][0]["resolved"]["method"] == method
    assert report["scope"]["right_hand_excitation"] is True


def test_no_authored_right_hand_keeps_report_scope_inactive():
    out = _realized({"string": 1, "fret": 0}, 64)
    report = out["guitar_performance_report"]["tracks"]["g"]
    assert report["scope"]["right_hand_excitation"] is False
    assert report["right_hand_event_count"] == 0


def test_invalid_right_hand_fields_and_values_are_hard_errors():
    song, score = _score({"right_hand": {"method": "bow"}}, 64)
    plan = lower_song_to_execution_plan(song)
    with pytest.raises(PerformanceBridgeError, match="right_hand.method"):
        compile_performance_score_to_render_ir(plan, score)

    song, score = _score({"right_hand": {"pluck_position": 0.8}}, 64)
    plan = lower_song_to_execution_plan(song)
    with pytest.raises(PerformanceBridgeError, match="pluck_position"):
        compile_performance_score_to_render_ir(plan, score)

    song, score = _score({"right_hand": {"future_field": 1}}, 64)
    plan = lower_song_to_execution_plan(song)
    with pytest.raises(PerformanceBridgeError, match="unsupported AG03"):
        compile_performance_score_to_render_ir(plan, score)


def test_four_methods_are_distinct_but_remain_bounded_on_same_position():
    patch = materialize_preset("acoustic_guitar.steel_single_string")
    graph = patch["acoustic_guitar_graph"]
    fingering = resolve_fingering(64, {"string": 1, "fret": 0})
    baseline = _render(64, {"guitar_realization": fingering})
    rendered = {}
    for method in METHODS:
        rh = resolve_right_hand({"method": method}, graph)
        rendered[method] = _render(
            64,
            {
                "guitar_realization": fingering,
                "right_hand_realization": rh,
            },
        )
        ratio = _rms(rendered[method] - baseline) / _rms(baseline)
        assert 1e-5 < ratio < 0.35

    for i, a in enumerate(METHODS):
        for b in METHODS[i + 1:]:
            assert not np.array_equal(rendered[a], rendered[b])
            assert _rms(rendered[a] - rendered[b]) / _rms(baseline) > 1e-4


def test_pluck_position_angle_strength_and_velocity_affect_explicit_excitation():
    patch = materialize_preset("acoustic_guitar.steel_single_string")
    graph = patch["acoustic_guitar_graph"]
    fingering = resolve_fingering(64, {"string": 1, "fret": 0})

    def render_right(payload, velocity=0.65):
        rh = resolve_right_hand(payload, graph)
        return _render(
            64,
            {
                "guitar_realization": fingering,
                "right_hand_realization": rh,
            },
            velocity=velocity,
        )

    near_bridge = render_right({"method": "finger", "pluck_position": 0.07})
    away_bridge = render_right({"method": "finger", "pluck_position": 0.28})
    assert not np.array_equal(near_bridge, away_bridge)

    shallow = render_right({"method": "pick", "attack_angle_deg": 15.0})
    steep = render_right({"method": "pick", "attack_angle_deg": 75.0})
    assert not np.array_equal(shallow, steep)

    light = render_right({"method": "nail", "strength": 0.2})
    strong = render_right({"method": "nail", "strength": 0.9})
    assert not np.array_equal(light, strong)

    soft_velocity = render_right({"method": "pick"}, velocity=0.35)
    hard_velocity = render_right({"method": "pick"}, velocity=0.92)
    assert not np.array_equal(soft_velocity, hard_velocity)


def test_ag03_never_changes_authored_pitch_or_timing():
    out = _realized(
        {
            "string": 2,
            "fret": 5,
            "right_hand": {
                "method": "pick",
                "pluck_position": 0.11,
                "attack_angle_deg": 35.0,
                "strength": 0.7,
            },
        },
        64,
    )
    ev = out["tracks"][0]["events"][0]
    assert ev["midi"] == 64
    assert ev["start_beat"] == 0.0
    assert ev["duration_beats"] == 0.5
