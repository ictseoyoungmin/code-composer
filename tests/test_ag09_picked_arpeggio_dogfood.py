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
    assert song["meta"]["revision"] == "AG09-D2-R2"


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
    assert song["meta"]["revision"] == "AG09-D2-R2"


def test_ag09_d2_harmonic_plan_matches_every_authored_pitch():
    cert = MOD.harmonic_plan_certificate(MOD.build_events())
    assert cert["valid"] is True
    assert cert["undeclared_non_chord_tone_count"] == 0
    assert len(cert["bars"]) == 12
    assert [b["label"] for b in cert["bars"]] == [
        "Em(add9)", "Cmaj7", "G6", "D/F#", "Em7", "Cmaj9",
        "Am7", "B7", "Em/G", "Cmaj7", "B7sus4->B7", "Em(add9)",
    ]
    assert all(b["required_pitch_classes_present"] for b in cert["bars"])


def test_ag09_d2_am7_actually_contains_g_seventh():
    bar7 = [
        e for e in MOD.build_events()
        if 24.0 <= float(e["start_beat"]) < 28.0
    ]
    pcs = {int(e["midi"]) % 12 for e in bar7}
    assert pcs == {0, 4, 7, 9}


def test_ag09_d2_b7_leading_tone_resolves_to_tonic_e():
    cert = MOD.harmonic_plan_certificate(MOD.build_events())
    res = cert["leading_tone_resolution"]
    assert res["source_midi"] % 12 == 3
    assert res["target_midi"] % 12 == 4
    assert res["direction_semitones"] == 1
    assert res["resolution_beats"] <= 0.5
