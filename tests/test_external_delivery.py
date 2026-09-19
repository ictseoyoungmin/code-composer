from hashlib import sha256
import json
from pathlib import Path
import struct

import numpy as np

from code_composer.app.delivery_cli import main as delivery_main
from code_composer.export.delivery import (
    DEFAULT_STEM_FORMAT,
    DELIVERY_FORMAT,
    DeliveryExportError,
    export_external_delivery,
    export_per_track_midi,
    export_track_stems,
)
from code_composer.pipeline.service import render_to_files


ROOT = Path(__file__).resolve().parents[1]


def _load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _float_wav(path: Path):
    data = path.read_bytes()
    assert data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    pos = 12
    fmt = None
    raw = None
    frames = None
    while pos + 8 <= len(data):
        kind = data[pos:pos+4]
        size = struct.unpack_from("<I", data, pos+4)[0]
        payload = data[pos+8:pos+8+size]
        if kind == b"fmt ":
            fmt = struct.unpack("<HHIIHH", payload)
        elif kind == b"fact":
            frames = struct.unpack("<I", payload)[0]
        elif kind == b"data":
            raw = payload
        pos += 8 + size + (size & 1)
    assert fmt is not None and raw is not None
    tag, channels, sr, _, block_align, bits = fmt
    audio = np.frombuffer(raw, dtype="<f4").reshape(-1, channels)
    assert frames == len(audio)
    return {"tag": tag, "channels": channels, "sr": sr, "bits": bits, "block_align": block_align, "audio": audio}


def test_track_stems_are_aligned_float32_and_one_per_track(tmp_path):
    ir = _load("examples/v1.16/final_closure/B_rhythm_centered/resolved_after.json")
    result = export_track_stems(ir, tmp_path / "stems")
    assert result["sample_format"] == DEFAULT_STEM_FORMAT == "float32"
    assert len(result["tracks"]) == len(ir["tracks"])
    frames = {item["frames"] for item in result["tracks"]}
    assert frames == {result["timeline_frames"]}
    for item in result["tracks"]:
        parsed = _float_wav(tmp_path / "stems" / item["file"])
        assert parsed["tag"] == 3
        assert parsed["channels"] == 2
        assert parsed["bits"] == 32
        assert parsed["sr"] == ir["meta"]["sample_rate"]
        assert len(parsed["audio"]) == result["timeline_frames"]
        assert item["sha256"] == sha256((tmp_path / "stems" / item["file"]).read_bytes()).hexdigest()


def test_graph_mode_stems_include_track_route_gain_but_exclude_shared_bus_claim(tmp_path):
    ir = _load("examples/v1.16/final_closure/A_lyrical_piano/resolved_after.json")
    result = export_track_stems(ir, tmp_path / "stems")
    assert {item["processing_policy"] for item in result["tracks"]} == {"post_track_route_pre_bus_pre_master"}
    # Track route gains are materially below unity in this fixture. Exported
    # stems should remain finite even when shared bus/master processing is absent.
    for item in result["tracks"]:
        assert np.isfinite(item["peak_float"])
        assert np.isfinite(item["rms_float"])
        assert item["peak_float"] > 0


def test_per_track_midi_is_type1_conductor_plus_one_track(tmp_path):
    ir = _load("examples/v1.16/final_closure/B_rhythm_centered/resolved_after.json")
    result = export_per_track_midi(ir, tmp_path / "midi")
    assert len(result["tracks"]) == len(ir["tracks"])
    for item in result["tracks"]:
        payload = (tmp_path / "midi" / item["file"]).read_bytes()
        assert payload[:4] == b"MThd"
        fmt, ntrks, ppq = struct.unpack(">HHH", payload[8:14])
        assert fmt == 1
        assert ntrks == 2
        assert ppq == 960
        source = next(t for t in ir["tracks"] if t["id"] == item["track_id"])
        assert item["note_events"] == len(source.get("events", []))


def test_per_track_drum_midi_keeps_channel_10(tmp_path):
    ir = _load("examples/v1.16/final_closure/B_rhythm_centered/resolved_after.json")
    result = export_per_track_midi(ir, tmp_path / "midi")
    drums = next(item for item in result["tracks"] if item["track_id"] == "drums")
    assert drums["percussion_channel"] is True
    assert drums["midi_channel"] == 10


