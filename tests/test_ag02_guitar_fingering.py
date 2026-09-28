from copy import deepcopy

import numpy as np
import pytest

from code_composer.audio.acoustic_guitar import render_acoustic_guitar_note
from code_composer.audio.engines import engine_capabilities
from code_composer.core.song import song_fingerprint
from code_composer.execution import (
    PerformanceBridgeError,
    compile_performance_score_to_render_ir,
    lower_song_to_execution_plan,
    realize_instrument_mechanics,
)
from code_composer.performance.guitar import (
    GuitarFingeringError,
    fingering_candidates,
    resolve_fingering,
)
from code_composer.presets import materialize_preset


PITCHES = (40, 52, 64)  # E2, E3, E4


def _song():
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG02 R3 Fingering", "global_seed": 23},
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


def _score(song=None, midi=64, instrument_performance=None):
    song = song or _song()
    event = {
        "id": "n1",
        "type": "note",
        "start_beat": 0.0,
        "duration_beats": 0.5,
        "midi": midi,
        "velocity": 0.65,
    }
    if instrument_performance is not None:
        event["instrument_performance"] = deepcopy(instrument_performance)
    return {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(song),
        },
        "meta": {"title": "AG02 R3 Fingering"},
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


def _realized(midi=64, payload=None):
    song = _song()
    plan = lower_song_to_execution_plan(song)
    ir = compile_performance_score_to_render_ir(plan, _score(song, midi, payload))
    return realize_instrument_mechanics(ir, plan)


def test_ag02_capability_is_r3_patch_scoped_not_ag00():
    foundation = materialize_preset("acoustic_guitar.steel_foundation")
    r3 = materialize_preset("acoustic_guitar.steel_single_string")
    assert engine_capabilities(foundation)["instrument_performance"] is False
    assert engine_capabilities(foundation)["mechanics_realization"] is False
    assert r3["acoustic_guitar_graph"]["physical_model"] == "ag01_modal_bridge_body_v2"
    assert r3["acoustic_guitar_graph"]["string_source_model"] == "triangular_pluck_bridge_force_v2"
    assert engine_capabilities(r3)["instrument_performance"] is True
    assert engine_capabilities(r3)["mechanics_realization"] is True


def test_standard_tuning_candidates_cover_supported_range():
    assert fingering_candidates(39) == []
    assert fingering_candidates(40)[0]["string"] == 6
    assert any(x["string"] == 1 and x["fret"] == 20 for x in fingering_candidates(84))
    assert fingering_candidates(85) == []


def test_explicit_string_and_fret_are_preserved_exactly():
    out = _realized(64, {"string": 2, "fret": 5})
    ev = out["tracks"][0]["events"][0]
    assert ev["performance"]["instrument"] == {"string": 2, "fret": 5}
    gr = ev["performance"]["guitar_realization"]
    assert (gr["string"], gr["fret"], gr["authority"]) == (
        2, 5, "authored_string_fret"
    )
    report = out["guitar_performance_report"]["tracks"]["g"]["events"][0]
    assert report["authored"] == {"string": 2, "fret": 5}
    assert out["guitar_performance_report"]["upstream_baseline"]["slice"] == "AG01 R3"


def test_partial_authority_fills_only_missing_mechanics():
    a = resolve_fingering(64, {"string": 2})
    assert (a["string"], a["fret"], a["authority"]) == (2, 5, "authored_string")
    b = resolve_fingering(64, {"fret": 5})
    assert (b["string"], b["fret"], b["authority"]) == (2, 5, "authored_fret")


def test_unspecified_fingering_is_deterministic_reference_position():
    a = resolve_fingering(60)
    b = resolve_fingering(60)
    assert a == b
    assert (a["string"], a["fret"]) == (2, 1)
    assert a["authority"] == "deterministic_resolver"
    assert a["position_is_reference"] is True


