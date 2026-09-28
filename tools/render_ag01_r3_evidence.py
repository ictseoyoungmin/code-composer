#!/usr/bin/env python3
"""Render AG01 R3 reopen evidence from the actual Code Composer branch."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import wave

import numpy as np

from code_composer.audio.acoustic_guitar import render_acoustic_guitar_note
from code_composer.presets import materialize_preset


SR = 24000
GATE = 0.45
VELOCITIES = (0.35, 0.65, 0.92)
PITCHES = (("E2", 40), ("E3", 52), ("E4", 64))
OUT = Path(os.environ.get("AG01_R3_EVIDENCE_DIR", "artifacts/ag01-r3"))


def _write(path: Path, audio: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def _rms(audio: np.ndarray) -> float:
    return float(np.sqrt(np.mean(audio * audio)) + 1e-12)


def _r2_patch() -> dict:
    patch = materialize_preset("acoustic_guitar.steel_single_string", version="1.0.0")
    g = patch["acoustic_guitar_graph"]
    g.update({
        "physical_model": "ag01_modal_bridge_body_v1",
        "string_source_model": "ag01_legacy_modal_v1",
        "max_partials": 30,
        "pluck_position": 0.16,
        "partial_rolloff": 0.86,
        "string_inharmonicity": 0.000045,
        "base_decay_s": 2.35,
        "frequency_damping": 0.11,
        "damping_power": 1.35,
        "decay_keytrack": 0.012,
        "fret_contact": 0.30,
        "string_release_ramp_s": 0.00045,
        "excitation_noise_gain": 0.040,
        "excitation_highpass_hz": 850,
        "excitation_lowpass_hz": 7200,
        "excitation_decay_s": 0.018,
        "release_click_gain": 0.018,
        "bridge_lowpass_hz": 9200,
        "body_modal_mix": 1.0,
        "body_mode_damping": 1.0,
        "direct_bridge_mix": 0.34,
        "air_mode_mix": 0.11,
        "radiation_lowpass_hz": 8800,
        "stereo_width": 0.065,
        "body_drive": 0.92,
        "radiation_keytrack": 1.10,
        "output_gain": 0.82,
        "seed": 11901,
    })
    return patch


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    r3 = materialize_preset("acoustic_guitar.steel_single_string", version="1.0.0")
    r2 = _r2_patch()

    manifest = [
        "AG01 R3 reopen evidence",
        f"git_sha: {os.environ.get('GITHUB_SHA', 'local')}",
        f"sample_rate: {SR}",
        f"gate_seconds: {GATE}",
        "",
        "Closure rule: E2, E3 and E4 must each be judged independently.",
        "A = rejected AG01 R2 signal reconstructed by the actual branch renderer.",
        "B = AG01 R3 reopen candidate.",
        "Matched files use per-pair RMS matching only for timbre comparison.",
        "",
    ]
    mid_rms = []

    for label, midi in PITCHES:
        for velocity_name, velocity in zip(("soft", "mid", "hard"), VELOCITIES):
            a = render_acoustic_guitar_note(midi, GATE, SR, r2, velocity=velocity)
            b = render_acoustic_guitar_note(midi, GATE, SR, r3, velocity=velocity)
            if not np.isfinite(a).all() or not np.isfinite(b).all():
                raise AssertionError(f"{label}/{velocity_name}: non-finite render")
            gain = _rms(a) / _rms(b)
            b_match = b * gain

            _write(OUT / f"{label}_A_R2_{velocity_name}.wav", a)
            _write(OUT / f"{label}_B_R3_{velocity_name}_raw.wav", b)
            _write(OUT / f"{label}_B_R3_{velocity_name}_rms_matched.wav", b_match)

            if velocity_name == "mid":
                mid_rms.append(_rms(b))
                delta = _rms(a - b_match) / _rms(a)
                manifest.append(
                    f"{label}: R3_mid_rms={_rms(b):.9f}; "
                    f"R2_to_R3_matched_delta_ratio={delta:.6f}; "
                    f"R3_match_gain={gain:.6f}"
                )

    level_ratio = max(mid_rms) / min(mid_rms)
    if level_ratio >= 1.35:
        raise AssertionError(f"R3 E2-E4 mid RMS ratio {level_ratio:.6f} >= 1.35")
    manifest += [
        f"",
        f"R3 E2-E4 mid RMS max/min: {level_ratio:.6f}",
        "",
        "Human gate:",
        "1. Listen to E4_B_R3_mid_raw.wav by itself first.",
        "2. Then E3_B_R3_mid_raw.wav and E2_B_R3_mid_raw.wav individually.",
        "3. Each note must independently read as generic steel-string acoustic guitar.",
        "4. A/B matched files are secondary diagnostics only; montage impression cannot close AG01.",
    ]
    (OUT / "MANIFEST.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    (OUT / "R3_PRESET.json").write_text(
        json.dumps(r3["acoustic_guitar_graph"], indent=2) + "\n", encoding="utf-8"
    )
    print("\n".join(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
