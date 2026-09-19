from hashlib import sha256
import json
from pathlib import Path
import struct

from code_composer.export.midi import (
    DEFAULT_PPQ,
    DRUM_NOTES,
    export_collaboration_bundle,
    export_midi,
    midi_bytes,
    resolve_for_midi,
)

ROOT = Path(__file__).resolve().parents[1]


def _vlq(data: bytes, pos: int):
    value = 0
    while True:
        b = data[pos]
        pos += 1
        value = (value << 7) | (b & 0x7F)
        if not b & 0x80:
            return value, pos


def _parse_smf(data: bytes):
    assert data[:4] == b"MThd"
    hlen = struct.unpack(">I", data[4:8])[0]
    fmt, ntrks, ppq = struct.unpack(">HHH", data[8:14])
    pos = 8 + hlen
    tracks = []
    for _ in range(ntrks):
        assert data[pos:pos+4] == b"MTrk"
        length = struct.unpack(">I", data[pos+4:pos+8])[0]
        payload = data[pos+8:pos+8+length]
        pos += 8 + length
        tick = 0
        i = 0
        events = []
        while i < len(payload):
            delta, i = _vlq(payload, i)
            tick += delta
            status = payload[i]
            i += 1
            if status == 0xFF:
                meta_type = payload[i]
                i += 1
                size, i = _vlq(payload, i)
                value = payload[i:i+size]
                i += size
                events.append((tick, "meta", meta_type, value))
                if meta_type == 0x2F:
                    break
            elif status & 0xF0 in (0x80, 0x90):
                note, velocity = payload[i], payload[i+1]
                i += 2
                events.append((tick, "midi", status, note, velocity))
            elif status & 0xF0 in (0xC0, 0xD0):
                value = payload[i]
                i += 1
                events.append((tick, "midi1", status, value))
            else:
                a, b = payload[i], payload[i+1]
                i += 2
                events.append((tick, "midi", status, a, b))
        tracks.append(events)
    assert pos == len(data)
    return {"format": fmt, "ntrks": ntrks, "ppq": ppq, "tracks": tracks}


def _load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _meta_texts(track, meta_type):
    return [ev[3].decode("utf-8") for ev in track if ev[1] == "meta" and ev[2] == meta_type]


def test_type1_header_conductor_and_track_count():
    ir = _load("examples/basic/demo_ir.json")
    payload, manifest, _ = midi_bytes(ir)
    parsed = _parse_smf(payload)
    assert parsed["format"] == 1
    assert parsed["ppq"] == DEFAULT_PPQ == 960
    assert parsed["ntrks"] == 1 + len(ir["tracks"])
    assert manifest["track_count"] == parsed["ntrks"]


def test_conductor_carries_tempo_time_signature_and_sections():
    ir = _load("examples/v1.16/final_closure/B_rhythm_centered/resolved_after.json")
    payload, manifest, _ = midi_bytes(ir, resolve=False)
    conductor = _parse_smf(payload)["tracks"][0]
    tempo = [ev for ev in conductor if ev[1] == "meta" and ev[2] == 0x51]
    sig = [ev for ev in conductor if ev[1] == "meta" and ev[2] == 0x58]
    markers = [(ev[0], ev[3].decode("utf-8")) for ev in conductor if ev[1] == "meta" and ev[2] == 0x06]
    assert int.from_bytes(tempo[0][3], "big") == round(60_000_000 / 112)
    assert sig[0][3][:2] == bytes((4, 2))
    assert markers == [(0, "pulse"), (8 * 960, "drive"), (16 * 960, "break"), (24 * 960, "final")]
    assert manifest["time_signature"] == [4, 4]


def test_realized_humanization_is_preserved_as_note_ticks_and_velocity():
    ir = _load("examples/v1.16/final_closure/A_lyrical_piano/resolved_after.json")
    payload, _, _ = midi_bytes(ir, resolve=False)
    lead = _parse_smf(payload)["tracks"][1]
    note_ons = [ev for ev in lead if ev[1] == "midi" and ev[2] & 0xF0 == 0x90]
    second = ir["tracks"][0]["events"][1]
    expected_tick = int(second["start_beat"] * 960 + 0.5)
    expected_velocity = int(second["velocity"] * 127 + 0.5)
    match = [ev for ev in note_ons if ev[0] == expected_tick and ev[3] == second["midi"]]
    assert match
    assert match[0][4] == expected_velocity


