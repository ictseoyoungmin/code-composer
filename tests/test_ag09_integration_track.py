from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=spec_from_file_location("ag09_d5",ROOT/"tools"/"render_ag09_integration_track.py")
MOD=module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def test_d5_is_one_persistent_guitar_track_with_final_preset():
    song=MOD.build_song()
    assert len(song["tracks"])==1
    assert song["tracks"][0]["instrument"]=="guitar"
    assert song["instruments"][0]["render_lock"]["preset"]=="acoustic_guitar.steel_stateful_performance"
    assert song["sections"][0]["bars"]==16


def test_transition_bars_switch_technique_inside_same_performance():
    events,technique=MOD.build_events()
    assert technique[4]=="fingerstyle->picked"
    assert technique[8]=="picked->strum"
    assert technique[12]=="strum->percussive"
    assert technique[1]=="fingerstyle"
    assert technique[5]=="picked-arpeggio"
    assert technique[9]=="strumming"
    assert technique[13]=="percussive-fingerstyle"
    assert len({e["id"] for e in events})==len(events)


def test_integration_contains_all_required_mechanics():
    events,_=MOD.build_events()
    notes=[e for e in events if e["type"]=="note"]
    actions=[e for e in events if e["type"]=="instrument_action"]
    assert any(e["instrument_performance"].get("arpeggio",{}).get("player")!="pick" for e in notes)
    assert any(e["instrument_performance"].get("arpeggio",{}).get("player")=="pick" for e in notes)
    assert any("strum" in e["instrument_performance"] for e in notes)
    assert any(e["instrument_performance"].get("left_hand",{}).get("technique")=="dead_note" for e in notes)
    assert {e["action"] for e in actions}=={"top_slap","body_tap","string_slap"}


def test_harmony_is_declared_and_string_fret_authority_is_exact():
    events,_=MOD.build_events()
    cert=MOD.harmonic_certificate(events)
    assert cert["valid"] is True
    assert cert["undeclared_non_chord_tone_count"]==0
    for e in events:
        if e["type"]!="note":
            continue
        perf=e["instrument_performance"]
        assert e["midi"]==MOD.OPEN[perf["string"]]+perf["fret"]


def test_hybrid_transition_bars_have_events_on_both_sides_of_midbar():
    events,_=MOD.build_events()
    for bar in (4,8,12):
        start=(bar-1)*4.0
        rows=[e for e in events if start <= float(e["start_beat"]) < start+4.0]
        onsets={round(float(e["start_beat"])-start,6) for e in rows}
        assert any(x < 2.0 for x in onsets)
        assert any(x >= 2.0 for x in onsets)


def test_render_contract_is_24k_dry_and_human_gated():
    song=MOD.build_song(); score=MOD.build_score(song)
    assert score["render"]["sample_rate"]==24000
    assert score["render"]["mix"]["room_return_gain"]==0.0
    assert score["render"]["mix"]["tracks"][0]["reverb_send"]==0.0
