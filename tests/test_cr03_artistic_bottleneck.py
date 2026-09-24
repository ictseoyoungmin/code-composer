import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator

from code_composer.core.song import song_fingerprint
from code_composer.execution import (
    PerformanceBridgeError,
    canonical_performance_score_json,
    compile_performance_score_to_render_ir,
    lower_song_to_execution_plan,
    performance_score_fingerprint,
    realize_instrument_mechanics,
    validate_performance_score,
)
from code_composer.execution.artistic_render import render_song_score_to_files


ROOT = Path(__file__).resolve().parents[1]
DOGFOOD = ROOT / "examples/cr03/quiet_thread"


def _song():
    return json.loads((DOGFOOD / "song.json").read_text(encoding="utf-8"))


def _score():
    return json.loads((DOGFOOD / "performance_score.json").read_text(encoding="utf-8"))


def _note_signature(ir):
    return {
        t["id"]: [
            (float(e["start_beat"]), float(e["duration_beats"]), int(e["midi"]))
            for e in t["events"] if "midi" in e
        ]
        for t in ir["tracks"]
    }


def test_cr03_dogfood_score_is_bound_to_exact_song():
    song = _song()
    score = _score()
    validate_performance_score(score)
    assert score["source_song"]["fingerprint"] == song_fingerprint(song)