def test_external_delivery_surface_and_manifest_hashes(tmp_path):
    ir = _load("examples/basic/demo_ir.json")
    render = render_to_files(ir, tmp_path / "source.wav", tmp_path / "source_resolved.json", None)
    out = tmp_path / "delivery"
    result = export_external_delivery(render["resolved"], out, reference_wav=tmp_path / "source.wav", stem="demo")
    manifest = result["manifest"]
    assert manifest["format"] == DELIVERY_FORMAT
    assert manifest["authority"]["sound_mix"] == "reference_mix.wav"
    assert manifest["files"]["full_midi"] == "demo.mid"
    assert (out / "demo.mid").is_file()
    assert (out / "reference_mix.wav").is_file()
    assert (out / "resolved_ir.json").is_file()
    assert (out / "DELIVERY_NOTES.txt").is_file()
    assert (out / "manifest.json").is_file()
    assert len(list((out / "midi").glob("*.mid"))) == len(render["resolved"]["tracks"])
    assert len(list((out / "stems").glob("*.wav"))) == len(render["resolved"]["tracks"])
    assert manifest["hashes"]["reference_mix_sha256"] == sha256((out / "reference_mix.wav").read_bytes()).hexdigest()
    assert manifest["hashes"]["full_midi_sha256"] == sha256((out / "demo.mid").read_bytes()).hexdigest()
    assert Path(result["manifest_path"]) == out / "manifest.json"


def test_delivery_does_not_invent_unsupported_controller_or_tempo_map_data(tmp_path):
    ir = _load("examples/basic/demo_ir.json")
    render = render_to_files(ir, tmp_path / "source.wav", None, None)
    manifest = export_external_delivery(render["resolved"], tmp_path / "delivery", reference_wav=tmp_path / "source.wav")["manifest"]
    policy = manifest["interchange_policy"]
    assert "single_global_bpm" in policy["tempo_map"]
    assert "no_canonical_cc_lane" in policy["continuous_cc"]
    assert "no_canonical_pitch_bend_lane" in policy["pitch_bend"]
    assert manifest["midi"]["time_signature_source"] == "beats_per_bar_plus_quarter_note_engine_beat"


def test_delivery_notes_explain_reference_and_stem_non_additivity(tmp_path):
    ir = _load("examples/basic/demo_ir.json")
    render = render_to_files(ir, tmp_path / "source.wav", None, None)
    export_external_delivery(render["resolved"], tmp_path / "delivery", reference_wav=tmp_path / "source.wav")
    notes = (tmp_path / "delivery" / "DELIVERY_NOTES.txt").read_text(encoding="utf-8")
    assert "authoritative sound/mix reference" in notes
    assert "not claimed to sum exactly" in notes
    assert "32-bit float" in notes


def test_delivery_is_byte_deterministic_for_same_resolved_state(tmp_path):
    ir = _load("examples/basic/demo_ir.json")
    render = render_to_files(ir, tmp_path / "source.wav", None, None)
    a = tmp_path / "a"
    b = tmp_path / "b"
    export_external_delivery(render["resolved"], a, reference_wav=tmp_path / "source.wav", stem="same")
    export_external_delivery(render["resolved"], b, reference_wav=tmp_path / "source.wav", stem="same")
    rels = [
        "same.mid", "resolved_ir.json", "DELIVERY_NOTES.txt", "manifest.json",
        *[str(p.relative_to(a)) for p in sorted((a / "midi").glob("*.mid"))],
        *[str(p.relative_to(a)) for p in sorted((a / "stems").glob("*.wav"))],
    ]
    for rel in rels:
        assert (a / rel).read_bytes() == (b / rel).read_bytes(), rel


def test_delivery_cli_renders_and_exports_complete_package(tmp_path, capsys):
    source = ROOT / "examples/basic/demo_ir.json"
    out = tmp_path / "delivery"
    assert delivery_main([str(source), str(out), "--stem", "handoff", "--ppq", "480"]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["full_midi"] == "handoff.mid"
    assert printed["ppq"] == 480
    assert printed["per_track_midi"] == printed["stems"]
    assert printed["stem_sample_format"] == "float32"
    assert (out / "reference_mix.wav").exists()
    assert (out / "handoff.mid").exists()


def test_external_delivery_rejects_missing_reference_wav(tmp_path):
    import pytest
    ir = _load("examples/basic/demo_ir.json")
    with pytest.raises(DeliveryExportError, match="does not exist"):
        export_external_delivery(ir, tmp_path / "delivery", reference_wav=tmp_path / "missing.wav")
