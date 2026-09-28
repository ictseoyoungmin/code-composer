#!/usr/bin/env python3
"""Render AG02-on-R3 A/B/C evidence from the actual Code Composer branch."""
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
OUT = Path(os.environ.get("AG02_R3_EVIDENCE_DIR", "artifacts/ag02-r3"))
CASES = [
    ("E4", 64, (1, 0), (2, 5)),
    ("E3", 52, (4, 2), (6, 12)),
    ("C4", 60, (2, 1), (4, 10)),
]


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


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    patch = materialize_preset("acoustic_guitar.steel_single_string", version="1.0.0")
    graph = patch["acoustic_guitar_graph"]
    assert graph["physical_model"] == "ag01_modal_bridge_body_v2"
    assert graph["string_source_model"] == "triangular_pluck_bridge_force_v2"

    short = np.zeros((int(0.30 * SR), 2), dtype=np.float64)
    long_gap = np.zeros((int(0.70 * SR), 2), dtype=np.float64)
    montage = []
    lines = [
        "AG02 on AG01 R3 canonical A/B/C evidence",
        f"git_sha: {os.environ.get('GITHUB_SHA', 'local')}",
        f"sample_rate: {SR}",
        f"gate_seconds: {GATE_S}",
        f"velocity: {VELOCITY}",
        "",
        "A = AG01 R3 canonical render with no AG02 mechanics",
        "B = AG02 explicit canonical reference position; MUST be sample-exact with A",
        "C = same MIDI at an alternate valid string/fret position",
        "C listening copy is RMS-matched to A; raw C is also included.",
        "",
    ]

    for label, midi, ref_pos, alt_pos in CASES:
        reference = resolve_fingering(
            midi, {"string": ref_pos[0], "fret": ref_pos[1]}
        )
        alternate = resolve_fingering(
            midi, {"string": alt_pos[0], "fret": alt_pos[1]}
        )
        assert reference["position_is_reference"] is True
        assert alternate["position_is_reference"] is False

        a = render_acoustic_guitar_note(midi, GATE_S, SR, patch, velocity=VELOCITY)
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
            raise AssertionError(f"{label}: reference mechanics drifted from AG01 R3")

        delta_ratio = _rms(a - c) / _rms(a)
        if not 1e-6 < delta_ratio < 0.12:
            raise AssertionError(
                f"{label}: alternate delta ratio {delta_ratio:.6f} outside (0, 0.12)"
            )

        c_gain = _rms(a) / _rms(c)
        c_match = c * c_gain
        peak = max(
            float(np.max(np.abs(a))),
            float(np.max(np.abs(b))),
            float(np.max(np.abs(c_match))),
        )
        common = 0.94 / peak if peak > 0.94 else 1.0
        a_listen = a * common
        b_listen = b * common
        c_listen = c_match * common

        _write(OUT / f"{label}_A_AG01_R3_canonical.wav", a)
        _write(OUT / f"{label}_B_AG02_reference.wav", b)
        _write(OUT / f"{label}_C_AG02_alternate_raw.wav", c)
        _write(OUT / f"{label}_C_AG02_alternate_rms_matched.wav", c_listen)

        montage.extend([a_listen, short, b_listen, short, c_listen, long_gap])
        lines.append(
            f"{label}: MIDI {midi}; "
            f"reference=string {ref_pos[0]}/fret {ref_pos[1]}; "
            f"alternate=string {alt_pos[0]}/fret {alt_pos[1]}; "
            f"A==B sample_exact=true; C_delta_ratio={delta_ratio:.6f}; "
            f"C_rms_match_gain={c_gain:.6f}"
        )

    _write(OUT / "AG02_R3_ABC_montage_24k.wav", np.concatenate(montage, axis=0))
    lines += [
        "",
        "Human listening rule:",
        "1. Verify A still has the accepted AG01 R3 guitar identity.",
        "2. A and B should be audibly identical.",
        "3. C should remain the same accepted guitar, with only a subtle position change.",
        "AG02 remains OPEN until explicit human listening PASS.",
    ]
    (OUT / "MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