def test_impossible_authored_position_is_hard_error():
    with pytest.raises(GuitarFingeringError, match="conflicts with authored string"):
        resolve_fingering(64, {"string": 2, "fret": 4})

    song = _song()
    plan = lower_song_to_execution_plan(song)
    ir = compile_performance_score_to_render_ir(
        plan, _score(song, 64, {"string": 2, "fret": 4})
    )
    with pytest.raises(PerformanceBridgeError, match="conflicts with authored string"):
        realize_instrument_mechanics(ir, plan)


def test_engine_rejects_invalid_or_flat_future_payload_fields():
    song = _song()
    plan = lower_song_to_execution_plan(song)
    with pytest.raises(PerformanceBridgeError, match="string.*outside"):
        compile_performance_score_to_render_ir(plan, _score(song, 64, {"string": 7}))
    with pytest.raises(PerformanceBridgeError, match="unsupported acoustic-guitar"):
        compile_performance_score_to_render_ir(plan, _score(song, 64, {"pick": "medium"}))


def test_unplayable_pitch_is_hard_error():
    song = _song()
    plan = lower_song_to_execution_plan(song)
    ir = compile_performance_score_to_render_ir(plan, _score(song, 39))
    with pytest.raises(PerformanceBridgeError, match="no standard-tuning acoustic-guitar fingering"):
        realize_instrument_mechanics(ir, plan)


def test_no_mechanics_and_reference_position_preserve_r3_sample_exact_across_e2_e4():
    patch = materialize_preset("acoustic_guitar.steel_single_string")
    for midi in PITCHES:
        canonical = render_acoustic_guitar_note(midi, 0.45, 24000, patch, velocity=0.65)
        resolved = _realized(midi, None)["tracks"][0]["events"][0]["performance"]
        assert resolved["guitar_realization"]["position_is_reference"] is True
        via_resolver = render_acoustic_guitar_note(
            midi, 0.45, 24000, patch, velocity=0.65, performance=resolved
        )
        explicit_reference = resolve_fingering(midi)
        via_reference = render_acoustic_guitar_note(
            midi,
            0.45,
            24000,
            patch,
            velocity=0.65,
            performance={"guitar_realization": explicit_reference},
        )
        assert np.array_equal(canonical, via_resolver)
        assert np.array_equal(canonical, via_reference)


@pytest.mark.parametrize(
    "midi,reference_pos,alternate_pos",
    [
        (64, (1, 0), (2, 5)),
        (60, (2, 1), (4, 10)),
        (52, (4, 2), (6, 12)),
    ],
)
def test_same_midi_alternate_position_is_distinct_but_tightly_bounded(
    midi, reference_pos, alternate_pos
):
    patch = materialize_preset("acoustic_guitar.steel_single_string")
    reference = resolve_fingering(
        midi, {"string": reference_pos[0], "fret": reference_pos[1]}
    )
    alternate = resolve_fingering(
        midi, {"string": alternate_pos[0], "fret": alternate_pos[1]}
    )
    assert reference["position_is_reference"] is True
    assert alternate["position_is_reference"] is False

    a = render_acoustic_guitar_note(
        midi, 0.45, 24000, patch, velocity=0.65,
        performance={"guitar_realization": reference},
    )
    b = render_acoustic_guitar_note(
        midi, 0.45, 24000, patch, velocity=0.65,
        performance={"guitar_realization": alternate},
    )
    delta = float(np.sqrt(np.mean((a - b) ** 2)))
    reference_rms = float(np.sqrt(np.mean(a * a)))
    ratio = delta / reference_rms
    assert 1e-6 < ratio < 0.12


def test_ag02_realizer_never_changes_authored_pitch_or_timing():
    out = _realized(64, {"string": 2, "fret": 5})
    ev = out["tracks"][0]["events"][0]
    assert ev["midi"] == 64
    assert ev["start_beat"] == 0.0
    assert ev["duration_beats"] == 0.5
