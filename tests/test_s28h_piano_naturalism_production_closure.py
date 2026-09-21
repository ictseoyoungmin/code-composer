from code_composer.presets import materialize_preset
from code_composer.audio.piano_design import resolve_piano_design


def _patch():
    return resolve_piano_design(materialize_preset('piano.concert_grand_natural_unison_subtle',role='piano'))


def test_s28h_production_preset_keeps_three_string_treble_and_mean_detune():
    strings=_patch()['piano_graph']['strings']
    assert strings['high_strings']==3
    assert strings['detune_cents']>0
    assert strings['unison_decoherence']['partial_mistune_cents']>0


def test_s28h_rejected_coupled_unison_transfer_is_not_present():
    strings=_patch()['piano_graph']['strings']
    assert 'unison_coupling_transfer' not in strings
    assert 'unison_coupling_tau_s' not in strings


def test_s28h_per_strike_identity_remains_enabled():
    strike=_patch()['piano_graph']['strike_identity']
    assert strike['phase_jitter_rad']>0
    assert strike['unison_phase_jitter_rad']>0
    assert strike['hammer_gain_variation']>0


def test_s28h_subtle_unison_is_treble_scoped():
    strings=_patch()['piano_graph']['strings']
    assert strings['unison_decoherence']['start_midi']>=61


def test_s28h_source_baseline_has_no_automatic_ducking_contract():
    # Ducking is a mix-plan decision, not an acoustic-piano preset behavior.
    patch=materialize_preset('piano.concert_grand_natural_unison_subtle',role='piano')
    text=str(patch).lower()
    assert 'duck' not in text
    assert 'sidechain' not in text
