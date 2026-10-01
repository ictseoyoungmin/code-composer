from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location(
    "ag09_picked_arpeggio",
    ROOT / "tools" / "render_ag09_picked_arpeggio_dogfood.py",
)
MOD = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def test_ag09_d2_has_12_bar_explicit_picked_arpeggio_authority():
    events = MOD.build_events()
    assert len(events) == 96
    gestures = {}
    for event in events:
        perf = event["instrument_performance"]
        string = int(perf["string"])
        fret = int(perf["fret"])
        assert int(event["midi"]) == MOD.OPEN[string] + fret
        right = perf["right_hand"]
        assert right["method"] == "pick"
        assert 0.03 <= float(right["pluck_position"]) <= 0.49
        assert 0.0 <= float(right["attack_angle_deg"]) <= 90.0
        assert 0.0 <= float(right["strength"]) <= 1.0
        arp = perf["arpeggio"]
        assert arp["player"] == "pick"
        gestures.setdefault(arp["gesture_id"], []).append(event)

    assert len(gestures) == 12
    for group in gestures.values():
        ordered = sorted(group, key=lambda e: e["start_beat"])
        assert [e["instrument_performance"]["arpeggio"]["sequence_index"] for e in ordered] == list(range(8))
        assert len({e["instrument_performance"]["string"] for e in group}) >= 5


def test_ag09_d2_contains_required_same_pitch_alternate_string_positions():
    events = MOD.build_events()
    by_pitch = {}
    for e in events:
        perf = e["instrument_performance"]
        by_pitch.setdefault(int(e["midi"]), set()).add((int(perf["string"]), int(perf["fret"])))
    assert {(3,0),(4,5)}.issubset(by_pitch[55])
    assert {(2,0),(3,4)}.issubset(by_pitch[59])
    assert {(1,0),(2,5)}.issubset(by_pitch[64])


def test_ag09_d2_has_no_same_string_state_overlap():
    events = sorted(MOD.build_events(), key=lambda e: (e["start_beat"], e["id"]))
    by_string = {i: [] for i in range(1, 7)}
    for e in events:
        by_string[int(e["instrument_performance"]["string"])].append(e)
    for group in by_string.values():
        for a,b in zip(group, group[1:]):
            assert float(a["start_beat"]) + float(a["duration_beats"]) <= float(b["start_beat"]) + 1e-12


def test_ag09_d2_uses_final_ag08_preset_and_24k():
    song = MOD.build_song()
    score = MOD.build_score(song)
    lock = song["instruments"][0]["render_lock"]
    assert lock["preset"] == "acoustic_guitar.steel_stateful_performance"
    assert lock["preset_version"] == "1.0.0"
    assert score["render"]["sample_rate"] == 24000
    assert score["render"]["mix"]["room_return_gain"] == 0.0
    assert song["meta"]["revision"] == "AG09-D2-R1"


def test_ag09_d2_has_real_harmonic_movement():
    # R1 must not collapse into one repeated chord shape.
    events = MOD.build_events()
    bars = []
    for bar in range(12):
        bar_events = [e for e in events if bar * 4.0 <= float(e["start_beat"]) < (bar + 1) * 4.0]
        pitch_classes = tuple(sorted({int(e["midi"]) % 12 for e in bar_events}))
        bass = min(int(e["midi"]) for e in bar_events)
        bars.append((pitch_classes, bass))
    assert len(set(bars)) >= 8

    song = MOD.build_song()
    assert song["meta"]["revision"] == "AG09-D2-R1"
