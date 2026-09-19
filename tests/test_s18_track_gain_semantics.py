from copy import deepcopy

import numpy as np
import pytest

from code_composer.presets import materialize_preset
from code_composer.render import _render_dry_track


SR = 12000
BEAT_S = 0.5
N = int(2.2 * SR)


def _ir(patch, event, *, gain=1.0, pan=0.0, fx=None):
    track = {
        "id": "subject",
        "instrument": "subject_patch",
        "gain": float(gain),
        "pan": float(pan),
        "events": [deepcopy(event)],
    }
    if fx:
        track["fx"] = deepcopy(fx)
    return {
        "meta": {"global_seed": 2718, "sample_rate": SR},
        "instruments": {"subject_patch": deepcopy(patch)},
        "tracks": [track],
    }, track


def _pitched(midi=60, velocity=.74, performance=None):
    ev = {
        "start_beat": 0.0,
        "duration_beats": 1.0,
        "midi": int(midi),
        "velocity": float(velocity),
    }
    if performance is not None:
        ev["performance"] = deepcopy(performance)
    return ev


def _drum(kind="snare", velocity=.78):
    return {
        "event_type": "drum",
        "drum": kind,
        "start_beat": 0.0,
        "duration_beats": .2,
        "velocity": float(velocity),
    }


def _render_legacy(patch, event, gain, *, fx=None):
    ir, track = _ir(patch, event, gain=gain, fx=fx)
    return _render_dry_track(ir, track, N, SR, BEAT_S, graph_mode=False)


def _assert_exact_linear_fader(patch, event, gain=.37, *, fx=None):
    unity = _render_legacy(patch, event, 1.0, fx=fx)
    scaled = _render_legacy(patch, event, gain, fx=fx)
    assert np.array_equal(scaled, unity * gain)
    assert float(np.max(np.abs(unity))) > 1e-8
    return unity, scaled


def test_s18_piano_track_gain_is_post_instrument_linear_fader():
    patch = materialize_preset("piano.concert_grand", role="piano")
    _assert_exact_linear_fader(patch, _pitched(60, .86), .41)


def test_s18_articulated_violin_track_gain_does_not_rewrite_excitation():
    patch = materialize_preset("bowed.violin.modeled_articulated", role="lead")
    event = _pitched(69, .72, {"articulation": "pizzicato"})
    _assert_exact_linear_fader(patch, event, .53)


def test_s18_modeled_bass_track_gain_is_exactly_predictable():
    patch = materialize_preset("bass.electric_finger_modeled", role="bass")
    _assert_exact_linear_fader(patch, _pitched(36, .82), .29)


def test_s18_modeled_percussion_track_gain_is_exactly_predictable():
    patch = materialize_preset("drums.acoustic_kit_modeled", role="drums")
    _assert_exact_linear_fader(patch, _drum("snare", .91), .64)


def test_s18_legacy_track_fader_is_after_legacy_insert_fx():
    patch = materialize_preset("generic.clean_lead", role="lead")
    fx = {
        "delay": {"time": .08, "feedback": .15, "repeats": 2, "cross": .4},
        "reverb": True,
    }
    _assert_exact_linear_fader(patch, _pitched(64, .68), .45, fx=fx)


def test_s18_unity_legacy_gain_matches_graph_mode_dry_render_before_routing():
    cases = [
        (materialize_preset("piano.concert_grand", role="piano"), _pitched(60, .83)),
        (
            materialize_preset("bowed.violin.modeled_articulated", role="lead"),
            _pitched(69, .70, {"articulation": "pizzicato"}),
        ),
        (materialize_preset("bass.electric_finger_modeled", role="bass"), _pitched(36, .80)),
        (materialize_preset("drums.acoustic_kit_modeled", role="drums"), _drum("kick", .84)),
    ]
    for patch, event in cases:
        ir, track = _ir(patch, event, gain=1.0, pan=0.0)
        legacy = _render_dry_track(ir, track, N, SR, BEAT_S, graph_mode=False)
        graph_dry = _render_dry_track(ir, track, N, SR, BEAT_S, graph_mode=True)
        assert np.array_equal(legacy, graph_dry)


def test_s18_track_gain_changes_level_not_normalized_waveform():
    patch = materialize_preset("piano.concert_grand", role="piano")
    unity, scaled = _assert_exact_linear_fader(patch, _pitched(67, .94), .25)
    mask = np.abs(unity) > 1e-12
    # Explicitly guard the property that failed in the post-S17 dogfood:
    # normalized waveform/timbre must remain unchanged when only track gain moves.
    assert np.max(np.abs((scaled[mask] / .25) - unity[mask])) == 0.0
