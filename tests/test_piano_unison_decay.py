"""Regression coverage for the natural envelope of each acoustic-piano string.

Keep the other unison controls at zero: a combined-preset comparison can pass
while decay_spread alone is silently discarded by the legacy release path.
"""
from copy import deepcopy

import numpy as np
import pytest

from code_composer.audio.piano import render_piano_note


SR = 24000
DURATION = 1.0


def _patch(decay_spread):
    # Mute independent sources so different render lengths cannot change hammer
    # RNG or resonance. The real string, damper, pan and body-filter paths run.
    return {
        "kind": "piano",
        "piano_graph": {
            "strings": {
                "max_partials": 12,
                "base_decay_s": 4.2,
                "detune_cents": 0.65,
                "unison_decoherence": {
                    "start_midi": 61,
                    "partial_mistune_cents": 0.0,
                    "inharmonicity_spread": 0.0,
                    "decay_spread": decay_spread,
                    "level_spread": 0.0,
                },
            },
            "hammer": {"gain": 0.0, "noise_gain": 0.0, "tonal_gain": 0.0},
            "resonance": {"gain": 0.0, "pedal_gain": 0.0},
            "mechanics": {"key_noise_gain": 0.0, "damper_noise_gain": 0.0},
            "damper": {"release_s": 0.20, "pedal_release_s": 1.65},
        },
    }


def _render(midi, spread, pedal, controlled=False):
    return render_piano_note(
        midi, DURATION, SR, _patch(spread), velocity=0.75,
        performance={"pedal": pedal, "pedal_controlled": controlled},
    )


@pytest.mark.parametrize("midi", [72, 76, 84, 88])
@pytest.mark.parametrize("pedal", [False, True])
def test_decay_spread_alone_changes_legacy_sustain_and_release(midi, pedal):
    reference = _render(midi, 0.0, pedal)
    varied = _render(midi, 0.20, pedal)
    off = int(DURATION * SR)
    # The old bug overwrote the entire array, not just its release slice.
    for region in (slice(int(0.20 * SR), off), slice(off, off + int(0.05 * SR))):
        assert np.max(np.abs(varied[region] - reference[region])) > 1e-6
    assert reference.shape == varied.shape
    assert np.isfinite(varied).all()
    assert np.max(np.abs(varied)) <= 1.0


@pytest.mark.parametrize("midi", [72, 76, 84, 88])
@pytest.mark.parametrize("pedal", [False, True])
@pytest.mark.parametrize("spread", [0.0, 0.20])
def test_held_string_envelope_agrees_across_pedal_control_paths(midi, pedal, spread):
    # While the key remains held, neither release policy should rewrite the
    # natural string envelope. This is an independent behavioral oracle, not
    # a second copy of the oscillator/envelope implementation.
    legacy = _render(midi, spread, pedal)
    controlled = _render(midi, spread, pedal, controlled=True)
    off = int(DURATION * SR)
    np.testing.assert_allclose(legacy[:off], controlled[:off], rtol=0, atol=1e-14)


@pytest.mark.parametrize("midi", [36, 55, 60, 61])
@pytest.mark.parametrize("pedal", [False, True])
def test_decay_spread_leaves_unweighted_registers_unchanged(midi, pedal):
    np.testing.assert_array_equal(_render(midi, 0.0, pedal), _render(midi, 0.20, pedal))


@pytest.mark.parametrize("pedal", [False, True])
def test_zero_decay_spread_matches_absent_decoherence(pedal):
    patch = _patch(0.0)
    without = deepcopy(patch)
    del without["piano_graph"]["strings"]["unison_decoherence"]
    performance = {"pedal": pedal}
    expected = render_piano_note(84, DURATION, SR, without, velocity=0.75, performance=performance)
    actual = render_piano_note(84, DURATION, SR, patch, velocity=0.75, performance=performance)
    np.testing.assert_array_equal(actual, expected)


def test_decay_spread_render_is_deterministic_and_does_not_mutate_inputs():
    patch = _patch(0.20)
    performance = {"pedal": True}
    before = deepcopy((patch, performance))
    a = render_piano_note(84, DURATION, SR, patch, velocity=0.75, performance=performance)
    b = render_piano_note(84, DURATION, SR, patch, velocity=0.75, performance=performance)
    np.testing.assert_array_equal(a, b)
    assert (patch, performance) == before