def test_note_off_precedes_retrigger_at_same_tick():
    ir = _load("examples/basic/demo_ir.json")
    # Create a deliberately adjacent repeated note in an existing valid track.
    track = ir["tracks"][0]
    track["events"] = [
        {"start_beat": 0.0, "duration_beats": 1.0, "midi": 60, "velocity": 0.5},
        {"start_beat": 1.0, "duration_beats": 1.0, "midi": 60, "velocity": 0.5},
    ]
    payload, _, _ = midi_bytes(ir, resolve=False)
    events = _parse_smf(payload)["tracks"][1]
    at_tick = [ev for ev in events if ev[0] == 960 and ev[1] == "midi" and ev[3] == 60]
    assert [ev[2] & 0xF0 for ev in at_tick] == [0x80, 0x90]


def test_percussion_uses_gm_channel_10_and_drum_notes():
    ir = _load("examples/v1.16/final_closure/B_rhythm_centered/resolved_after.json")
    payload, manifest, _ = midi_bytes(ir, resolve=False)
    parsed = _parse_smf(payload)
    drum_index = next(i for i, info in enumerate(manifest["tracks"]) if info["track_id"] == "drums")
    drum_track = parsed["tracks"][1 + drum_index]
    note_ons = [ev for ev in drum_track if ev[1] == "midi" and ev[2] & 0xF0 == 0x90]
    assert note_ons
    assert {ev[2] & 0x0F for ev in note_ons} == {9}
    assert {ev[3] for ev in note_ons} <= set(DRUM_NOTES.values())
    # Historical three-piece mappings remain stable while later slices may add
    # explicit acoustic-kit voices.
    assert {k: DRUM_NOTES[k] for k in ("kick", "snare", "hat")} == {"kick": 36, "snare": 38, "hat": 42}
    assert {"ride": 51, "crash": 49, "tom_high": 50, "tom_mid": 47, "tom_floor": 43}.items() <= DRUM_NOTES.items()


def test_track_names_and_no_misleading_program_changes():
    ir = _load("examples/v1.16/final_closure/B_rhythm_centered/resolved_after.json")
    payload, manifest, _ = midi_bytes(ir, resolve=False)
    parsed = _parse_smf(payload)
    names = [_meta_texts(track, 0x03)[0] for track in parsed["tracks"][1:]]
    assert names == [track["id"] for track in ir["tracks"]]
    statuses = [ev[2] for track in parsed["tracks"] for ev in track if ev[1].startswith("midi")]
    assert not any(status & 0xF0 == 0xC0 for status in statuses)
    assert all(info["program_change"] is None for info in manifest["tracks"])



def test_midi_meta_text_is_ascii_safe_for_cross_daw_interchange():
    ir = _load("examples/v1.16/final_closure/B_rhythm_centered/resolved_after.json")
    payload, _, _ = midi_bytes(ir, resolve=False)
    parsed = _parse_smf(payload)
    for track in parsed["tracks"]:
        for ev in track:
            if ev[1] == "meta" and ev[2] in (0x01, 0x03, 0x04, 0x06):
                ev[3].decode("ascii")
    assert _meta_texts(parsed["tracks"][0], 0x03) == ["Code Composer Conductor"]

def test_midi_export_is_byte_deterministic(tmp_path):
    ir = _load("examples/v1.16/final_closure/C_sparse_chamber_electronic/resolved_after.json")
    one = tmp_path / "one.mid"
    two = tmp_path / "two.mid"
    a = export_midi(ir, one, resolve=False)["manifest"]
    b = export_midi(ir, two, resolve=False)["manifest"]
    assert one.read_bytes() == two.read_bytes()
    assert a["midi_sha256"] == b["midi_sha256"] == sha256(one.read_bytes()).hexdigest()


def test_resolve_for_midi_can_accept_unresolved_high_level_ir():
    ir = _load("examples/basic/high_level_ir.json")
    resolved = resolve_for_midi(ir)
    assert resolved["tracks"]
    assert all(track["source"]["type"] == "resolved" for track in resolved["tracks"])
    assert all("events" in track for track in resolved["tracks"])


