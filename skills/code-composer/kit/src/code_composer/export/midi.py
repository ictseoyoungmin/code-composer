from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil
import struct
import unicodedata
from typing import Any

from ..composition.arrange import arrange_ir
from ..composition.performance import realize_performance_ir, validate_ir_performance_contract
from ..composition.resolve import resolve_ir
from ..core.constraints import enforce_forbidden_track_events
from ..core.ir import validate_ir
from ..mix.mixer import validate_mix_graph
from ..validation_contracts import validate_runtime_extensions

DEFAULT_PPQ = 960
DRUM_NOTES = {
    "kick": 36, "snare": 38, "hat": 42,
    "snare_center": 38, "snare_ghost": 38, "snare_rimshot": 38, "snare_cross_stick": 37,
    "hat_tight_closed": 42, "hat_closed": 42,
    "hat_half_open": 46, "hat_open": 46,
    "hat_pedal": 44, "hat_foot_splash": 44,
    "tom_floor": 43, "tom_floor_edge": 43,
    "tom_mid": 47, "tom_mid_edge": 47,
    "tom_high": 50, "tom_high_edge": 50,
    "crash": 49, "ride": 51,
}
_MELODIC_CHANNELS = tuple(list(range(0, 9)) + list(range(10, 16)))


class MidiExportError(ValueError):
    pass


def _vlq(value: int) -> bytes:
    if value < 0:
        raise MidiExportError("MIDI delta time cannot be negative")
    buffer = value & 0x7F
    out = bytearray([buffer])
    value >>= 7
    while value:
        buffer = (value & 0x7F) | 0x80
        out.insert(0, buffer)
        value >>= 7
    return bytes(out)


def _meta(meta_type: int, payload: bytes) -> bytes:
    return bytes((0xFF, meta_type)) + _vlq(len(payload)) + payload


def _midi_text(text: str) -> bytes:
    # Standard MIDI meta-text has no universal Unicode encoding agreement.
    # Use an ASCII-safe representation for cross-DAW readability; the bundle
    # manifest retains the original Unicode metadata losslessly.
    translated = str(text).translate({
        0x2013: ord("-"),  # en dash
        0x2014: ord("-"),  # em dash
        0x2018: ord("'"),
        0x2019: ord("'"),
        0x201C: ord('"'),
        0x201D: ord('"'),
    })
    return unicodedata.normalize("NFKD", translated).encode("ascii", "replace")


def _text_meta(meta_type: int, text: str) -> bytes:
    return _meta(meta_type, _midi_text(text))


def _tick(beat: float, ppq: int) -> int:
    # Round-half-up, independent of Python's banker rounding.
    return max(0, int(math.floor(float(beat) * ppq + 0.5)))


def _velocity(value: Any) -> int:
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise MidiExportError(f"invalid velocity {value!r}") from exc
    return max(1, min(127, int(math.floor(v * 127.0 + 0.5))))


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return kind + struct.pack(">I", len(payload)) + payload


def _track_bytes(events: list[tuple[int, int, bytes]]) -> bytes:
    # priority: note-off (0) before meta/control (1) before note-on (2)
    events = sorted(events, key=lambda item: (item[0], item[1], item[2]))
    body = bytearray()
    previous = 0
    for tick, _priority, payload in events:
        if tick < previous:
            raise MidiExportError("MIDI events are not monotonic")
        body.extend(_vlq(tick - previous))
        body.extend(payload)
        previous = tick
    body.extend(_vlq(0))
    body.extend(_meta(0x2F, b""))
    return _chunk(b"MTrk", bytes(body))


def resolve_for_midi(ir: dict[str, Any]) -> dict[str, Any]:
    """Resolve canonical Music IR without rendering audio.

    This mirrors the symbolic portion of ``render.render`` but remains a one-way
    export adapter: it never mutates analyzers or composition intent.
    """
    validate_ir(ir)
    validate_runtime_extensions(ir)
    validate_ir_performance_contract(ir)
    graph = ir.get("mix", {}).get("graph")
    if graph is not None:
        validate_mix_graph(graph, {t.get("id") for t in ir["tracks"]})

    out = deepcopy(ir)
    if out.get("arrangement") and not out.get("arrangement_resolved"):
        out = arrange_ir(out)
    out = resolve_ir(out)
    if out.get("performance_ir") and not out.get("performance_resolved"):
        out = realize_performance_ir(out)
    out["tracks"] = enforce_forbidden_track_events(out.get("tracks", []), out)
    return out


