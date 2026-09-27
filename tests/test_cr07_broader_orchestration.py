import json
from pathlib import Path

import numpy as np

from code_composer.core.song import song_fingerprint
from code_composer.execution import (
    compile_performance_score_to_render_ir,
    execution_plan_fingerprint,
    lower_song_to_execution_plan,
    performance_score_fingerprint,
    realize_instrument_mechanics,
)
from code_composer.execution.performance_score import validate_performance_score
from code_composer.core.song import validate_song


ROOT = Path(__file__).resolve().parents[1]
DOGFOOD = ROOT / "examples/cr07"
CASES = ("copper_lines", "glass_courtyard", "blue_relay")
FIXED_ROLE_WORDS = {"lead", "harmony", "bass", "drums", "pad", "fx"}
KNOWN_DEFAULT_FAMILIES = {"piano", "violin", "bass", "drums"}


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _case(slug):
    base = DOGFOOD / slug
    return _load(base / "song.json"), _load(base / "performance_score.json")


def test_cr07_three_independent_ensembles_are_valid_and_source_bound():
    fps = set()
    for slug in CASES:
        song, score = _case(slug)
        validate_song(song)
        validate_performance_score(score)
        fp = song_fingerprint(song)
        assert score["source_song"]["fingerprint"] == fp
        fps.add(fp)
    assert len(fps) == len(CASES)


def test_cr07_track_functions_are_arbitrary_and_preserved_exactly():
    all_functions = set()
    for slug in CASES:
        song, score = _case(slug)
        plan = lower_song_to_execution_plan(song)
        authored = {t["id"]: t["function"] for t in song["tracks"]}
        lowered = {t["id"]: t["function"] for t in plan["tracks"]}
        assert lowered == authored
        assert not (set(authored.values()) & FIXED_ROLE_WORDS)
        all_functions.update(authored.values())
        assert [t["id"] for t in score["tracks"]] == [t["id"] for t in song["tracks"]]
    assert len(all_functions) >= 10


def test_cr07_unknown_instrument_families_are_explicitly_locked_not_fallbacks():
    unknown = []
    for slug in CASES:
        song, _ = _case(slug)
        plan = lower_song_to_execution_plan(song)
        plan_instruments = {i["id"]: i for i in plan["instruments"]}
        for instrument in song["instruments"]:
            if instrument["family"] in KNOWN_DEFAULT_FAMILIES:
                continue
            unknown.append((slug, instrument["id"], instrument["family"]))
            assert instrument["render_lock"]["preset"]
            resolved = plan_instruments[instrument["id"]]
            assert resolved["resolution"]["source"] == "explicit_preset_lock"
    assert {family for _, _, family in unknown} >= {
        "electric_guitar", "electric_keys", "cello", "synth_pad", "synth_lead"
    }


def test_cr07_realized_ir_preserves_exact_track_identity_and_authored_notes():
    for slug in CASES:
        song, score = _case(slug)
        plan = lower_song_to_execution_plan(song)
        ir = compile_performance_score_to_render_ir(plan, score)
        realized = realize_instrument_mechanics(ir, plan)
        expected_ids = [t["id"] for t in song["tracks"]]
        assert [t["id"] for t in realized["tracks"]] == expected_ids

        before = {
            t["id"]: [
                (float(e["start_beat"]), float(e["duration_beats"]), int(e["midi"]))
                for e in t["events"] if e["type"] == "note"
            ]
            for t in score["tracks"]
        }
        after = {
            t["id"]: [
                (float(e["start_beat"]), float(e["duration_beats"]), int(e["midi"]))
                for e in t["events"] if "midi" in e
            ]
            for t in realized["tracks"]
        }
        assert after == before


def test_cr07_lowering_is_deterministic_for_all_ensembles():
    for slug in CASES:
        song, score = _case(slug)
        a = lower_song_to_execution_plan(song)
        b = lower_song_to_execution_plan(song)
        assert execution_plan_fingerprint(a) == execution_plan_fingerprint(b)
        assert performance_score_fingerprint(score) == performance_score_fingerprint(score)


def test_cr07_fixtures_are_materially_distinct():
    rows = []
    for slug in CASES:
        song, score = _case(slug)
        rows.append((
            song["transport"]["bpm"],
            song["transport"]["meter"]["beats_per_bar"],
            len(song["tracks"]),
            tuple(sorted(i["family"] for i in song["instruments"])),
            sum(len(t["events"]) for t in score["tracks"]),
        ))
    assert len(set(rows)) == len(CASES)
