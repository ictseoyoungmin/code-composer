import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from code_composer.app.song_cli import main as song_cli_main
from code_composer.core.song import (
    SONG_FORMAT,
    SongValidationError,
    canonical_song_json,
    song_fingerprint,
    validate_song,
)
from code_composer.song_validation import (
    SongRuntimeValidationError,
    validate_song_for_runtime,
)


ROOT = Path(__file__).resolve().parents[1]


def _song():
    return json.loads((ROOT / "tests/fixtures/cr01_song.json").read_text(encoding="utf-8"))


def test_cr01_song_validates_without_seed_ir():
    song = _song()
    validate_song(song)
    validate_song_for_runtime(song)
    assert song["format"] == SONG_FORMAT
    assert {track["function"] for track in song["tracks"]} == {"harmonic-bed", "counterline"}


def test_cr01_track_function_is_not_a_fixed_role_enum():
    song = _song()
    song["tracks"][1]["function"] = "granular-shadow"
    validate_song(song)


def test_cr01_render_engine_is_not_required_for_instrument_identity():
    song = _song()
    song["instruments"][1].pop("render_lock")
    validate_song_for_runtime(song)
    assert song["instruments"][1]["family"] == "violin"


def test_cr01_non_tonal_song_is_legal_when_no_tonal_locks_exist():
    song = _song()
    song.pop("tonal")
    song["locks"] = {"bpm": 84}
    validate_song(song)


def test_cr01_duplicate_ids_are_rejected():
    song = _song()
    song["tracks"][1]["id"] = song["tracks"][0]["id"]
    with pytest.raises(SongValidationError, match="duplicate id"):
        validate_song(song)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("section", "missing-section", "unknown section"),
        ("track", "missing-track", "unknown track"),
        ("material", "missing-material", "unknown material"),
    ],
)
def test_cr01_part_cross_references_are_hard_errors(field, value, message):
    song = _song()
    song["parts"][0][field] = value
    with pytest.raises(SongValidationError, match=message):
        validate_song(song)


def test_cr01_track_instrument_reference_is_hard_error():
    song = _song()
    song["tracks"][0]["instrument"] = "missing-instrument"
    with pytest.raises(SongValidationError, match="unknown instrument"):
        validate_song(song)


def test_cr01_hard_locks_guard_composer_revision():
    song = _song()
    song["transport"]["bpm"] = 86
    with pytest.raises(SongValidationError, match="locks.bpm"):
        validate_song(song)


def test_cr01_old_register_shift_surface_is_not_accepted():
    song = _song()
    song["tracks"][0]["register_shift"] = 12
    with pytest.raises(SongValidationError, match="unknown field"):
        validate_song(song)


def test_cr01_explicit_render_lock_must_match_runtime_preset_engine():
    song = _song()
    song["instruments"][0]["render_lock"]["engine"] = "generic"
    with pytest.raises(SongRuntimeValidationError, match="conflicts with preset engine"):
        validate_song_for_runtime(song)


def test_cr01_unknown_explicit_engine_fails_before_render():
    song = _song()
    song["instruments"][0]["render_lock"] = {"engine": "does-not-exist"}
    with pytest.raises(SongRuntimeValidationError, match="unknown engine"):
        validate_song_for_runtime(song)


def test_cr01_canonical_fingerprint_ignores_input_key_order():
    song = _song()
    reordered = dict(reversed(list(deepcopy(song).items())))
    assert canonical_song_json(song) == canonical_song_json(reordered)
    assert song_fingerprint(song) == song_fingerprint(reordered)
    assert len(song_fingerprint(song)) == 64


def test_cr01_schema_copies_match_and_accept_fixture():
    source = ROOT / "skills/code-composer/kit/schemas/song.schema.json"
    packaged = ROOT / "skills/code-composer/kit/src/code_composer/reference/schemas/song.schema.json"
    assert source.read_bytes() == packaged.read_bytes()

    schema = json.loads(source.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_song())


def test_cr01_song_cli_validates_seedlessly(tmp_path, capsys):
    song_path = tmp_path / "song.json"
    song_path.write_text(json.dumps(_song()), encoding="utf-8")
    assert song_cli_main(["validate", str(song_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is True
    assert payload["tracks"] == 2
    assert payload["sections"] == 2
    assert len(payload["fingerprint"]) == 64


def test_cr01_new_song_surface_has_no_legacy_seed_or_fixed_role_contract():
    song_source = (
        ROOT / "skills/code-composer/kit/src/code_composer/core/song.py"
    ).read_text(encoding="utf-8")
    cli_source = (
        ROOT / "skills/code-composer/kit/src/code_composer/app/song_cli.py"
    ).read_text(encoding="utf-8")

    banned = (
        "seed_ir",
        "PITCHED_SOUND_ROLES",
        "SOUND_ROLES",
        "foreground_mode",
        "register_shift_add",
        "CompositionBrief",
    )
    assert all(token not in song_source for token in banned)
    assert all(token not in cli_source for token in banned)
