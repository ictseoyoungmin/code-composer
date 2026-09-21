import hashlib

import numpy as np

from code_composer.audio.engines import engine_for_patch
from code_composer.percussion import render_drum_event
from code_composer.presets import materialize_preset, list_presets

SR = 24000


def _hash(x):
    return hashlib.sha256(x.tobytes()).hexdigest()


def _mono(x):
    return 0.5 * (x[:, 0] + x[:, 1])


def _window_rms(x, a, b):
    y = _mono(x)[int(a * SR):int(b * SR)]
    return float(np.sqrt(np.mean(y * y)) + 1e-12)


def _band_energy_ratio(x, t0, low_band, high_band, window_s=.015):
    y = _mono(x)[int(t0 * SR):int((t0 + window_s) * SR)]
    w = np.hanning(len(y))
    p = np.abs(np.fft.rfft(y * w)) ** 2
    f = np.fft.rfftfreq(len(y), 1 / SR)
    def energy(band):
        lo, hi = band
        return float(p[(f >= lo) & (f < hi)].sum() + 1e-12)
    return energy(high_band) / energy(low_band)




def _band_fraction(x, t0, t1, band):
    y = _mono(x)[int(t0 * SR):int(t1 * SR)]
    w = np.hanning(len(y))
    p = np.abs(np.fft.rfft(y * w)) ** 2
    f = np.fft.rfftfreq(len(y), 1 / SR)
    total = float(p[(f >= 40) & (f < 11500)].sum() + 1e-12)
    lo, hi = band
    return float(p[(f >= lo) & (f < hi)].sum() / total)

def _preset():
    return materialize_preset('drums.s19_core_cymbal_extension', role='drums')


def test_s25_s19_checkpoint_preset_is_registered():
    ids = [x['preset_id'] for x in list_presets()]
    assert 'drums.s19_core_cymbal_extension' in ids
    patch = _preset()
    assert patch['drum_graph']['cymbal_extension']['enabled'] is True
    assert engine_for_patch(patch).tail_seconds(patch) == 1.65


def test_s25_preserves_s19_legacy_core_byte_exactly():
    patch = _preset()
    expected = {
        'kick': '6b2a723048822690dabed02cb2b422cf7d4fb98d229b8259fb0d54acb2191643',
        'snare': 'b0fd58a055ce6ea7f725988df064a7e8a6f1eecb960e930559e083858bc24025',
        'hat': 'f7536f79fe0f48141adaabcd2461a11c16b5fbe7b8d27e4b8637adbba35b2ca4',
    }
    for kind, digest in expected.items():
        y = render_drum_event(kind, .1, SR, .8, seed=17, patch=patch)
        assert _hash(y) == digest


def test_s25_does_not_change_existing_s17_modeled_preset_hashes():
    patch = materialize_preset('drums.acoustic_kit_modeled', role='drums')
    expected = {
        'kick': '380e698edfe82884757e23a81f8318a61d973968ba8c4c11e8a99d450a034df6',
        'snare': 'aaf1e8e3e15d2e64d746a6d635716a0db3e71c122a25c86cc79ae8382686ecaf',
        'hat': '7b6b0613fdbc8af958d7a1c57f0faeb3c3693ec2ca0f5c1d7b168b23e06cd558',
    }
    for kind, digest in expected.items():
        y = render_drum_event(kind, .1, SR, .8, seed=17, patch=patch)
        assert _hash(y) == digest


def test_s25_ride_and_crash_are_deterministic_seed_sensitive_and_bounded():
    patch = _preset()
    for kind in ('ride', 'crash'):
        a = render_drum_event(kind, .1, SR, .88, seed=41, patch=patch)
        b = render_drum_event(kind, .1, SR, .88, seed=41, patch=patch)
        c = render_drum_event(kind, .1, SR, .88, seed=42, patch=patch)
        assert np.array_equal(a, b)
        assert not np.array_equal(a, c)
        assert float(np.max(np.abs(a))) < .5
        assert _window_rms(a, .35, .55) > 1e-4


def test_s25_crash_has_delayed_high_frequency_bloom():
    crash = render_drum_event('crash', .1, SR, .9, seed=17, patch=_preset())
    early = _band_energy_ratio(crash, 0.0, (100, 700), (3000, 10000))
    bloom = _band_energy_ratio(crash, .060, (100, 700), (3000, 10000))
    assert early < .25
    assert bloom > early * 5.0


