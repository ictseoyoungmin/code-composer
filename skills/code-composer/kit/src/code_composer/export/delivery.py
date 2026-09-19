from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import struct
from typing import Any

import numpy as np

from ..audio.dsp import apply_pan
from ..mix.automation import compile_automation
from ..render import _render_dry_track, _timeline_size
from .midi import DEFAULT_PPQ, export_midi


DELIVERY_FORMAT = "code-composer-external-delivery/v1"
DEFAULT_STEM_FORMAT = "float32"


class DeliveryExportError(ValueError):
    pass


def _safe_name(value: str, fallback: str) -> str:
    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = value.strip("_")
    return value or fallback


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_float32_wav(path: Path, audio: np.ndarray, sr: int) -> None:
    """Write deterministic stereo IEEE-float WAV.

    32-bit float is deliberate for delivery stems: it preserves headroom and
    avoids silently clipping isolated sources that may exceed full-scale before
    the shared Code Composer bus/master chain is applied.
    """
    x = np.asarray(audio, dtype="<f4")
    if x.ndim != 2 or x.shape[1] != 2:
        raise DeliveryExportError("delivery stems must be stereo arrays")
    if sr <= 0:
        raise DeliveryExportError("sample rate must be positive")
    if not np.all(np.isfinite(x)):
        raise DeliveryExportError("delivery stem contains non-finite samples")

    channels = 2
    bits = 32
    block_align = channels * (bits // 8)
    byte_rate = sr * block_align
    data = x.tobytes(order="C")
    # IEEE float (format tag 3) plus FACT chunk for broad DAW compatibility.
    fmt = struct.pack("<HHIIHH", 3, channels, sr, byte_rate, block_align, bits)
    fact = struct.pack("<I", len(x))
    chunks = (
        b"fmt " + struct.pack("<I", len(fmt)) + fmt,
        b"fact" + struct.pack("<I", len(fact)) + fact,
        b"data" + struct.pack("<I", len(data)) + data,
    )
    body = b"WAVE" + b"".join(chunks)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)


def _automation_lane(automation: dict[str, dict[str, Any]], target: str):
    for lane in automation.values():
        if lane.get("target") == target:
            return lane.get("values")
    return None


def _track_delivery_buffer(
    resolved_ir: dict[str, Any],
    track: dict[str, Any],
    *,
    n: int,
    sr: int,
    beat_s: float,
    automation: dict[str, dict[str, Any]],
) -> tuple[np.ndarray, str]:
    graph = resolved_ir.get("mix", {}).get("graph")
    graph_mode = bool(graph)
    buf = _render_dry_track(resolved_ir, track, n, sr, beat_s, graph_mode=graph_mode)

    if not graph_mode:
        # _render_dry_track already includes legacy track gain/pan and legacy
        # track insert effects. Only the shared master limiter is omitted.
        return buf, "post_legacy_track_fx_pre_master"

    tid = str(track["id"])
    route = graph["tracks"][tid]
    sig = buf * float(route.get("gain", 1.0))
    auto = _automation_lane(automation, f"track.{tid}.gain")
    if auto is not None:
        sig = sig * np.asarray(auto, dtype=np.float64)[:, None]
    sig = apply_pan(sig, route.get("pan", 0.0))
    # Shared sends, bus processing, sidechains and master FX are intentionally
    # not printed into track stems. Those interactions are non-additive and
    # remain represented by reference_mix.wav + resolved_ir.json.
    return sig, "post_track_route_pre_bus_pre_master"