def _conductor_events(ir: dict[str, Any], ppq: int) -> list[tuple[int, int, bytes]]:
    transport = ir["transport"]
    bpm = float(transport["bpm"])
    if bpm <= 0:
        raise MidiExportError("transport.bpm must be > 0")
    micros = max(1, min(0xFFFFFF, int(math.floor(60_000_000.0 / bpm + 0.5))))
    beats_per_bar = int(transport["beats_per_bar"])
    if beats_per_bar <= 0 or beats_per_bar > 255:
        raise MidiExportError("transport.beats_per_bar must fit MIDI time-signature numerator")

    title = str(ir.get("meta", {}).get("title", "Code Composer Export"))
    tonal = ir.get("tonal", {})
    events = [
        (0, 1, _text_meta(0x03, "Code Composer Conductor")),
        (0, 1, _text_meta(0x01, f"Title: {title}")),
        (0, 1, _meta(0x51, micros.to_bytes(3, "big"))),
        # Current IR defines beats-per-bar but no denominator. The engine beat is
        # a quarter note, so MIDI export states n/4 explicitly.
        (0, 1, _meta(0x58, bytes((beats_per_bar, 2, 24, 8)))),
        (0, 1, _text_meta(0x01, f"Key: {tonal.get('root', '?')} {tonal.get('scale', '?')}")),
        (0, 1, _text_meta(0x01, f"Code Composer PPQ={ppq}; time signature inferred as {beats_per_bar}/4")),
    ]
    for section in ir.get("form", []):
        if not isinstance(section, dict) or "start_bar" not in section:
            continue
        sid = str(section.get("id", "section"))
        tick = _tick(float(section["start_bar"]) * beats_per_bar, ppq)
        events.append((tick, 1, _text_meta(0x06, sid)))
    return events


def _track_channel(track_index: int, percussion: bool) -> int:
    if percussion:
        return 9
    return _MELODIC_CHANNELS[track_index % len(_MELODIC_CHANNELS)]


def _midi_note_for_event(event: dict[str, Any]) -> int:
    if event.get("event_type") == "drum":
        drum = str(event.get("drum", ""))
        try:
            return DRUM_NOTES[drum]
        except KeyError as exc:
            raise MidiExportError(f"unsupported drum role for MIDI export: {drum!r}") from exc
    if "midi" not in event:
        raise MidiExportError("pitched event is missing midi note")
    note = int(event["midi"])
    if not 0 <= note <= 127:
        raise MidiExportError(f"MIDI note out of range: {note}")
    return note


def _instrument_summary(instrument_id: str, patch: dict[str, Any], role: str) -> str:
    family = None
    if isinstance(patch.get("piano_design"), dict):
        family = patch["piano_design"].get("family", "acoustic")
    kind = patch.get("kind", "synth")
    parts = [f"role={role}", f"instrument={instrument_id}", f"kind={kind}"]
    if family:
        parts.append(f"family={family}")
    return "; ".join(parts)


def _build_track(ir: dict[str, Any], track: dict[str, Any], channel: int, ppq: int) -> tuple[bytes, dict[str, Any]]:
    tid = str(track.get("id", "track"))
    instrument_id = str(track.get("instrument", "unknown"))
    patch = ir.get("instruments", {}).get(instrument_id, {})
    percussion = patch.get("kind") == "percussion" or any(
        ev.get("event_type") == "drum" for ev in track.get("events", [])
    )
    role = str(track.get("arrangement_role", tid))
    events: list[tuple[int, int, bytes]] = [
        (0, 1, _text_meta(0x03, tid)),
        (0, 1, _text_meta(0x04, _instrument_summary(instrument_id, patch, role))),
    ]
    section_ids: set[str] = set()
    note_count = 0
    for event in track.get("events", []):
        if event.get("event_type") == "drum_control":
            continue
        start = _tick(float(event.get("start_beat", 0.0)), ppq)
        duration = max(1, _tick(float(event.get("duration_beats", 0.0)), ppq))
        end = start + duration
        note = _midi_note_for_event(event)
        vel = _velocity(event.get("velocity", 0.8))
        if event.get("section_id") is not None:
            section_ids.add(str(event["section_id"]))
        events.append((end, 0, bytes((0x80 | channel, note, 0))))
        events.append((start, 2, bytes((0x90 | channel, note, vel))))
        note_count += 1

    manifest = {
        "track_id": tid,
        "instrument_id": instrument_id,
        "instrument_kind": patch.get("kind", "synth"),
        "channel": channel + 1,
        "percussion_channel": percussion,
        "note_events": note_count,
        "section_ids": sorted(section_ids),
        "program_change": None,
        "program_change_policy": "omitted_to_avoid_misrepresenting_code_composer_timbre",
    }
    if isinstance(patch.get("piano_design"), dict):
        manifest["piano_design"] = deepcopy(patch["piano_design"])
    return _track_bytes(events), manifest


