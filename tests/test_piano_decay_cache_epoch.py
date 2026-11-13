"""Old preview stems must not mask either piano decay correction."""
import numpy as np
import pytest

from code_composer.execution import preview


@pytest.mark.parametrize("old_epoch", ["cr05-renderer-epoch-1", "cr05-renderer-epoch-2"])
def test_piano_decay_fix_invalidates_pre_fix_stems(tmp_path, monkeypatch, old_epoch):
    current_epoch = preview.STEM_CACHE_RENDERER_EPOCH
    assert current_epoch != old_epoch
    ir = {
        "transport": {"bpm": 120, "beats_per_bar": 4},
        "meta": {"global_seed": 0},
        "instruments": {"p": {"kind": "piano"}},
    }
    track = {"id": "piano", "instrument": "p", "events": []}
    calls = []

    def render(ir, track, n, sr, beat_s, *, graph_mode):
        calls.append(preview.STEM_CACHE_RENDERER_EPOCH)
        return np.full((n, 2), 0.125, dtype=np.float64)

    monkeypatch.setattr(preview, "_render_dry_track", render)
    kwargs = dict(n=32, sr=24000, beat_s=0.5, graph_mode=True, cache_dir=tmp_path)
    with monkeypatch.context() as old:
        old.setattr(preview, "STEM_CACHE_RENDERER_EPOCH", old_epoch)
        _, stale = preview._load_or_render_stem(ir, track, **kwargs)
        _, old_hit = preview._load_or_render_stem(ir, track, **kwargs)
        assert not stale["cache_hit"] and old_hit["cache_hit"]

    fresh_audio, fresh = preview._load_or_render_stem(ir, track, **kwargs)
    cached_audio, hit = preview._load_or_render_stem(ir, track, **kwargs)
    assert not fresh["cache_hit"]
    assert hit["cache_hit"]
    assert stale["cache_key"] != fresh["cache_key"]
    assert calls == [old_epoch, current_epoch]
    np.testing.assert_array_equal(fresh_audio, cached_audio)
