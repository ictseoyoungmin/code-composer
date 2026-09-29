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


PITCHES = (40, 52, 64)


def _song():
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG04 Left Hand", "global_seed": 43},
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


def _score(events):
    song = _song()
    return song, {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(song),
        },
        "meta": {"title": "AG04 Left Hand"},
        "tracks": [{"id": "g", "events": deepcopy(events)}],
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


def _note(event_id, start, midi, string, fret, *, left_hand=None, right_hand=None):
    perf = {"string": string, "fret": fret}
    if right_hand is not None:
        perf["right_hand"] = deepcopy(right_hand)
    if left_hand is not None:
        perf["left_hand"] = deepcopy(left_hand)
    return {
        "id": event_id,
        "type": "note",
        "start_beat": float(start),
        "duration_beats": 0.5,
        "midi": int(midi),
        "velocity": 0.65,
        "instrument_performance": perf,
    }


def _realized(events):
    song, score = _score(events)
    plan = lower_song_to_execution_plan(song)
    ir = compile_performance_score_to_render_ir(plan, score)
    return realize_instrument_mechanics(ir, plan)


def _render(midi, perf=None):
    patch = materialize_preset("acoustic_guitar.steel_single_string")
    return render_acoustic_guitar_note(
        midi, 0.45, 24000, patch, velocity=0.65, performance=perf
    )


def _rms(x):
    return float(np.sqrt(np.mean(x * x)) + 1e-12)


def _attack_high_band_energy(x, sr=24000, ms=25, fmin=2000.0):
    n = max(16, int(sr * ms / 1000.0))
    mono = np.mean(x[:n], axis=1)
    win = np.hanning(len(mono))
    spec = np.fft.rfft(mono * win)
    freqs = np.fft.rfftfreq(len(mono), 1.0 / sr)
    mask = freqs >= float(fmin)
    return float(np.sqrt(np.sum(np.abs(spec[mask]) ** 2)) + 1e-12)


def test_no_left_hand_preserves_ag03_canonical_sample_exact_across_e2_e4():
    positions = {40: (6, 0), 52: (4, 2), 64: (1, 0)}
    for midi in PITCHES:
        string, fret = positions[midi]
        out = _realized([_note("n", 0.0, midi, string, fret)])
        perf = out["tracks"][0]["events"][0]["performance"]
        assert "left_hand_realization" not in perf
        canonical = _render(midi, {
            "guitar_realization": perf["guitar_realization"],
        })
        assert np.array_equal(canonical, _render(midi, perf))


@pytest.mark.parametrize("technique", ["palm_mute", "fretting_mute", "dead_note", "natural_harmonic"])
def test_single_note_left_hand_techniques_preserve_authored_identity(technique):
    payload = {"technique": technique}
    if technique == "natural_harmonic":
        payload["harmonic_order"] = 2
    out = _realized([_note("n", 0.0, 64, 1, 0, left_hand=payload)])
    ev = out["tracks"][0]["events"][0]
    assert ev["midi"] == 64
    assert ev["start_beat"] == 0.0
    assert ev["duration_beats"] == 0.5
    lh = ev["performance"]["left_hand_realization"]
    assert lh["technique"] == technique
    report = out["guitar_performance_report"]["tracks"]["g"]
    assert report["scope"]["left_hand_articulation"] is True
    assert report["left_hand_event_count"] == 1


def test_mute_dead_and_harmonic_are_deterministic_and_physically_distinct():
    baseline = _realized([_note("n", 0.0, 64, 1, 0)])
    base_perf = baseline["tracks"][0]["events"][0]["performance"]
    base = _render(64, base_perf)

    rendered = {}
    for technique in ("palm_mute", "fretting_mute", "dead_note", "natural_harmonic"):
        payload = {"technique": technique}
        if technique == "natural_harmonic":
            payload["harmonic_order"] = 2
        out = _realized([_note("n", 0.0, 64, 1, 0, left_hand=payload)])
        perf = out["tracks"][0]["events"][0]["performance"]
        a = _render(64, perf)
        b = _render(64, perf)
        assert np.array_equal(a, b)
        rendered[technique] = a
        assert _rms(a - base) / _rms(base) > 0.03

    assert _rms(rendered["dead_note"]) < _rms(rendered["palm_mute"])
    assert not np.array_equal(rendered["palm_mute"], rendered["fretting_mute"])
    assert not np.array_equal(rendered["natural_harmonic"], rendered["palm_mute"])


