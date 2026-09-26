import json
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator

from code_composer.execution import (
    PreviewValidationError,
    apply_revision_plan,
    performance_score_fingerprint,
    validate_preview_request,
)
import code_composer.execution.preview as preview_module


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/cr03/lantern_current"
REVISION = ROOT / "examples/cr04/lantern_current_coda"
DOGFOOD = ROOT / "examples/cr05/lantern_current_preview"


def _song():
    return json.loads((SOURCE / "song.json").read_text(encoding="utf-8"))


def _score():
    return json.loads((SOURCE / "performance_score.json").read_text(encoding="utf-8"))


def _revision_plan():
    return json.loads((REVISION / "revision_plan.json").read_text(encoding="utf-8"))


def _request(name="original_request.json"):
    return json.loads((DOGFOOD / name).read_text(encoding="utf-8"))


def test_cr05_preview_request_schema_copies_match_and_accept_examples():
    source = ROOT / "skills/code-composer/kit/schemas/preview_request.schema.json"
    packaged = ROOT / "skills/code-composer/kit/src/code_composer/reference/schemas/preview_request.schema.json"
    assert source.read_bytes() == packaged.read_bytes()
    schema = json.loads(source.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    validator.validate(_request())
    validator.validate(_request("revised_request.json"))


def test_cr05_preview_report_schema_copies_match():
    source = ROOT / "skills/code-composer/kit/schemas/preview_report.schema.json"
    packaged = ROOT / "skills/code-composer/kit/src/code_composer/reference/schemas/preview_report.schema.json"
    assert source.read_bytes() == packaged.read_bytes()
    Draft202012Validator.check_schema(json.loads(source.read_text(encoding="utf-8")))


def test_cr05_preview_request_binds_exact_source_score():
    score = _score()
    req = _request()
    validate_preview_request(req)
    assert req["source_score"]["fingerprint"] == performance_score_fingerprint(score)

    wrong = json.loads(json.dumps(req))
    wrong["source_score"]["fingerprint"] = "0" * 64
    with pytest.raises(PreviewValidationError, match="source score fingerprint"):
        preview_module.render_song_score_preview(
            _song(), score, wrong, "/tmp/never.wav", "/tmp/never-cache"
        )


def test_cr05_bar_range_resolves_to_expected_beats():
    req = _request()
    start, end, source = preview_module._resolve_range(
        req, beats_per_bar=3, total_beats=36.0
    )
    assert start == pytest.approx(24.0)
    assert end == pytest.approx(36.0)
    assert source == {"mode": "bars", "start_bar": 9, "end_bar": 12}


def test_cr05_track_cache_identity_is_local_to_dry_stem_dependencies():
    score = _score()
    revised, _ = apply_revision_plan(score, _revision_plan())

    _, before_ir = preview_module._prepare_render_ir(_song(), score, 24000)
    _, after_ir = preview_module._prepare_render_ir(_song(), revised, 24000)

    before_tracks = {t["id"]: t for t in before_ir["tracks"]}
    after_tracks = {t["id"]: t for t in after_ir["tracks"]}
    beat_s = 60.0 / float(before_ir["transport"]["bpm"])
    n0 = preview_module._timeline_size(before_ir, 24000, beat_s)
    n1 = preview_module._timeline_size(after_ir, 24000, beat_s)
    assert n0 == n1

    violin_before = preview_module._stem_cache_identity(
        before_ir, before_tracks["violin-line"], n=n0, sr=24000, graph_mode=True
    )
    violin_after = preview_module._stem_cache_identity(
        after_ir, after_tracks["violin-line"], n=n1, sr=24000, graph_mode=True
    )
    piano_before = preview_module._stem_cache_identity(
        before_ir, before_tracks["piano-foundation"], n=n0, sr=24000, graph_mode=True
    )
    piano_after = preview_module._stem_cache_identity(
        after_ir, after_tracks["piano-foundation"], n=n1, sr=24000, graph_mode=True
    )

    assert preview_module._canonical_hash(violin_before) == preview_module._canonical_hash(violin_after)
    assert preview_module._canonical_hash(piano_before) != preview_module._canonical_hash(piano_after)


def test_cr05_cache_cold_then_warm_then_track_local_miss(tmp_path, monkeypatch):
    calls = []

    def fake_render(ir, track, n, sr, beat_s, graph_mode=False):
        calls.append(track["id"])
        signature = sum(
            int(e.get("midi", 0)) + int(round(float(e.get("velocity", 0)) * 100))
            for e in track.get("events", [])
        )
        value = (signature % 97 + 1) / 1000.0
        return np.full((n, 2), value, dtype=np.float64)

    monkeypatch.setattr(preview_module, "_render_dry_track", fake_render)

    ir = {
        "meta": {"global_seed": 7},
        "transport": {"bpm": 72.0, "beats_per_bar": 3},
        "instruments": {
            "piano": {"engine": "piano", "preset": "fake"},
            "violin": {"engine": "bowed_waveguide", "preset": "fake"},
        },
    }
    piano = {
        "id": "piano-foundation",
        "instrument": "piano",
        "events": [{"start_beat": 0.0, "duration_beats": 1.0, "midi": 60, "velocity": .5}],
    }
    violin = {
        "id": "violin-line",
        "instrument": "violin",
        "events": [{"start_beat": 0.0, "duration_beats": 1.0, "midi": 69, "velocity": .5}],
    }

    for track in (piano, violin):
        _, report = preview_module._load_or_render_stem(
            ir, track, n=128, sr=24000, beat_s=60/72, graph_mode=True, cache_dir=tmp_path
        )
        assert report["cache_hit"] is False
    assert calls == ["piano-foundation", "violin-line"]

    for track in (piano, violin):
        _, report = preview_module._load_or_render_stem(
            ir, track, n=128, sr=24000, beat_s=60/72, graph_mode=True, cache_dir=tmp_path
        )
        assert report["cache_hit"] is True
    assert calls == ["piano-foundation", "violin-line"]

    revised_piano = json.loads(json.dumps(piano))
    revised_piano["events"][0]["velocity"] = .4
    _, piano_report = preview_module._load_or_render_stem(
        ir, revised_piano, n=128, sr=24000, beat_s=60/72, graph_mode=True, cache_dir=tmp_path
    )
    _, violin_report = preview_module._load_or_render_stem(
        ir, violin, n=128, sr=24000, beat_s=60/72, graph_mode=True, cache_dir=tmp_path
    )
    assert piano_report["cache_hit"] is False
    assert violin_report["cache_hit"] is True
    assert calls == ["piano-foundation", "violin-line", "piano-foundation"]


def test_cr05_cache_renderer_epoch_is_explicit():
    assert preview_module.STEM_CACHE_RENDERER_EPOCH.startswith("cr05-renderer-epoch-")


def test_cr05_preview_is_explicitly_not_final_render_authority(tmp_path, monkeypatch):
    score = _score()
    req = _request()

    plan = preview_module.lower_song_to_execution_plan(_song())
    ir = {
        "meta": {"sample_rate": 24000, "global_seed": 1},
        "transport": {"bpm": 72.0, "beats_per_bar": 3},
        "instruments": {
            "piano": {"engine": "piano"},
            "violin": {"engine": "bowed_waveguide"},
        },
        "tracks": [
            {"id": "piano-foundation", "instrument": "piano", "events": []},
            {"id": "violin-line", "instrument": "violin", "events": []},
        ],
        "mix": {
            "tail_seconds": 0.0,
            "graph": {
                "tracks": {
                    "piano-foundation": {"gain": 1.0, "pan": 0.0, "output": "music", "sends": {}},
                    "violin-line": {"gain": 1.0, "pan": 0.0, "output": "music", "sends": {}},
                },
                "buses": {"music": {"kind": "group", "gain": 1.0, "output": "master", "fx": []}},
                "sidechains": [],
                "master": {"gain": 1.0, "fx": []},
            },
        },
    }
    monkeypatch.setattr(preview_module, "_prepare_render_ir", lambda *args, **kwargs: (plan, ir))
    monkeypatch.setattr(preview_module, "_timeline_size", lambda *args, **kwargs: 900000)
    monkeypatch.setattr(
        preview_module,
        "_render_dry_track",
        lambda ir, track, n, sr, beat_s, graph_mode=False: np.zeros((n, 2), dtype=np.float64),
    )

    result = preview_module.render_song_score_preview(
        _song(), score, req, tmp_path / "preview.wav", tmp_path / "cache"
    )
    assert result["report"]["authority"] == "draft-preview-only"
    assert result["report"]["final_render_authority"] is False
    assert result["report"]["range"]["start_beat"] == pytest.approx(24.0)
    assert result["report"]["range"]["end_beat"] == pytest.approx(36.0)
