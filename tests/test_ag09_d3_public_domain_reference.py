from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=spec_from_file_location("ag09_d3_pd",ROOT/"tools"/"render_ag09_d3_public_domain_reference.py")
MOD=module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def test_public_domain_reference_has_16_bars_and_recognizable_melody_contract():
    assert len(MOD.MELODY)==16
    assert len(MOD.BAR_HARMONY)==16
    events=MOD.build_melody_events()
    assert len(events)>=50
    assert {int(e["midi"]) for e in events}.issubset({60,62,64,65,67,69})


def test_public_domain_reference_chord_voicings_match_declared_harmony():
    cert=MOD.harmonic_certificate()
    assert cert["valid"] is True
    assert cert["voicing_chord_tones_valid"] is True
    assert cert["undeclared_non_chord_tone_count"]==0


def test_clean_and_expressive_share_identical_song_identity():
    song=MOD.build_song()
    clean=MOD.build_score(song,expressive=False)
    expressive=MOD.build_score(song,expressive=True)
    clean_mel=next(t for t in clean["tracks"] if t["id"]=="melody")["events"]
    expressive_mel=next(t for t in expressive["tracks"] if t["id"]=="melody")["events"]
    assert clean_mel==expressive_mel

    def chord_stream(score):
        rhythm=next(t for t in score["tracks"] if t["id"]=="rhythm")["events"]
        return [(e["midi"],e["start_beat"]) for e in rhythm]
    assert chord_stream(clean)==chord_stream(expressive)


def test_expressive_variant_only_adds_phrase_ending_dead_note_chokes():
    clean=MOD.build_rhythm_events(expressive=False)
    expressive=MOD.build_rhythm_events(expressive=True)
    assert len(clean)==len(expressive)
    clean_muted=sum(e["instrument_performance"]["strum"]["state"]=="muted" for e in clean)
    expressive_muted=sum(e["instrument_performance"]["strum"]["state"]=="muted" for e in expressive)
    assert clean_muted==0
    assert expressive_muted>0


def test_public_domain_provenance_is_explicit():
    p=MOD.PUBLIC_DOMAIN_PROVENANCE
    assert p["work"]=="Oh! Susanna"
    assert p["composer"]=="Stephen Collins Foster"
    assert p["year"]==1848
    assert "loc.gov" in p["loc_reference"]
    assert "commons.wikimedia.org" in p["public_domain_scan"]


def test_reference_uses_final_ag08_preset_and_24k():
    song=MOD.build_song()
    score=MOD.build_score(song,expressive=True)
    assert all(i["render_lock"]["preset"]=="acoustic_guitar.steel_stateful_performance" for i in song["instruments"])
    assert score["render"]["sample_rate"]==24000
    assert score["render"]["mix"]["room_return_gain"]==0.0