def test_cr03_performance_score_schema_copies_match_and_accept_dogfood():
    source = ROOT / "skills/code-composer/kit/schemas/performance_score.schema.json"
    packaged = ROOT / "skills/code-composer/kit/src/code_composer/reference/schemas/performance_score.schema.json"
    assert source.read_bytes() == packaged.read_bytes()
    schema = json.loads(source.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(_score())


def test_cr03_score_fingerprint_is_key_order_independent():
    score = _score()
    reordered = dict(reversed(list(deepcopy(score).items())))
    assert canonical_performance_score_json(score) == canonical_performance_score_json(reordered)
    assert performance_score_fingerprint(score) == performance_score_fingerprint(reordered)
    assert len(performance_score_fingerprint(score)) == 64


def test_cr03_bridge_preserves_authored_note_pitch_timing_and_duration_exactly():
    plan = lower_song_to_execution_plan(_song())
    score = _score()
    ir = compile_performance_score_to_render_ir(plan, score)

    expected = {
        track["id"]: [
            (float(e["start_beat"]), float(e["duration_beats"]), int(e["midi"]))
            for e in track["events"] if e["type"] == "note"
        ]
        for track in score["tracks"]
    }
    assert _note_signature(ir) == expected

    realized = realize_instrument_mechanics(ir, plan)
    assert _note_signature(realized) == expected


def test_cr03_violin_uses_modeled_admittance_and_continuous_mechanical_realization():
    plan = lower_song_to_execution_plan(_song())
    violin = next(x for x in plan["instruments"] if x["id"] == "violin")
    assert violin["engine"] == "bowed_waveguide"
    assert violin["resolution"]["preset_id"] == "bowed.violin.modeled_admittance"
    assert violin["patch"]["bowed_waveguide_graph"]["continuous"]["enabled"] is True

    realized = realize_instrument_mechanics(
        compile_performance_score_to_render_ir(plan, _score()),
        plan,
    )
    report = realized["violin_performance_report"]
    assert report["playability"]["classification"] == "comfortable"
    track = next(t for t in realized["tracks"] if t["id"] == "violin-line")
    notes = [e for e in track["events"] if "midi" in e]
    assert len(notes) == 26
    assert all("violin_realization" in e["performance"] for e in notes)

    first_phrase = notes[:10]
    assert all(e["performance"]["articulation"] == "legato" for e in first_phrase[:9])
    for a, b in zip(first_phrase[:8], first_phrase[1:9]):
        assert float(a["start_beat"]) + float(a["duration_beats"]) == pytest.approx(float(b["start_beat"]))

    bow_groups = [e["performance"]["violin_realization"]["bow"]["group_id"] for e in first_phrase]
    # A long legato phrase may require a physical bow retake. The retake must not
    # become a score rest or note rewrite, and it should remain a small number of
    # continuous bow groups rather than per-note retriggering.
    assert 1 <= len(set(bow_groups[:9])) <= 2
    assert bow_groups[0] == bow_groups[5]
    assert bow_groups[6] == bow_groups[8]
    assert bow_groups[9] != bow_groups[8]


def test_cr03_piano_sustain_is_explicit_control_not_hidden_note_pedal():
    plan = lower_song_to_execution_plan(_song())
    ir = compile_performance_score_to_render_ir(plan, _score())
    piano = next(t for t in ir["tracks"] if t["id"] == "piano-foundation")
    controls = [e for e in piano["events"] if e.get("event_type") == "piano_control"]
    notes = [e for e in piano["events"] if "midi" in e]
    assert len(controls) == 10
    assert all(c["control"] == "sustain_pedal" for c in controls)
    assert all(not (e.get("performance") or {}).get("pedal") for e in notes)


def test_cr03_high_register_is_brief_apex_not_persistent_state():
    notes = [
        e for track in _score()["tracks"] if track["id"] == "violin-line"
        for e in track["events"] if e["type"] == "note"
    ]
    total = sum(float(e["duration_beats"]) for e in notes)
    high = sum(float(e["duration_beats"]) for e in notes if int(e["midi"]) >= 76)
    assert min(int(e["midi"]) for e in notes) == 62
    assert max(int(e["midi"]) for e in notes) == 77
    assert high / total < 0.10


def test_cr03_source_fingerprint_mismatch_is_hard_error():
    score = _score()
    score["source_song"]["fingerprint"] = "0" * 64
    plan = lower_song_to_execution_plan(_song())
    with pytest.raises(PerformanceBridgeError, match="source Song fingerprint"):
        compile_performance_score_to_render_ir(plan, score)


def test_cr03_sustain_control_on_violin_is_hard_error():
    score = _score()
    violin = next(t for t in score["tracks"] if t["id"] == "violin-line")
    violin["events"].append({
        "id": "bad-pedal",
        "type": "sustain_pedal",
        "start_beat": 39.75,
        "duration_beats": 0.25,
        "points": [
            {"offset_beats": 0.0, "position": 0.0},
            {"offset_beats": 0.25, "position": 1.0},
        ],
    })
    plan = lower_song_to_execution_plan(_song())
    with pytest.raises(PerformanceBridgeError, match="requires piano family"):
        compile_performance_score_to_render_ir(plan, score)


def test_cr03_score_tracks_must_match_plan_exactly():
    score = _score()
    score["tracks"] = score["tracks"][:1]
    score["render"]["mix"]["tracks"] = score["render"]["mix"]["tracks"][:1]
    plan = lower_song_to_execution_plan(_song())
    with pytest.raises(PerformanceBridgeError, match="tracks must exactly match"):
        compile_performance_score_to_render_ir(plan, score)


def test_cr03_new_path_has_no_fixed_role_or_register_shift_vocabulary():
    sources = [
        ROOT / "skills/code-composer/kit/src/code_composer/execution/performance_score.py",
        ROOT / "skills/code-composer/kit/src/code_composer/execution/render_bridge.py",
        ROOT / "skills/code-composer/kit/src/code_composer/execution/artistic_render.py",
    ]
    banned = (
        "CompositionBrief",
        "PITCHED_SOUND_ROLES",
        "SOUND_ROLES",
        "foreground_mode",
        "register_shift",
        "lead_density",
        "topline_density",
        "seed_ir",
    )
    text = "\n".join(p.read_text(encoding="utf-8") for p in sources)
    assert all(token not in text for token in banned)


def test_cr03_tiny_end_to_end_render_path_writes_finite_audio(tmp_path):
    song = {
        "format": "code-composer-song/v1",
        "meta": {"title": "One Note", "global_seed": 3},
        "transport": {"bpm": 120, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
        "tonal": {"root": "D", "scale": "natural_minor"},
        "sections": [{"id": "a", "bars": 1}],
        "instruments": [{
            "id": "piano", "family": "piano", "variant": "acoustic-grand",
            "render_lock": {"preset": "piano.concert_grand_natural", "preset_version": "1.0.0"},
        }],
        "tracks": [{"id": "p", "function": "single-note", "instrument": "piano"}],
        "materials": [{"id": "m", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": "part", "section": "a", "track": "p", "material": "m"}],
    }
    from code_composer.core.song import song_fingerprint
    score = {
        "format": "code-composer-performance-score/v1",
        "source_song": {"format": "code-composer-song/v1", "fingerprint": song_fingerprint(song)},
        "meta": {"title": "One Note"},
        "tracks": [{"id": "p", "events": [{
            "id": "n", "type": "note", "start_beat": 0, "duration_beats": 0.5,
            "midi": 62, "velocity": 0.4,
        }]}],
        "render": {
            "sample_rate": 8000,
            "tail_seconds": 0.1,
            "mix": {
                "tracks": [{"track": "p", "gain": 0.3, "pan": 0.0, "reverb_send": 0.0}],
                "music_bus_gain": 1.0, "room_return_gain": 0.0, "master_gain": 0.8,
            },
        },
    }
    wav = tmp_path / "one.wav"
    result = render_song_score_to_files(song, score, wav)
    assert wav.exists() and wav.stat().st_size > 100
    assert result["sr"] == 8000
    assert np.isfinite(result["audio"]).all()
    assert float(np.max(np.abs(result["audio"]))) < 1.0