def export_track_stems(
    resolved_ir: dict[str, Any],
    out_dir: str | Path,
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sr = int(resolved_ir.get("meta", {}).get("sample_rate", 44100))
    bpm = float(resolved_ir["transport"]["bpm"])
    if bpm <= 0:
        raise DeliveryExportError("transport.bpm must be > 0")
    beat_s = 60.0 / bpm
    n = _timeline_size(resolved_ir, sr, beat_s)
    graph = resolved_ir.get("mix", {}).get("graph")
    automation = compile_automation(resolved_ir, n, sr) if graph else {}

    tracks: list[dict[str, Any]] = []
    used_names: set[str] = set()
    for index, track in enumerate(resolved_ir.get("tracks", []), start=1):
        tid = str(track.get("id", f"track_{index}"))
        base = _safe_name(tid, f"track_{index}")
        name = f"{index:02d}_{base}"
        if name in used_names:
            name = f"{name}_{index}"
        used_names.add(name)
        path = out_dir / f"{name}.wav"
        sig, policy = _track_delivery_buffer(
            resolved_ir, track, n=n, sr=sr, beat_s=beat_s, automation=automation
        )
        _write_float32_wav(path, sig, sr)
        peak = float(np.max(np.abs(sig))) if len(sig) else 0.0
        rms = float(np.sqrt(np.mean(sig ** 2))) if len(sig) else 0.0
        tracks.append({
            "track_id": tid,
            "file": path.name,
            "sample_rate": sr,
            "channels": 2,
            "sample_format": DEFAULT_STEM_FORMAT,
            "frames": int(n),
            "duration_seconds": float(n / sr),
            "peak_float": peak,
            "rms_float": rms,
            "sha256": _sha256(path),
            "processing_policy": policy,
        })

    return {
        "directory": str(out_dir),
        "sample_rate": sr,
        "sample_format": DEFAULT_STEM_FORMAT,
        "timeline_frames": int(n),
        "timeline_seconds": float(n / sr),
        "tracks": tracks,
    }


def _single_track_ir(resolved_ir: dict[str, Any], track: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(resolved_ir)
    out["tracks"] = [deepcopy(track)]
    # MIDI export does not execute the mix graph. Remove it so this filtered IR
    # remains a truthful one-track delivery view rather than a partial graph.
    if isinstance(out.get("mix"), dict):
        out["mix"].pop("graph", None)
    return out


def export_per_track_midi(
    resolved_ir: dict[str, Any],
    out_dir: str | Path,
    *,
    ppq: int = DEFAULT_PPQ,
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tracks: list[dict[str, Any]] = []
    for index, track in enumerate(resolved_ir.get("tracks", []), start=1):
        tid = str(track.get("id", f"track_{index}"))
        name = f"{index:02d}_{_safe_name(tid, f'track_{index}')}.mid"
        path = out_dir / name
        result = export_midi(_single_track_ir(resolved_ir, track), path, ppq=ppq, resolve=False)
        info = result["manifest"]["tracks"][0]
        tracks.append({
            "track_id": tid,
            "file": name,
            "sha256": result["manifest"]["midi_sha256"],
            "bytes": result["manifest"]["midi_bytes"],
            "midi_channel": info["channel"],
            "percussion_channel": info["percussion_channel"],
            "note_events": info["note_events"],
        })
    return {"directory": str(out_dir), "ppq": ppq, "tracks": tracks}


def _delivery_notes(manifest: dict[str, Any]) -> str:
    lines = [
        "Code Composer External Delivery",
        "===============================",
        "",
        f"Title: {manifest['title']}",
        f"Tempo: {manifest['transport'].get('bpm')} BPM",
        f"Time signature: {manifest['midi']['time_signature'][0]}/{manifest['midi']['time_signature'][1]}",
        "",
        "Import guidance",
        "---------------",
        "1. Use reference_mix.wav as the authoritative sound/mix reference.",
        "2. Import the full-song MIDI for arrangement/structure or midi/*.mid for isolated tracks.",
        "3. stems/*.wav are time-aligned 32-bit float stereo sources from bar/beat zero.",
        "4. Graph-mode stems include track route gain/pan/track-gain automation, but not shared sends, buses, sidechains or master FX.",
        "5. Recreate shared mix interactions using resolved_ir.json and the reference mix; stems are intentionally not claimed to sum exactly to the mastered reference.",
        "6. MIDI program changes are omitted because Code Composer timbre cannot be represented faithfully by General MIDI patches.",
        "",
        "Canonical limitations",
        "---------------------",
        "- Current canonical IR has one global BPM rather than a tempo map.",
        "- Current transport stores beats_per_bar but no denominator; MIDI states n/4 because the engine beat is a quarter note.",
        "- No canonical continuous MIDI CC/pitch-bend lane exists in this release, so delivery does not invent controller data.",
        "",
    ]
    return "\n".join(lines)


def export_external_delivery(
    resolved_ir: dict[str, Any],
    out_dir: str | Path,
    *,
    reference_wav: str | Path,
    ppq: int = DEFAULT_PPQ,
    stem: str | None = None,
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    title = str(resolved_ir.get("meta", {}).get("title", "Code Composer Song"))
    stem = stem or _safe_name(title, "code_composer_song")

    reference_src = Path(reference_wav)
    if not reference_src.is_file():
        raise DeliveryExportError(f"reference WAV does not exist: {reference_src}")
    reference_dst = out_dir / "reference_mix.wav"
    if reference_src.resolve() != reference_dst.resolve():
        shutil.copyfile(reference_src, reference_dst)

    resolved_path = out_dir / "resolved_ir.json"
    resolved_path.write_text(
        json.dumps(resolved_ir, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    full_midi_path = out_dir / f"{stem}.mid"
    full_midi = export_midi(resolved_ir, full_midi_path, ppq=ppq, resolve=False)
    per_track_midi = export_per_track_midi(resolved_ir, out_dir / "midi", ppq=ppq)
    stems = export_track_stems(resolved_ir, out_dir / "stems")

    stem_by_track = {item["track_id"]: item for item in stems["tracks"]}
    midi_by_track = {item["track_id"]: item for item in per_track_midi["tracks"]}
    track_delivery = []
    for track in resolved_ir.get("tracks", []):
        tid = str(track.get("id"))
        patch_id = str(track.get("instrument", "unknown"))
        patch = resolved_ir.get("instruments", {}).get(patch_id, {})
        track_delivery.append({
            "track_id": tid,
            "arrangement_role": track.get("arrangement_role", tid),
            "instrument_id": patch_id,
            "instrument_kind": patch.get("kind", "synth"),
            "midi": midi_by_track[tid],
            "stem": stem_by_track[tid],
        })

    midi_manifest = deepcopy(full_midi["manifest"])
    midi_manifest["midi_path"] = full_midi_path.name

    manifest = {
        "format": DELIVERY_FORMAT,
        "title": title,
        "authority": {
            "sound_mix": "reference_mix.wav",
            "editable_symbolic_state": "resolved_ir.json",
            "midi": "interchange_representation",
            "stems": "aligned_track_delivery_sources",
        },
        "source_meta": deepcopy(resolved_ir.get("meta", {})),
        "transport": deepcopy(resolved_ir.get("transport", {})),
        "tonal": deepcopy(resolved_ir.get("tonal", {})),
        "midi": midi_manifest,
        "stems": {
            "sample_rate": stems["sample_rate"],
            "sample_format": stems["sample_format"],
            "timeline_frames": stems["timeline_frames"],
            "timeline_seconds": stems["timeline_seconds"],
            "shared_processing_policy": "shared bus/send/sidechain/master processing is reference-only and is not baked independently into track stems",
        },
        "tracks": track_delivery,
        "files": {
            "reference_mix": "reference_mix.wav",
            "resolved_ir": "resolved_ir.json",
            "full_midi": full_midi_path.name,
            "per_track_midi_dir": "midi",
            "stems_dir": "stems",
            "delivery_notes": "DELIVERY_NOTES.txt",
        },
        "hashes": {
            "reference_mix_sha256": _sha256(reference_dst),
            "resolved_ir_sha256": _sha256(resolved_path),
            "full_midi_sha256": _sha256(full_midi_path),
        },
        "interchange_policy": {
            "midi_program_changes": "omitted_to_avoid_misrepresenting_code_composer_timbre",
            "tempo_map": "not_exported_current_canonical_ir_has_single_global_bpm",
            "time_signature": "beats_per_bar_exported_as_n_over_4_engine_beat_is_quarter_note",
            "continuous_cc": "not_exported_no_canonical_cc_lane_in_v1.17_m3",
            "pitch_bend": "not_exported_no_canonical_pitch_bend_lane_in_v1.17_m3",
        },
    }

    notes_path = out_dir / "DELIVERY_NOTES.txt"
    notes_path.write_text(_delivery_notes(manifest), encoding="utf-8")
    manifest["hashes"]["delivery_notes_sha256"] = _sha256(notes_path)

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "manifest": manifest,
        "manifest_path": str(manifest_path),
        "full_midi_path": str(full_midi_path),
        "reference_mix_path": str(reference_dst),
        "resolved_ir_path": str(resolved_path),
    }