def test_collaboration_bundle_contains_delivery_surface(tmp_path):
    ir = _load("examples/basic/demo_ir.json")
    wav = tmp_path / "source.wav"
    wav.write_bytes(b"RIFF-test-reference")
    out = tmp_path / "bundle"
    result = export_collaboration_bundle(ir, out, reference_wav=wav, stem="demo")
    assert {p.name for p in out.iterdir()} == {"demo.mid", "reference_mix.wav", "resolved_ir.json", "manifest.json"}
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["format"] == "code-composer-collaboration-bundle/v1"
    assert manifest["files"]["midi"] == "demo.mid"
    assert manifest["hashes"]["midi_sha256"] == sha256((out / "demo.mid").read_bytes()).hexdigest()
    assert manifest["hashes"]["reference_mix_sha256"] == sha256((out / "reference_mix.wav").read_bytes()).hexdigest()
    assert Path(result["manifest_path"]) == out / "manifest.json"


def test_midi_manifest_preserves_patch_identity_without_claiming_midi_timbre():
    ir = _load("examples/v1.16/final_closure/A_lyrical_piano/resolved_after.json")
    _, manifest, _ = midi_bytes(ir, resolve=False)
    lead = next(info for info in manifest["tracks"] if info["track_id"] == "lead")
    assert lead["instrument_id"] == "lead"
    assert lead["piano_design"]["family"] == "acoustic"
    assert lead["program_change_policy"] == "omitted_to_avoid_misrepresenting_code_composer_timbre"


def test_midi_cli_main_exports_file(tmp_path, capsys):
    from code_composer.app.midi_cli import main
    source = ROOT / "examples/basic/demo_ir.json"
    out = tmp_path / "cli.mid"
    assert main([str(source), str(out), "--ppq", "480"]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert out.exists()
    assert printed["ppq"] == 480
    assert printed["midi_sha256"] == sha256(out.read_bytes()).hexdigest()


def test_collab_cli_main_uses_exact_render_state(tmp_path, capsys):
    from code_composer.app.collab_cli import main
    source = ROOT / "examples/basic/demo_ir.json"
    out = tmp_path / "collab"
    assert main([str(source), str(out), "--stem", "handoff"]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["midi"] == "handoff.mid"
    assert (out / "handoff.mid").exists()
    assert (out / "reference_mix.wav").exists()
    assert (out / "resolved_ir.json").exists()
    assert (out / "manifest.json").exists()


def test_export_rejects_invalid_ppq_and_event_payloads(tmp_path):
    import pytest
    from code_composer.export.midi import MidiExportError, _velocity

    ir = _load("examples/basic/demo_ir.json")
    with pytest.raises(MidiExportError, match="ppq"):
        midi_bytes(ir, ppq=12, resolve=False)
    with pytest.raises(MidiExportError, match="invalid velocity"):
        _velocity("not-a-number")

    bad = _load("examples/basic/demo_ir.json")
    bad["tracks"][0]["events"] = [{"start_beat": 0, "duration_beats": 1, "velocity": .5}]
    with pytest.raises(MidiExportError, match="missing midi"):
        midi_bytes(bad, resolve=False)

    bad = _load("examples/basic/demo_ir.json")
    bad["tracks"][0]["events"] = [{"start_beat": 0, "duration_beats": 1, "velocity": .5, "midi": 200}]
    with pytest.raises(MidiExportError, match="out of range"):
        midi_bytes(bad, resolve=False)

    drums = _load("examples/v1.16/final_closure/B_rhythm_centered/resolved_after.json")
    drum_track = next(t for t in drums["tracks"] if t["id"] == "drums")
    drum_track["events"][0]["drum"] = "cowbell"
    with pytest.raises(MidiExportError, match="unsupported drum"):
        midi_bytes(drums, resolve=False)


def test_collaboration_bundle_default_stem_and_missing_reference_guard(tmp_path):
    import pytest
    from code_composer.export.midi import MidiExportError

    ir = _load("examples/basic/demo_ir.json")
    ir["meta"]["title"] = "  A / Strange — Title!  "
    out = tmp_path / "bundle"
    result = export_collaboration_bundle(ir, out)
    assert Path(result["midi_path"]).name == "a_strange_title.mid"
    assert "reference_mix" not in result["manifest"]["files"]

    with pytest.raises(MidiExportError, match="does not exist"):
        export_collaboration_bundle(ir, tmp_path / "bad", reference_wav=tmp_path / "missing.wav")


def test_resolve_for_midi_realizes_performance_when_present():
    ir = _load("examples/v1.16/final_closure/A_lyrical_piano/music_ir_after.json")
    assert ir.get("performance_ir")
    ir.pop("performance_resolved", None)
    resolved = resolve_for_midi(ir)
    assert resolved.get("performance_resolved") is True
    lead = next(t for t in resolved["tracks"] if t["id"] == "lead")
    assert any("performance" in event for event in lead["events"])
