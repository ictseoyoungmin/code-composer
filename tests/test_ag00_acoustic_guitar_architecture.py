import json
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator

from code_composer.audio.engines import engine_capabilities, engine_for_patch
from code_composer.core.song import song_fingerprint
from code_composer.execution import (
    PerformanceBridgeError,
    compile_performance_score_to_render_ir,
    lower_song_to_execution_plan,
    realize_instrument_mechanics,
    validate_performance_score,
)
from code_composer.execution.artistic_render import render_song_score_to_files
from code_composer.presets import materialize_preset


ROOT = Path(__file__).resolve().parents[1]


def _song():
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG00 One Note", "global_seed": 19},
        "transport": {"bpm": 96, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
        "tonal": {"root": "E", "scale": "major"},
        "sections": [{"id": "a", "bars": 1}],
        "instruments": [{
            "id": "guitar",
            "family": "acoustic_guitar",
            "variant": "steel-string",
            "render_lock": {
                "preset": "acoustic_guitar.steel_foundation",
                "preset_version": "1.0.0",
            },
        }],
        "tracks": [{"id": "g", "function": "single-note", "instrument": "guitar"}],
        "materials": [{"id": "m", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": "part", "section": "a", "track": "g", "material": "m"}],
    }


def _score(song=None):
    song = song or _song()
    return {
        "format": "code-composer-performance-score/v1",
        "source_song": {"format": "code-composer-song/v1", "fingerprint": song_fingerprint(song)},
        "meta": {"title": "AG00 One Note"},
        "tracks": [{"id": "g", "events": [{
            "id": "n1", "type": "note", "start_beat": 0.0,
            "duration_beats": 0.5, "midi": 52, "velocity": 0.55,
        }]}],
        "render": {
            "sample_rate": 8000,
            "tail_seconds": 0.1,
            "mix": {
                "tracks": [{"track": "g", "gain": 0.5, "pan": 0.0, "reverb_send": 0.0}],
                "music_bus_gain": 1.0, "room_return_gain": 0.0, "master_gain": 0.8,
            },
        },
    }


def test_ag00_acoustic_guitar_preset_and_engine_are_dedicated_boundaries():
    patch = materialize_preset("acoustic_guitar.steel_foundation")
    engine = engine_for_patch(patch)
    assert engine.name == "acoustic_guitar"
    caps = engine_capabilities(patch)
    assert caps["extended_tail"] is True
    assert caps["instrument_performance"] is False
    assert caps["instrument_actions"] is False
    assert patch["preset_provenance"]["preset_id"] == "acoustic_guitar.steel_foundation"


def test_ag00_performance_score_schema_accepts_engine_scoped_payload_and_action():
    score = _score()
    score["tracks"][0]["events"] = [
        {
            "id": "n1", "type": "note", "start_beat": 0.0, "duration_beats": 0.5,
            "midi": 52, "velocity": 0.55,
            "instrument_performance": {"future_string": 6, "nested": {"flag": True}},
        },
        {
            "id": "a1", "type": "instrument_action", "start_beat": 0.75,
            "duration_beats": 0.1, "action": "future_body_tap",
            "parameters": {"zone": "lower_bout", "strength": 0.5},
        },
    ]
    validate_performance_score(score)
    schema = json.loads((ROOT / "skills/code-composer/kit/schemas/performance_score.schema.json").read_text())
    Draft202012Validator(schema).validate(score)


def test_ag00_engine_owns_payload_semantics_and_rejects_unsupported_future_fields():
    song = _song()
    score = _score(song)
    score["tracks"][0]["events"][0]["instrument_performance"] = {"string": 6}
    plan = lower_song_to_execution_plan(song)
    with pytest.raises(PerformanceBridgeError, match="does not support instrument_performance"):
        compile_performance_score_to_render_ir(plan, score)


def test_ag00_engine_owns_action_semantics_and_rejects_unsupported_future_actions():
    song = _song()
    score = _score(song)
    score["tracks"][0]["events"] = [{
        "id": "a1", "type": "instrument_action", "start_beat": 0.0,
        "duration_beats": 0.1, "action": "body_tap", "parameters": {"zone": "top"},
    }]
    plan = lower_song_to_execution_plan(song)
    with pytest.raises(PerformanceBridgeError, match="does not support instrument_action"):
        compile_performance_score_to_render_ir(plan, score)


def test_ag00_song_to_plan_to_ir_to_render_is_finite(tmp_path):
    song = _song()
    score = _score(song)
    plan = lower_song_to_execution_plan(song)
    instrument = plan["instruments"][0]
    assert instrument["engine"] == "acoustic_guitar"
    assert instrument["resolution"]["preset_id"] == "acoustic_guitar.steel_foundation"

    ir = compile_performance_score_to_render_ir(plan, score)
    realized = realize_instrument_mechanics(ir, plan)
    assert realized["tracks"][0]["events"][0]["midi"] == 52

    wav = tmp_path / "ag00.wav"
    result = render_song_score_to_files(song, score, wav)
    assert wav.exists() and wav.stat().st_size > 100
    assert result["sr"] == 8000
    assert np.isfinite(result["audio"]).all()
    assert float(np.max(np.abs(result["audio"]))) > 0.0
    assert float(np.max(np.abs(result["audio"]))) < 1.0


def test_ag00_mechanics_realization_is_engine_routed_not_family_branched():
    bridge = (ROOT / "skills/code-composer/kit/src/code_composer/execution/render_bridge.py").read_text()
    assert "realize_violin_performance" not in bridge
    assert "ViolinPerformanceError" not in bridge
    assert "realize_track_mechanics" in bridge
    bowed = (ROOT / "skills/code-composer/kit/src/code_composer/audio/engines/bowed_waveguide.py").read_text()
    assert "def realize_track_mechanics" in bowed
