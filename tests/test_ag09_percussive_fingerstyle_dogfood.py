from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=spec_from_file_location("ag09_d4",ROOT/"tools"/"render_ag09_percussive_fingerstyle_dogfood.py")
MOD=module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def test_ag09_d4_single_track_contains_notes_and_real_guitar_actions():
    events=MOD.build_events()
    notes=[e for e in events if e["type"]=="note"]
    actions=[e for e in events if e["type"]=="instrument_action"]
    assert len(notes)==96
    assert len(actions)==24
    assert {e["action"] for e in actions}=={"top_slap","body_tap","string_slap"}
    assert sum(e["action"]=="top_slap" for e in actions)==12
    assert sum(e["action"]=="body_tap" for e in actions)==6
    assert sum(e["action"]=="string_slap" for e in actions)==6


def test_ag09_d4_actions_share_authored_onsets_with_pitched_playing():
    events=MOD.build_events()
    note_onsets={round(float(e["start_beat"]),9) for e in events if e["type"]=="note"}
    actions=[e for e in events if e["type"]=="instrument_action"]
    assert all(round(float(e["start_beat"]),9) in note_onsets for e in actions)


def test_ag09_d4_string_fret_authority_is_exact():
    for e in MOD.build_events():
        if e["type"]!="note":
            continue
        perf=e["instrument_performance"]
        string=int(perf["string"])
        fret=int(perf["fret"])
        assert int(e["midi"])==MOD.OPEN[string]+fret


def test_ag09_d4_harmony_has_no_undeclared_non_chord_tones():
    cert=MOD.harmonic_certificate(MOD.build_events())
    assert cert["valid"] is True
    assert cert["undeclared_non_chord_tone_count"]==0
    assert [row["chord"] for row in cert["bars"]]==MOD.BAR_CHORDS


def test_ag09_d4_has_no_drum_or_percussion_substitute_track():
    song=MOD.build_song()
    score=MOD.build_score(song)
    assert len(song["tracks"])==1
    assert song["tracks"][0]["instrument"]=="guitar"
    assert song["tracks"][0]["function"]=="percussive-fingerstyle"
    assert len(score["tracks"])==1
    assert score["tracks"][0]["id"]=="guitar"


def test_ag09_d4_uses_final_ag08_preset_and_24k():
    song=MOD.build_song()
    score=MOD.build_score(song)
    assert song["meta"]["revision"]=="AG09-D4-R0"
    assert song["instruments"][0]["render_lock"]=={
        "preset":"acoustic_guitar.steel_stateful_performance",
        "preset_version":"1.0.0",
    }
    assert score["render"]["sample_rate"]==24000
    assert score["render"]["mix"]["room_return_gain"]==0.0
