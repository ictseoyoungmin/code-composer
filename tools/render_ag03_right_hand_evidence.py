#!/usr/bin/env python3
"""Render AG03 right-hand listening evidence from the actual branch."""
from __future__ import annotations

import os
from pathlib import Path
import wave

import numpy as np

from code_composer.audio.acoustic_guitar import render_acoustic_guitar_note
from code_composer.performance.guitar import resolve_fingering, resolve_right_hand
from code_composer.presets import materialize_preset


SR = 24000
GATE = 0.45
VELOCITY = 0.65
OUT = Path(os.environ.get("AG03_EVIDENCE_DIR", "artifacts/ag03-right-hand"))
METHODS = ("finger", "thumb", "nail", "pick")
CASES = (
    ("E4", 64, {"string": 1, "fret": 0}),
    ("E3", 52, {"string": 4, "fret": 2}),
)


def _write(path: Path, audio: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x * x)) + 1e-12)


def _centroid_50ms(x: np.ndarray) -> float:
    mono = x[: max(1, int(0.050 * SR))].mean(axis=1)
    win = np.hanning(len(mono))
    spec = np.abs(np.fft.rfft(mono * win))
    freqs = np.fft.rfftfreq(len(mono), 1.0 / SR)
    return float(np.sum(freqs * spec) / (np.sum(spec) + 1e-12))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    patch = materialize_preset("acoustic_guitar.steel_single_string", version="1.0.0")
    graph = patch["acoustic_guitar_graph"]

    lines = [
        "AG03 Right-Hand Excitation — canonical actual-branch evidence",
        f"git_sha: {os.environ.get('GITHUB_SHA', 'local')}",
        f"sample_rate: {SR}",
        f"gate_seconds: {GATE}",
        f"velocity: {VELOCITY}",
        "",
        "A = AG02 canonical (no right-hand mechanics)",
        "B/C/D/E = finger/thumb/nail/pick at identical pitch/string/fret/velocity",
        "Listening copies are RMS-matched to A; raw method renders are also included.",
        "",
    ]
    montage = []
    gap = np.zeros((int(0.28 * SR), 2), dtype=np.float64)
    case_gap = np.zeros((int(0.70 * SR), 2), dtype=np.float64)

    for label, midi, fingering_payload in CASES:
        fingering = resolve_fingering(midi, fingering_payload)
        base_perf = {"guitar_realization": fingering}
        a = render_acoustic_guitar_note(
            midi, GATE, SR, patch, velocity=VELOCITY, performance=base_perf
        )
        _write(OUT / f"{label}_A_AG02_canonical.wav", a)
        montage.append(a)

        lines.append(
            f"{label}: MIDI {midi}; string {fingering_payload['string']}; "
            f"fret {fingering_payload['fret']}; A_centroid_50ms={_centroid_50ms(a):.2f}"
        )

        for method in METHODS:
            rh = resolve_right_hand({"method": method}, graph)
            perf = {
                "guitar_realization": fingering,
                "right_hand_realization": rh,
            }
            raw = render_acoustic_guitar_note(
                midi, GATE, SR, patch, velocity=VELOCITY, performance=perf
            )
            gain = _rms(a) / _rms(raw)
            matched = raw * gain
            delta_ratio = _rms(a - matched) / _rms(a)
            _write(OUT / f"{label}_{method}_raw.wav", raw)
            _write(OUT / f"{label}_{method}_rms_matched.wav", matched)
            lines.append(
                f"  {method}: matched_delta_ratio={delta_ratio:.6f}; "
                f"rms_match_gain={gain:.6f}; "
                f"centroid_50ms={_centroid_50ms(matched):.2f}"
            )
            montage.extend([gap, matched])

        montage.append(case_gap)

    # Parameter-control diagnostics on E4 / string 1 / fret 0.
    fingering = resolve_fingering(64, {"string": 1, "fret": 0})
    control_cases = {
        "finger_near_bridge": {"method": "finger", "pluck_position": 0.07},
        "finger_away_bridge": {"method": "finger", "pluck_position": 0.28},
        "pick_shallow": {"method": "pick", "attack_angle_deg": 15.0},
        "pick_steep": {"method": "pick", "attack_angle_deg": 75.0},
        "nail_light": {"method": "nail", "strength": 0.2},
        "nail_strong": {"method": "nail", "strength": 0.9},
    }
    for name, payload in control_cases.items():
        rh = resolve_right_hand(payload, graph)
        audio = render_acoustic_guitar_note(
            64,
            GATE,
            SR,
            patch,
            velocity=VELOCITY,
            performance={
                "guitar_realization": fingering,
                "right_hand_realization": rh,
            },
        )
        _write(OUT / f"CONTROL_{name}.wav", audio)

    _write(OUT / "AG03_methods_montage_24k.wav", np.concatenate(montage, axis=0))
    lines += [
        "",
        "Human listening gate:",
        "1. A must retain the accepted AG02/AG01 guitar identity.",
        "2. finger/thumb/nail/pick should be distinguishable as excitation/attack changes.",
        "3. None of the methods should sound like a different instrument or an EQ preset.",
        "4. Parameter-control WAVs are diagnostics for pluck position / angle / strength.",
        "AG03 remains OPEN until explicit human listening PASS.",
    ]
    (OUT / "MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
