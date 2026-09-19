from copy import deepcopy

import numpy as np

from code_composer.audio.dsp import apply_pan
from code_composer.presets import materialize_preset
from code_composer.render import _render_dry_track


SR = 12000
BEAT_S = 0.5
N = int(2.4 * SR)


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
        "meta": {"global_seed": 314159, "sample_rate": SR},
        "instruments": {"subject_patch": deepcopy(patch)},
        "tracks": [track],
    }, track


def _pitched(midi=60, velocity=.78, performance=None, pan=None):
    ev = {
        "start_beat": 0.0,
        "duration_beats": 1.2,
        "midi": int(midi),
        "velocity": float(velocity),
    }
    if performance is not None:
        ev["performance"] = deepcopy(performance)
    if pan is not None:
        ev["pan"] = float(pan)
    return ev


def _drum(kind="snare", velocity=.82, pan=None):
    ev = {
        "event_type": "drum",
        "drum": kind,
        "start_beat": 0.0,
        "duration_beats": .24,
        "velocity": float(velocity),
    }
    if pan is not None:
        ev["pan"] = float(pan)
    return ev


def _legacy(patch, event, pan, *, fx=None):
    ir, track = _ir(patch, event, pan=pan, fx=fx)
    return _render_dry_track(ir, track, N, SR, BEAT_S, graph_mode=False)


def _assert_stereo_balance_matches_unpanned(patch, event, pan, *, fx=None):
    center = _legacy(patch, event, 0.0, fx=fx)
    moved = _legacy(patch, event, pan, fx=fx)
    expected = apply_pan(center, pan)
    assert np.array_equal(moved, expected)
    assert float(np.max(np.abs(center))) > 1e-8
    return center, moved


def _lr_corr(sig):
    left, right = sig[:, 0], sig[:, 1]
    if np.std(left) < 1e-12 or np.std(right) < 1e-12:
        return 1.0
    return float(np.corrcoef(left, right)[0, 1])


def test_s19_piano_track_pan_preserves_intrinsic_stereo_image():
    patch = materialize_preset("piano.concert_grand", role="piano")
    center, moved = _assert_stereo_balance_matches_unpanned(
        patch, _pitched(64, .88), -.22
    )
    # The pre-S19 bug collapsed any non-zero track pan to a perfectly correlated
    # mono image before repanning. The stereo-aware balance must retain decorrelation.
    assert _lr_corr(center) < .999
    assert _lr_corr(moved) < .999


def test_s19_articulated_violin_track_pan_preserves_intrinsic_stereo_image():
    patch = materialize_preset("bowed.violin.modeled_articulated", role="lead")
    center, moved = _assert_stereo_balance_matches_unpanned(
        patch, _pitched(69, .73, {"articulation": "pizzicato"}), .18
    )
    assert _lr_corr(center) < .999
    assert _lr_corr(moved) < .999


def test_s19_modeled_bass_track_pan_uses_same_stereo_balance_operator():
    patch = materialize_preset("bass.electric_finger_modeled", role="bass")
    _assert_stereo_balance_matches_unpanned(patch, _pitched(38, .81), -.31)


def test_s19_modeled_percussion_track_pan_uses_same_stereo_balance_operator():
    patch = materialize_preset("drums.acoustic_kit_modeled", role="drums")
    _assert_stereo_balance_matches_unpanned(patch, _drum("snare", .90), .27)


def test_s19_legacy_track_pan_is_after_track_insert_fx():
    patch = materialize_preset("generic.clean_lead", role="lead")
    fx = {
        "delay": {"time": .07, "feedback": .14, "repeats": 2, "cross": .45},
        "reverb": True,
    }
    _assert_stereo_balance_matches_unpanned(
        patch, _pitched(67, .71), .24, fx=fx
    )


def test_s19_legacy_pan_matches_graph_route_pan_operator_for_dry_track():
    cases = [
        (materialize_preset("piano.concert_grand", role="piano"), _pitched(60, .84), -.19),
        (materialize_preset("bass.electric_finger_modeled", role="bass"), _pitched(36, .79), .25),
        (materialize_preset("drums.acoustic_kit_modeled", role="drums"), _drum("kick", .86), -.16),
    ]
    for patch, event, pan in cases:
        ir, track = _ir(patch, event, pan=pan)
        graph_dry = _render_dry_track(ir, track, N, SR, BEAT_S, graph_mode=True)
        legacy = _render_dry_track(ir, track, N, SR, BEAT_S, graph_mode=False)
        assert np.array_equal(legacy, apply_pan(graph_dry, pan))


def test_s19_explicit_event_pan_remains_event_local_then_track_pan_balances_result():
    patch = materialize_preset("piano.concert_grand", role="piano")
    event = _pitched(72, .76, pan=-.25)
    center_track = _legacy(patch, event, 0.0)
    moved_track = _legacy(patch, event, .20)
    assert np.array_equal(moved_track, apply_pan(center_track, .20))
