import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from code_composer.app.song_cli import main as song_cli_main
from code_composer.execution import (
    SongLoweringError,
    execution_plan_fingerprint,
    lower_song_to_execution_plan,
    validate_execution_plan,
)


ROOT = Path(__file__).resolve().parents[1]


def _song():
    return json.loads((ROOT / "tests/fixtures/cr01_song.json").read_text(encoding="utf-8"))


def _material(plan, material_id):
    return next(x for x in plan["materials"] if x["id"] == material_id)


def _instrument(plan, instrument_id):
    return next(x for x in plan["instruments"] if x["id"] == instrument_id)


def test_cr02_lowers_seedlessly_and_preserves_arbitrary_track_functions():
    song = _song()
    plan = lower_song_to_execution_plan(song)
    validate_execution_plan(plan)

    assert plan["format"] == "code-composer-execution-plan/v1"
    assert [x["function"] for x in plan["tracks"]] == ["harmonic-bed", "counterline"]
    assert plan["sections"][0]["start_beat"] == 0
    assert plan["sections"][1]["start_beat"] == 8
    assert len(plan["part_instances"]) == 7


def test_cr02_hidden_082_gate_cannot_shorten_authored_material_duration():
    plan = lower_song_to_execution_plan(_song())
    thread = _material(plan, "thread")
    assert thread["duration_beats"] == pytest.approx(4.0)

    instances = [
        x for x in plan["part_instances"]
        if x["source_part"] == "theme-thread"
    ]
    assert [x["duration_beats"] for x in instances] == pytest.approx([4.0] * 4)
    assert [x["start_beat"] for x in instances] == pytest.approx([8.0, 12.0, 16.0, 20.0])


def test_cr02_explicit_preset_locks_materialize_expected_runtime_engines():
    plan = lower_song_to_execution_plan(_song())
    piano = _instrument(plan, "piano-a")
    violin = _instrument(plan, "violin-a")

    assert piano["engine"] == "piano"
    assert piano["resolution"] == {
        "source": "explicit_preset_lock",
        "preset_id": "piano.concert_grand_natural",
        "preset_version": "1.0.0",
    }
    assert violin["engine"] == "bowed_waveguide"
    assert violin["resolution"]["preset_id"] == "bowed.violin.modeled_continuous"
    assert violin["patch"]["preset_provenance"]["preset_id"] == "bowed.violin.modeled_continuous"


def test_cr02_unlocked_known_family_uses_documented_capability_default():
    song = _song()
    for instrument in song["instruments"]:
        instrument.pop("render_lock")
    plan = lower_song_to_execution_plan(song)
    assert _instrument(plan, "piano-a")["resolution"]["source"] == "family_default"
    assert _instrument(plan, "violin-a")["resolution"]["source"] == "family_default"
    assert _instrument(plan, "violin-a")["engine"] == "bowed_waveguide"


def test_cr02_engine_only_lock_uses_compatible_family_default():
    song = _song()
    song["instruments"][1]["render_lock"] = {"engine": "bowed_waveguide"}
    plan = lower_song_to_execution_plan(song)
    violin = _instrument(plan, "violin-a")
    assert violin["resolution"]["source"] == "engine_lock_family_default"
    assert violin["resolution"]["preset_id"] == "bowed.violin.modeled_continuous"


def test_cr02_never_falls_back_to_generic_for_unknown_family_variant():
    song = _song()
    song["instruments"][1].pop("render_lock")
    song["instruments"][1]["variant"] = "unknown-violin-variant"
    with pytest.raises(SongLoweringError, match="add an explicit render_lock.preset"):
        lower_song_to_execution_plan(song)


def test_cr02_explicit_family_engine_mismatch_is_hard_error():
    song = _song()
    song["instruments"][1]["render_lock"] = {
        "engine": "generic",
        "preset": "generic.clean_lead",
        "preset_version": "1.0.0",
    }
    with pytest.raises(SongLoweringError, match="requires runtime engine"):
        lower_song_to_execution_plan(song)


