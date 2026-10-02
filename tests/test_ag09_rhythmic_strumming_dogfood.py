from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=spec_from_file_location("ag09_d3",ROOT/"tools"/"render_ag09_rhythmic_strumming_dogfood.py")
MOD=module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def test_ag09_d3_has_12_bar_eighth_note_down_up_pattern():
    events=MOD.build_events()
    by_stroke={}
    for e in events:
        s=e["instrument_performance"]["strum"]
        by_stroke.setdefault(s["stroke_id"],[]).append(e)
    assert len(by_stroke)==96
    for bar in range(12):
        ids=[f"b{bar+1:02d}s{i}" for i in range(8)]
        assert all(i in by_stroke for i in ids)
        directions=[by_stroke[i][0]["instrument_performance"]["strum"]["direction"] for i in ids]
        assert directions==["down","up","down","up","down","up","down","up"]


def test_ag09_d3_muted_strokes_are_real_left_hand_dead_notes():
    events=MOD.build_events()
    muted={}
    for e in events:
        perf=e["instrument_performance"]
        s=perf["strum"]
        if s["state"]=="muted":
            muted.setdefault(s["stroke_id"],[]).append(e)
            assert perf["left_hand"]["technique"]=="dead_note"
        else:
            assert "left_hand" not in perf
    assert len(muted)==24
    for stroke_id,group in muted.items():
        idx=int(stroke_id.split("s")[-1])
        assert idx in MOD.MUTED_STROKES
        assert all(e["duration_beats"]==0.18 for e in group)


def test_ag09_d3_harmonic_plan_matches_every_bar():
    cert=MOD.harmonic_certificate(MOD.build_events())
    assert cert["valid"] is True
    assert cert["undeclared_non_chord_tone_count"]==0
    assert [b["chord"] for b in cert["bars"]]==MOD.BAR_CHORDS


def test_ag09_d3_preserves_string_fret_pitch_identity():
    for e in MOD.build_events():
        perf=e["instrument_performance"]
        string=int(perf["string"])
        fret=int(perf["fret"])
        assert int(e["midi"])==MOD.OPEN[string]+fret


def test_ag09_d3_strong_beats_have_local_accent_not_uniform_velocity_hack():
    events=MOD.build_events()
    by_stroke={}
    for e in events:
        s=e["instrument_performance"]["strum"]
        by_stroke.setdefault(s["stroke_id"],s)
    for stroke_id,s in by_stroke.items():
        idx=int(stroke_id.split("s")[-1])
        if idx in {0,4}:
            assert s["accent_amount"]==0.34
        elif idx in {2,6}:
            assert s["accent_amount"]==0.16
        else:
            assert s["accent_amount"]==0.06


def test_ag09_d3_uses_final_ag08_preset_and_24k():
    song=MOD.build_song()
    score=MOD.build_score(song)
    assert song["meta"]["revision"]=="AG09-D3-R0"
    assert song["instruments"][0]["render_lock"]=={
        "preset":"acoustic_guitar.steel_stateful_performance",
        "preset_version":"1.0.0",
    }
    assert score["render"]["sample_rate"]==24000
    assert score["render"]["mix"]["room_return_gain"]==0.0
