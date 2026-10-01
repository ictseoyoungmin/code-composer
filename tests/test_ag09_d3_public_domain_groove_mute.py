from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location(
    "ag09_d3_pd_mute",
    ROOT / "tools" / "render_ag09_d3_public_domain_groove_mute.py",
)
MOD = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def test_groove_mute_keeps_same_public_domain_song_identity():
    song = MOD.BASE.build_song()
    score = MOD.build_score(song)
    melody = next(t for t in score["tracks"] if t["id"] == "melody")["events"]
    assert melody == MOD.BASE.build_melody_events()
    assert len(melody) == 53


def test_groove_mute_has_64_strokes_and_20_muted_strokes():
    rhythm = MOD.build_groove_rhythm_events()
    strokes = {}
    for event in rhythm:
        s = event["instrument_performance"]["strum"]
        strokes.setdefault(s["stroke_id"], []).append(event)
    assert len(strokes) == 64
    muted = {
        stroke_id
        for stroke_id, group in strokes.items()
        if group[0]["instrument_performance"]["strum"]["state"] == "muted"
    }
    assert len(muted) == 20


def test_regular_mute_is_first_offbeat_and_phrase_end_adds_second_offbeat():
    rhythm = MOD.build_groove_rhythm_events()
    by_stroke = {}
    for event in rhythm:
        s = event["instrument_performance"]["strum"]
        by_stroke.setdefault(s["stroke_id"], s)

    for bar in range(16):
        assert by_stroke[f"m-b{bar+1:02d}s1"]["state"] == "muted"
        expected = "muted" if bar in MOD.PHRASE_END_BARS else "sounding"
        assert by_stroke[f"m-b{bar+1:02d}s3"]["state"] == expected


def test_muted_strokes_use_left_hand_dead_note_not_gain_ducking():
    for event in MOD.build_groove_rhythm_events():
        perf = event["instrument_performance"]
        state = perf["strum"]["state"]
        if state == "muted":
            assert perf["left_hand"]["technique"] == "dead_note"
            assert event["duration_beats"] == 0.18
        else:
            assert "left_hand" not in perf


def test_groove_mute_keeps_public_domain_harmony_contract():
    cert = MOD.BASE.harmonic_certificate()
    assert cert["valid"] is True
    assert cert["voicing_chord_tones_valid"] is True
    assert cert["undeclared_non_chord_tone_count"] == 0


def test_groove_mute_uses_final_ag08_preset_and_24k():
    song = MOD.BASE.build_song()
    score = MOD.build_score(song)
    assert all(i["render_lock"]["preset"] == "acoustic_guitar.steel_stateful_performance" for i in song["instruments"])
    assert score["render"]["sample_rate"] == 24000
    assert score["render"]["mix"]["room_return_gain"] == 0.0