def midi_bytes(ir: dict[str, Any], *, ppq: int = DEFAULT_PPQ, resolve: bool = True) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
    if not isinstance(ppq, int) or not 24 <= ppq <= 32767:
        raise MidiExportError("ppq must be an integer in [24, 32767]")
    resolved = resolve_for_midi(ir) if resolve else deepcopy(ir)
    # Even pre-resolved input must satisfy the core contract.
    validate_ir(resolved)

    conductor = _track_bytes(_conductor_events(resolved, ppq))
    track_chunks: list[bytes] = []
    track_manifest: list[dict[str, Any]] = []
    melodic_index = 0
    for track in resolved.get("tracks", []):
        patch = resolved.get("instruments", {}).get(track.get("instrument"), {})
        percussion = patch.get("kind") == "percussion" or any(
            ev.get("event_type") == "drum" for ev in track.get("events", [])
        )
        channel = _track_channel(melodic_index, percussion)
        if not percussion:
            melodic_index += 1
        chunk, info = _build_track(resolved, track, channel, ppq)
        track_chunks.append(chunk)
        track_manifest.append(info)

    ntrks = 1 + len(track_chunks)
    header = _chunk(b"MThd", struct.pack(">HHH", 1, ntrks, ppq))
    payload = header + conductor + b"".join(track_chunks)
    manifest = {
        "format": 1,
        "ppq": ppq,
        "track_count": ntrks,
        "musical_track_count": len(track_chunks),
        "tempo_bpm": float(resolved["transport"]["bpm"]),
        "time_signature": [int(resolved["transport"]["beats_per_bar"]), 4],
        "time_signature_source": "beats_per_bar_plus_quarter_note_engine_beat",
        "tonal": deepcopy(resolved.get("tonal", {})),
        "tracks": track_manifest,
        "drum_map": deepcopy(DRUM_NOTES),
        "sound_policy": "MIDI carries notes/performance/structure; Code Composer DSP/timbre remains in the reference WAV/IR.",
    }
    return payload, manifest, resolved


def export_midi(ir: dict[str, Any], out_path: str | Path, *, ppq: int = DEFAULT_PPQ, resolve: bool = True) -> dict[str, Any]:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload, manifest, resolved = midi_bytes(ir, ppq=ppq, resolve=resolve)
    out.write_bytes(payload)
    result = deepcopy(manifest)
    result.update({
        "midi_path": str(out),
        "midi_bytes": len(payload),
        "midi_sha256": sha256(payload).hexdigest(),
    })
    return {"manifest": result, "resolved": resolved}


def _safe_stem(title: str) -> str:
    chars = []
    for ch in title.strip():
        if ch.isalnum():
            chars.append(ch.lower())
        elif chars and chars[-1] != "_":
            chars.append("_")
    stem = "".join(chars).strip("_")
    return stem or "code_composer_song"


def export_collaboration_bundle(
    resolved_ir: dict[str, Any],
    out_dir: str | Path,
    *,
    reference_wav: str | Path | None = None,
    ppq: int = DEFAULT_PPQ,
    stem: str | None = None,
) -> dict[str, Any]:
    """Write MIDI + resolved IR + collaboration manifest.

    ``resolved_ir`` is expected to be the exact resolved state used for the
    reference render. ``code-composer-collab`` supplies this by invoking the
    existing render pipeline once before calling this adapter.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    title = str(resolved_ir.get("meta", {}).get("title", "Code Composer Song"))
    stem = stem or _safe_stem(title)

    midi_path = out_dir / f"{stem}.mid"
    midi_result = export_midi(resolved_ir, midi_path, ppq=ppq, resolve=False)
    resolved_path = out_dir / "resolved_ir.json"
    resolved_path.write_text(json.dumps(resolved_ir, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    files = {
        "midi": midi_path.name,
        "resolved_ir": resolved_path.name,
    }
    hashes = {
        "midi_sha256": midi_result["manifest"]["midi_sha256"],
        "resolved_ir_sha256": sha256(resolved_path.read_bytes()).hexdigest(),
    }
    if reference_wav is not None:
        src = Path(reference_wav)
        if not src.is_file():
            raise MidiExportError(f"reference WAV does not exist: {src}")
        dst = out_dir / "reference_mix.wav"
        if src.resolve() != dst.resolve():
            shutil.copyfile(src, dst)
        files["reference_mix"] = dst.name
        hashes["reference_mix_sha256"] = sha256(dst.read_bytes()).hexdigest()

    manifest = {
        "format": "code-composer-collaboration-bundle/v1",
        "title": title,
        "source_meta": deepcopy(resolved_ir.get("meta", {})),
        "transport": deepcopy(resolved_ir.get("transport", {})),
        "tonal": deepcopy(resolved_ir.get("tonal", {})),
        "midi": midi_result["manifest"],
        "files": files,
        "hashes": hashes,
        "collaboration_notes": [
            "Import the Type 1 MIDI into a DAW to preserve track separation, note timing, duration, and velocity.",
            "Section IDs are exported as MIDI marker meta-events on the conductor track.",
            "Code Composer synth/piano/percussion DSP and mix processing are not encoded as MIDI program changes.",
            "Use reference_mix.wav as the authoritative timbre/mix reference when present.",
        ],
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"manifest": manifest, "manifest_path": str(manifest_path), "midi_path": str(midi_path)}
