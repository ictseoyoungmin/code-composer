import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from code_composer.audio.engines import registered_engines
from code_composer.agent.composition_brief import brief_from_dict, validate_brief
from code_composer.agent.composer_planner import compile_brief, apply_composer_plan
from code_composer.drum_analysis import analyze_drum_hit
from code_composer.percussion import render_drum_event
from code_composer.presets import materialize_preset, list_presets, PresetError

ROOT = Path(__file__).resolve().parents[1]
SR = 24000


def _preset():
    return materialize_preset('drums.acoustic_kit_modeled', role='drums')


def _hash(x):
    return hashlib.sha256(x.tobytes()).hexdigest()


def _rms(x):
    mono = 0.5 * (x[:, 0] + x[:, 1])
    return float(np.sqrt(np.mean(mono * mono)) + 1e-12)


def test_s17_registers_percussion_engine_and_factory_preset():
    assert 'percussion' in registered_engines()
    ids = [x['preset_id'] for x in list_presets()]
    assert 'drums.acoustic_kit_modeled' in ids
    patch = _preset()
    assert patch['engine'] == 'percussion'
    assert patch['kind'] == 'percussion'
    assert patch['drum_graph']['realism_hardening']['enabled'] is True


def test_s17_legacy_drum_path_is_byte_identical_to_s16_baseline():
    patch = {'kind': 'percussion'}
    expected = {
        'kick': '6b2a723048822690dabed02cb2b422cf7d4fb98d229b8259fb0d54acb2191643',
        'snare': 'b0fd58a055ce6ea7f725988df064a7e8a6f1eecb960e930559e083858bc24025',
        'hat': 'f7536f79fe0f48141adaabcd2461a11c16b5fbe7b8d27e4b8637adbba35b2ca4',
    }
    for kind in ('kick', 'snare', 'hat'):
        y = render_drum_event(kind, .1, SR, .8, seed=17, patch=patch)
        assert _hash(y) == expected[kind]


def test_s17_disabled_realism_block_is_legacy_identical():
    base = {'kind': 'percussion'}
    disabled = {'kind': 'percussion', 'drum_graph': {'realism_hardening': {'enabled': False}}}
    for kind in ('kick', 'snare', 'hat'):
        a = render_drum_event(kind, .1, SR, .8, seed=17, patch=base)
        b = render_drum_event(kind, .1, SR, .8, seed=17, patch=disabled)
        assert np.array_equal(a, b)


def test_s17_modeled_hits_are_deterministic_but_strike_seed_sensitive():
    patch = _preset()
    for kind in ('kick', 'snare', 'hat'):
        a = render_drum_event(kind, .08, SR, .78, seed=21, patch=patch)
        b = render_drum_event(kind, .08, SR, .78, seed=21, patch=patch)
        c = render_drum_event(kind, .08, SR, .78, seed=22, patch=patch)
        assert np.array_equal(a, b)
        assert not np.array_equal(a, c)
        assert float(np.max(np.abs(a))) < 1.0


def test_s17_velocity_changes_snare_brightness_not_only_gain():
    patch = _preset()
    low = render_drum_event('snare', .08, SR, .35, seed=17, patch=patch)
    high = render_drum_event('snare', .08, SR, .95, seed=17, patch=patch)
    a = analyze_drum_hit(low, SR)
    b = analyze_drum_hit(high, SR)
    assert b['centroid_hz'] > a['centroid_hz'] + 150.0
    # Normalize loudness to prove the waveforms differ beyond scalar gain.
    low_n = low / _rms(low)
    high_n = high / _rms(high)
    assert float(np.mean(np.abs(low_n - high_n))) > 0.05


def test_s17_hat_velocity_changes_decay_and_remains_air_dominant():
    patch = _preset()
    low = render_drum_event('hat', .06, SR, .35, seed=17, patch=patch)
    high = render_drum_event('hat', .06, SR, .95, seed=17, patch=patch)
    a = analyze_drum_hit(low, SR)
    b = analyze_drum_hit(high, SR)
    assert b['decay_time_s'] > a['decay_time_s'] + .012
    assert a['air_ratio_7k_16k'] > .60
    assert b['air_ratio_7k_16k'] > .60


def test_s17_snare_has_late_wire_rattle_energy_without_unbounded_tail():
    patch = _preset()
    modeled = render_drum_event('snare', .08, SR, .82, seed=31, patch=patch)
    legacy = render_drum_event('snare', .08, SR, .82, seed=31, patch={'kind': 'percussion'})
    def window_rms(x, a, b):
        mono = .5 * (x[:, 0] + x[:, 1])
        lo, hi = int(a * SR), min(len(mono), int(b * SR))
        return float(np.sqrt(np.mean(mono[lo:hi] ** 2)) + 1e-12)
    assert window_rms(modeled, .12, .20) > window_rms(legacy, .12, .20) * 1.8
    assert analyze_drum_hit(modeled, SR)['decay_time_s'] < .34


def test_s17_kick_membrane_tail_stays_low_frequency_and_bounded():
    patch = _preset()
    y = render_drum_event('kick', .08, SR, .9, seed=11, patch=patch)
    a = analyze_drum_hit(y, SR)
    assert a['low_ratio_20_120'] > .97
    assert a['centroid_hz'] < 90.0
    assert .20 < a['decay_time_s'] < .36
    assert float(np.max(np.abs(y))) < .8


def test_s17_drum_factory_preset_is_agent_selectable():
    seed = json.loads((ROOT / 'tests/fixtures/topline_ir.json').read_text())
    data = {
        'source_prompt': 'S17 drum-preset protocol test',
        'concept': 'modeled acoustic percussion',
        'hard_constraints': {},
        'transport': {'bpm': 96, 'beats_per_bar': 4},
        'tonal': {'root': 'D', 'scale': 'major'},
        'form': {'sections': [{'id': 'main', 'bars': 2, 'energy': .7}]},
        'materials': {'progression': [1, 5, 6, 4], 'motif': [0, 2, 4, 2], 'motif_rhythm': [.5, .5, .5, .5]},
        'rhythm': {'groove': {'steps_per_bar': 16, 'roles': {'kick': [0]*16, 'snare': [0]*16, 'hat': [0]*16}}, 'section_profiles': {'main': {'density': 0, 'kick': 0, 'snare': 0, 'hat': 0, 'fill': 0}}},
        'orchestration': {'sections': {'main': {'foreground_mode': 'lead'}}},
        'harmony': {'colors': ['triad']},
        'development': {'sections': {'main': {'stage': 'establish'}}},
        'transitions': {},
        'sound_palette': {'roles': {'drums': {'preset_id': 'drums.acoustic_kit_modeled'}}},
    }
    brief = brief_from_dict(data)
    validate_brief(brief, seed)
    out = apply_composer_plan(seed, compile_brief(seed, brief))
    iid = out['arrangement']['roles']['drums']['instrument']
    patch = out['instruments'][iid]
    assert patch['preset_provenance']['preset_id'] == 'drums.acoustic_kit_modeled'
    assert patch['engine'] == 'percussion'


def test_s17_invalid_realism_parameters_are_rejected():
    with pytest.raises(PresetError):
        materialize_preset(
            'drums.acoustic_kit_modeled', role='drums',
            patch_overrides={'drum_graph': {'realism_hardening': {'kick_tail_s': 5.0}}},
        )