def test_s25_ride_keeps_stick_definition_without_crash_style_bloom():
    ride = render_drum_event('ride', .1, SR, .9, seed=17, patch=_preset())
    early = _band_energy_ratio(ride, 0.0, (100, 700), (3000, 10000))
    later = _band_energy_ratio(ride, .060, (100, 700), (3000, 10000))
    assert early > 1.0
    assert later < early * 1.8
    assert _window_rms(ride, .70, 1.00) > 1e-4


def test_s25_cymbal_r2_rejects_long_tonal_smear():
    patch = _preset()
    ride = render_drum_event('ride', .1, SR, .9, seed=17, patch=patch)
    crash = render_drum_event('crash', .1, SR, .9, seed=17, patch=patch)
    ride_onset = _window_rms(ride, .03, .12)
    ride_late = _window_rms(ride, .85, 1.05)
    crash_onset = _window_rms(crash, .03, .12)
    crash_late = _window_rms(crash, .85, 1.05)
    assert ride_late / ride_onset < .30
    assert crash_late / crash_onset < .48

def test_s25_cymbal_r3_ride_presence_is_mid_forward_without_tail_regression():
    ride = render_drum_event('ride', .1, SR, .9, seed=17, patch=_preset())
    presence = _band_fraction(ride, .03, .35, (2000, 6000))
    upper_air = _band_fraction(ride, .03, .35, (6000, 11000))
    assert presence > .43
    assert upper_air < .26
    assert _window_rms(ride, .85, 1.05) / _window_rms(ride, .03, .12) < .24



def test_s25_cymbal_r4_recovers_presence_without_reopening_tail():
    patch = _preset()
    ride = render_drum_event('ride', .1, SR, .9, seed=17, patch=patch)
    crash = render_drum_event('crash', .1, SR, .9, seed=17, patch=patch)

    ride_presence = _band_fraction(ride, .03, .35, (2000, 6000))
    ride_air = _band_fraction(ride, .03, .35, (6000, 11000))
    assert ride_presence > .52
    assert ride_air < .22
    assert _window_rms(ride, .03, .12) > .05
    assert _window_rms(ride, .85, 1.05) / _window_rms(ride, .03, .12) < .24

    crash_presence = _band_fraction(crash, .03, .35, (2000, 6000))
    crash_air = _band_fraction(crash, .03, .35, (6000, 11000))
    assert crash_presence > .44
    assert crash_air < .15
    assert _window_rms(crash, .03, .12) > .058
    assert _window_rms(crash, .85, 1.05) / _window_rms(crash, .03, .12) < .48

    early = _band_energy_ratio(crash, 0.0, (100, 700), (3000, 10000))
    bloom = _band_energy_ratio(crash, .060, (100, 700), (3000, 10000))
    assert early < .25
    assert bloom > early * 5.0


def test_s25_cymbal_r5_performance_velocity_opens_strike_authority_without_tail_growth():
    patch = _preset()
    ride_soft = render_drum_event('ride', .1, SR, .45, seed=17, patch=patch)
    ride_accent = render_drum_event('ride', .1, SR, 1.0, seed=17, patch=patch)
    crash_soft = render_drum_event('crash', .1, SR, .45, seed=17, patch=patch)
    crash_accent = render_drum_event('crash', .1, SR, 1.0, seed=17, patch=patch)

    # Authored velocity must alter excitation hierarchy, not merely multiply a
    # fixed sample-like shape. Strong accents gain disproportionate onset energy.
    assert _window_rms(ride_accent, 0.0, .03) / _window_rms(ride_soft, 0.0, .03) > 2.70
    assert _window_rms(crash_accent, 0.0, .03) / _window_rms(crash_soft, 0.0, .03) > 2.80

    # Soft timekeeping / touch crashes must remain bounded rather than inheriting
    # the accent transient at a lower output gain.
    assert _window_rms(ride_soft, 0.0, .03) < .030
    assert _window_rms(crash_soft, 0.0, .03) < .023

    # High-velocity authority is allowed to change attack and bloom, never the
    # established R2/R4 sustain limits.
    assert _window_rms(ride_accent, .85, 1.05) / _window_rms(ride_accent, .03, .12) < .24
    assert _window_rms(crash_accent, .85, 1.05) / _window_rms(crash_accent, .03, .12) < .48
