from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location(
    "ag09_fingerstyle",
    ROOT / "tools" / "render_ag09_fingerstyle_dogfood.py",
)
MOD = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def test_ag09_d1_has_12_bar_three_voice_fingerstyle_authority():
    events = MOD.build_events()
    assert len(events) == 96
    assert len({e["id"] for e in events}) == 96

    gestures = {}
    for event in events:
        perf = event["instrument_performance"]
        string = int(perf["string"])
        fret = int(perf["fret"])
        assert int(event["midi"]) == MOD.OPEN[string] + fret
        arp = perf["arpeggio"]
        gestures.setdefault(arp["gesture_id"], []).append(event)

        voice = arp["voice"]
        if voice == "bass":
            assert string in (4, 5, 6)
            assert arp["player"] == "thumb"
            assert perf["right_hand"]["method"] == "thumb"
        elif voice == "inner":
            assert string == 3
            assert arp["player"] == "index"
            assert perf["right_hand"]["method"] == "finger"
        else:
            assert voice == "treble"
            assert string in (1, 2)
            assert arp["player"] in ("middle", "ring")
            assert perf["right_hand"]["method"] == "finger"

    assert len(gestures) == 12
    for gesture_events in gestures.values():
        ordered = sorted(gesture_events, key=lambda e: e["start_beat"])
        assert [e["instrument_performance"]["arpeggio"]["sequence_index"] for e in ordered] == list(range(8))
        assert {e["instrument_performance"]["arpeggio"]["voice"] for e in ordered} == {
            "bass", "inner", "treble"
        }


def test_ag09_d1_has_no_independent_same_string_overlap():
    events = sorted(MOD.build_events(), key=lambda e: (e["start_beat"], e["id"]))
    by_string = {i: [] for i in range(1, 7)}
    for event in events:
        string = event["instrument_performance"]["string"]
        by_string[string].append(event)

    for string_events in by_string.values():
        for a, b in zip(string_events, string_events[1:]):
            assert float(a["start_beat"]) + float(a["duration_beats"]) <= float(b["start_beat"]) + 1e-12


def test_ag09_d1_uses_final_ag08_preset_and_fast_render_rate():
    song = MOD.build_song()
    score = MOD.build_score(song)
    lock = song["instruments"][0]["render_lock"]
    assert lock["preset"] == "acoustic_guitar.steel_stateful_performance"
    assert lock["preset_version"] == "1.0.0"
    assert score["render"]["sample_rate"] == 24000
    assert score["render"]["mix"]["room_return_gain"] == 0.0
    assert song["meta"]["revision"] == "AG09-D1-R0"


def test_ag09_d1_authored_gates_stay_inside_piece_timeline():
    timeline_beats = 12 * 4.0
    for event in MOD.build_events():
        assert float(event["start_beat"]) >= 0.0
        assert float(event["start_beat"]) + float(event["duration_beats"]) <= timeline_beats + 1e-12
