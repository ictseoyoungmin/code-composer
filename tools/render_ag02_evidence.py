#!/usr/bin/env python3
"""Render AG02 R2 evidence from the actual Code Composer branch implementation."""
from __future__ import annotations

import os
from pathlib import Path
import wave

import numpy as np

from code_composer.audio.acoustic_guitar import render_acoustic_guitar_note
from code_composer.performance.guitar import resolve_fingering
from code_composer.presets import materialize_preset


SR = 24000
GATE_S = 0.45
VELOCITY = 0.65
OUT = Path(os.environ.get("AG02_EVIDENCE_DIR", "artifacts/ag02-r2"))
CASES = [
    ("E4", 64, (1, 0), (2, 5)),
    ("C4_D10", 60, (2, 1), (4, 10)),
    ("C4_LOW_E20", 60, (2, 1), (6, 20)),
]


def _write_wav(path: Path, audio: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def _rms(audio: np.ndarray) -> float:
    return float(np.sqrt(np.mean(audio * audio)) + 1e-12)


def _pad(audio: np.ndarray, n: int) -> np.ndarray:
    out = np.zeros((n, 2), dtype=np.float64)
    out[: len(audio)] = audio
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    patch = materialize_preset("acoustic_guitar.steel_single_string", version="1.0.0")
    silence_short = np.zeros((int(0.30 * SR), 2), dtype=np.float64)
    silence_long = np.zeros((int(0.70 * SR), 2), dtype=np.float64)
    montage = []
    lines = [
        "AG02 R2 canonical A/B/C listening evidence",
        f"git_sha: {os.environ.get('GITHUB_SHA', 'local')}",
        f"sample_rate: {SR}",
        f"gate_seconds: {GATE_S}",
        f"velocity: {VELOCITY}",
        "",
        "A = AG01 canonical render (no AG02 mechanics)",
        "B = AG02 explicit reference position (must be sample-exact with A)",
        "C = AG02 alternate valid position (bounded physical delta)",
        "",
    ]

    for label, midi, reference_pos, alternate_pos in CASES:
        reference = resolve_fingering(
            midi, {"string": reference_pos[0], "fret": reference_pos[1]}
        )
        alternate = resolve_fingering(
            midi, {"string": alternate_pos[0], "fret": alternate_pos[1]}
        )
        if not reference["position_is_reference"]:
            raise AssertionError(f"{label}: declared reference is not canonical")
        if alternate["position_is_reference"]:
            raise AssertionError(f"{label}: alternate unexpectedly equals reference")

        a = render_acoustic_guitar_note(
            midi, GATE_S, SR, patch, velocity=VELOCITY
        )
        b = render_acoustic_guitar_note(
            midi,
            GATE_S,
            SR,
            patch,
            velocity=VELOCITY,
            performance={"guitar_realization": reference},
        )
        c = render_acoustic_guitar_note(
            midi,
            GATE_S,
            SR,
            patch,
            velocity=VELOCITY,
            performance={"guitar_realization": alternate},
        )

        if not np.array_equal(a, b):
            raise AssertionError(f"{label}: AG02 reference drifted from AG01 canonical")

        n = max(len(a), len(c))
        ap = _pad(a, n)
        cp = _pad(c, n)
        delta = _rms(ap - cp)
        ratio = delta / _rms(ap)
        if not 1e-6 < ratio < 0.20:
            raise AssertionError(
                f"{label}: alternate-position delta ratio {ratio:.6f} outside (0, 0.20)"
            )

        c_gain = _rms(a) / _rms(c)
        c_matched = c * c_gain
        peak = max(
            float(np.max(np.abs(a))),
            float(np.max(np.abs(b))),
            float(np.max(np.abs(c_matched))),
        )
        common = 0.94 / peak if peak > 0.94 else 1.0
        a_listen = a * common
        b_listen = b * common
        c_listen = c_matched * common

        _write_wav(OUT / f"{label}_A_AG01_canonical.wav", a)
        _write_wav(OUT / f"{label}_B_AG02_reference.wav", b)
        _write_wav(OUT / f"{label}_C_AG02_alternate_raw.wav", c)
        _write_wav(OUT / f"{label}_C_AG02_alternate_rms_matched.wav", c_listen)

        montage.extend([a_listen, silence_short, b_listen, silence_short, c_listen, silence_long])
        lines.append(
            f"{label}: MIDI {midi}; reference=string {reference_pos[0]}/fret {reference_pos[1]}; "
            f"alternate=string {alternate_pos[0]}/fret {alternate_pos[1]}; "
            f"A==B sample_exact=true; C_delta_ratio={ratio:.6f}; "
            f"C_listening_rms_gain={c_gain:.6f}"
        )

    _write_wav(OUT / "AG02_R2_ABC_montage_24k.wav", np.concatenate(montage, axis=0))
    lines += [
        "",
        "Listening order per case: A -> B -> C.",
        "A and B must sound identical because B only establishes mechanics identity.",
        "C should remain the same accepted guitar while showing a subtle position change.",
        "AG02 remains OPEN until explicit human listening PASS.",
    ]
    (OUT / "MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