def test_cr02_authored_valid_but_runtime_unsupported_scale_fails_explicitly():
    song = _song()
    song["tonal"]["scale"] = "harmonic_minor"
    song["locks"]["scale"] = "harmonic_minor"
    with pytest.raises(SongLoweringError, match="authored-valid but unsupported"):
        lower_song_to_execution_plan(song)


def test_cr02_progression_without_rhythm_is_not_given_a_hidden_duration():
    song = _song()
    home = next(x for x in song["materials"] if x["id"] == "home")
    home.pop("rhythm")
    with pytest.raises(SongLoweringError, match="progression rhythm is required"):
        lower_song_to_execution_plan(song)


def test_cr02_repeated_part_must_fit_inside_section():
    song = _song()
    part = next(x for x in song["parts"] if x["id"] == "theme-thread")
    part["repeats"] = 5
    with pytest.raises(SongLoweringError, match="outside section"):
        lower_song_to_execution_plan(song)


def test_cr02_non_tonal_rhythm_only_song_can_lower():
    song = {
        "format": "code-composer-song/v1",
        "meta": {"title": "Pulse", "global_seed": 7},
        "transport": {"bpm": 100, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
        "sections": [{"id": "a", "bars": 1}],
        "instruments": [{"id": "kit", "family": "drums", "variant": "acoustic-kit"}],
        "tracks": [{"id": "pulse", "function": "rhythmic-grid", "instrument": "kit"}],
        "materials": [{
            "id": "grid",
            "kind": "rhythm",
            "cycle_beats": 4,
            "steps": [
                {"beat": 0, "weight": 1.0},
                {"beat": 2, "weight": 0.8},
            ],
        }],
        "parts": [{"id": "grid-a", "section": "a", "track": "pulse", "material": "grid"}],
    }
    plan = lower_song_to_execution_plan(song)
    assert "tonal" not in plan
    assert _instrument(plan, "kit")["engine"] == "percussion"
    assert plan["part_instances"][0]["duration_beats"] == pytest.approx(4.0)


def test_cr02_plan_fingerprint_is_deterministic():
    a = lower_song_to_execution_plan(_song())
    b = lower_song_to_execution_plan(deepcopy(_song()))
    assert a == b
    assert execution_plan_fingerprint(a) == execution_plan_fingerprint(b)
    assert len(execution_plan_fingerprint(a)) == 64


def test_cr02_execution_schema_copies_match_and_accept_lowered_plan():
    source = ROOT / "skills/code-composer/kit/schemas/execution_plan.schema.json"
    packaged = ROOT / "skills/code-composer/kit/src/code_composer/reference/schemas/execution_plan.schema.json"
    assert source.read_bytes() == packaged.read_bytes()
    schema = json.loads(source.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(lower_song_to_execution_plan(_song()))


def test_cr02_song_cli_lower_writes_plan_and_fingerprints(tmp_path, capsys):
    song_path = tmp_path / "song.json"
    plan_path = tmp_path / "plan.json"
    song_path.write_text(json.dumps(_song()), encoding="utf-8")

    assert song_cli_main(["lower", str(song_path), str(plan_path)]) == 0
    output = json.loads(capsys.readouterr().out)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    validate_execution_plan(plan)

    assert output["part_instances"] == 7
    assert output["plan_fingerprint"] == execution_plan_fingerprint(plan)
    assert len(output["source_fingerprint"]) == 64


def test_cr02_lowering_source_has_no_legacy_seed_role_or_register_shift_vocabulary():
    source = (
        ROOT / "skills/code-composer/kit/src/code_composer/execution/lowering.py"
    ).read_text(encoding="utf-8")
    banned = (
        "seed_ir",
        "CompositionBrief",
        "PITCHED_SOUND_ROLES",
        "SOUND_ROLES",
        "foreground_mode",
        "register_shift",
        "lead_density",
        "topline_density",
    )
    assert all(token not in source for token in banned)