@pytest.mark.parametrize(
    "technique,src_midi,src_fret,dst_midi,dst_fret",
    [
        ("slide", 64, 0, 69, 5),
        ("hammer_on", 64, 0, 67, 3),
        ("pull_off", 67, 3, 64, 0),
    ],
)
def test_transition_realization_uses_same_string_and_reduced_excitation(
    technique, src_midi, src_fret, dst_midi, dst_fret
):
    out = _realized([
        _note("a", 0.0, src_midi, 1, src_fret, right_hand={"method": "finger"}),
        _note("b", 0.5, dst_midi, 1, dst_fret, left_hand={"technique": technique}),
    ])
    ev = out["tracks"][0]["events"][1]
    lh = ev["performance"]["left_hand_realization"]
    assert lh["transition"] is True
    assert lh["from_midi"] == src_midi
    assert lh["to_midi"] == dst_midi
    assert lh["string"] == 1
    assert lh["excitation_scale"] < 0.11
    assert "right_hand_realization" not in ev["performance"]


def test_transition_render_is_not_a_fresh_pick_attack():
    out = _realized([
        _note("a", 0.0, 64, 1, 0, right_hand={"method": "pick"}),
        _note("b", 0.5, 67, 1, 3, left_hand={"technique": "hammer_on"}),
    ])
    dst = out["tracks"][0]["events"][1]
    legato = _render(67, dst["performance"])

    picked = _realized([
        _note("b", 0.0, 67, 1, 3, right_hand={"method": "pick"}),
    ])
    picked_audio = _render(67, picked["tracks"][0]["events"][0]["performance"])

    # Carried same-string tonal energy may keep total attack RMS high. The
    # no-fake-pick invariant is specifically about newly injected contact energy.
    legato_hf = _attack_high_band_energy(legato)
    picked_hf = _attack_high_band_energy(picked_audio)
    assert legato_hf < picked_hf * 0.75
    assert not np.array_equal(legato, picked_audio)


def test_slide_has_time_varying_pitch_transition():
    out = _realized([
        _note("a", 0.0, 64, 1, 0),
        _note("b", 0.5, 69, 1, 5, left_hand={"technique": "slide", "transition_ms": 90}),
    ])
    perf = out["tracks"][0]["events"][1]["performance"]
    slide = _render(69, perf)

    plain = _realized([_note("b", 0.0, 69, 1, 5)])
    plain_audio = _render(69, plain["tracks"][0]["events"][0]["performance"])
    assert not np.array_equal(slide, plain_audio)
    assert _rms(slide - plain_audio) / _rms(plain_audio) > 0.05


def test_transition_requires_previous_same_string_and_direction():
    with pytest.raises(PerformanceBridgeError, match="preceding pitched"):
        _realized([_note("b", 0.0, 67, 1, 3, left_hand={"technique": "hammer_on"})])

    with pytest.raises(PerformanceBridgeError, match="same-string"):
        _realized([
            _note("a", 0.0, 64, 1, 0),
            _note("b", 0.5, 67, 2, 8, left_hand={"technique": "slide"}),
        ])

    with pytest.raises(PerformanceBridgeError, match="above source"):
        _realized([
            _note("a", 0.0, 67, 1, 3),
            _note("b", 0.5, 64, 1, 0, left_hand={"technique": "hammer_on"}),
        ])

    with pytest.raises(PerformanceBridgeError, match="below source"):
        _realized([
            _note("a", 0.0, 64, 1, 0),
            _note("b", 0.5, 67, 1, 3, left_hand={"technique": "pull_off"}),
        ])


def test_transition_destination_rejects_new_right_hand_strike():
    with pytest.raises(PerformanceBridgeError, match="must not author a new right_hand"):
        _realized([
            _note("a", 0.0, 64, 1, 0),
            _note(
                "b", 0.5, 67, 1, 3,
                left_hand={"technique": "hammer_on"},
                right_hand={"method": "pick"},
            ),
        ])


def test_invalid_left_hand_contract_is_hard_error():
    song, score = _score([
        _note("n", 0.0, 64, 1, 0, left_hand={"technique": "bend"}),
    ])
    plan = lower_song_to_execution_plan(song)
    with pytest.raises(PerformanceBridgeError, match="left_hand.technique"):
        compile_performance_score_to_render_ir(plan, score)

    song, score = _score([
        _note("n", 0.0, 64, 1, 0, left_hand={"technique": "palm_mute", "future": 1}),
    ])
    plan = lower_song_to_execution_plan(song)
    with pytest.raises(PerformanceBridgeError, match="unsupported AG04"):
        compile_performance_score_to_render_ir(plan, score)
