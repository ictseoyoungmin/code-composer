from __future__ import annotations

"""Compact bridge-admittance identification utilities.

The fitter consumes a preprocessed bridge-admittance impulse response and derives a
reduced-order SISO state-space realization with the Eigensystem Realization
Algorithm (ERA).  The runtime representation is diagonalized into poles and
residues so the fitted response can be evaluated in O(M) per sample.

This module intentionally does not ship measurements of a named instrument.
Measurement provenance belongs to the caller / repository evidence, while the
installed skill only contains the generic fitting machinery.
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import wavfile

FORMAT = "code-composer-bridge-admittance-era/v1"


class BridgeAdmittanceFitError(ValueError):
    pass


def _finite_real_vector(values: Any) -> np.ndarray:
    y = np.asarray(values, dtype=np.float64).reshape(-1)
    if len(y) < 16:
        raise BridgeAdmittanceFitError("impulse response must contain at least 16 samples")
    if not np.isfinite(y).all():
        raise BridgeAdmittanceFitError("impulse response contains non-finite values")
    if float(np.max(np.abs(y))) <= 0.0:
        raise BridgeAdmittanceFitError("impulse response must not be silent")
    return y


def _nmse(reference: np.ndarray, estimate: np.ndarray) -> float:
    n = min(len(reference), len(estimate))
    ref = np.asarray(reference[:n], dtype=np.float64)
    est = np.asarray(estimate[:n], dtype=np.float64)
    den = float(np.sum(ref * ref))
    if den <= 1e-30:
        return 0.0
    return float(np.sum((ref - est) ** 2) / den)


def _complex_pairs(values: np.ndarray) -> list[list[float]]:
    return [[float(np.real(v)), float(np.imag(v))] for v in values]


def _as_complex_pairs(values: list[list[float]]) -> np.ndarray:
    out = []
    for item in values:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise BridgeAdmittanceFitError("complex values must be [real, imag] pairs")
        out.append(complex(float(item[0]), float(item[1])))
    return np.asarray(out, dtype=np.complex128)


def impulse_response_from_profile(profile: dict, length: int) -> np.ndarray:
    """Synthesize the discrete impulse response represented by a fitted profile."""
    validate_era_profile(profile)
    n = max(1, int(length))
    poles = _as_complex_pairs(profile["poles"])
    residues = _as_complex_pairs(profile["residues"])
    direct = float(profile.get("direct", 0.0))
    scale = float(profile.get("output_scale", 1.0))
    state = np.zeros(len(poles), dtype=np.complex128)
    out = np.zeros(n, dtype=np.float64)
    for k in range(n):
        u = 1.0 if k == 0 else 0.0
        y = direct * u + float(np.real(np.sum(residues * state)))
        out[k] = y * scale
        state = poles * state + u
    return out


def _stabilize_poles(poles: np.ndarray, max_radius: float) -> tuple[np.ndarray, int]:
    out = np.asarray(poles, dtype=np.complex128).copy()
    changed = 0
    for i, p in enumerate(out):
        r = abs(p)
        if r >= max_radius:
            if r <= 1e-15:
                out[i] = 0j
            else:
                out[i] = p * (max_radius / r)
            changed += 1
    return out, changed


def fit_era_impulse_response(
    impulse_response: Any,
    sample_rate_hz: int,
    *,
    order: int = 24,
    hankel_rows: int | None = None,
    hankel_cols: int | None = None,
    stabilize: bool = True,
    max_pole_radius: float = 0.99995,
    output_scale: float = 1.0,
    source: dict | None = None,
) -> dict:
    """Fit a compact ERA realization from a bridge-admittance impulse response.

    The input should already represent the force->bridge-velocity impulse response.
    Measurement-specific preprocessing (repeat averaging, force normalization,
    minimum-phase conversion, and noise-tail cropping) is deliberately kept outside
    the installed runtime so provenance remains explicit.
    """
    y = _finite_real_vector(impulse_response)
    sr = int(sample_rate_hz)
    if not (4000 <= sr <= 384000):
        raise BridgeAdmittanceFitError("sample_rate_hz outside supported range")
    m = int(order)
    if not (2 <= m <= 64):
        raise BridgeAdmittanceFitError("order must be in [2,64]")
    if not (0.90 <= float(max_pole_radius) < 1.0):
        raise BridgeAdmittanceFitError("max_pole_radius must be in [0.90,1.0)")

    max_side = max(2, (len(y) - 2) // 2)
    default_side = min(max_side, max(2 * m, 48))
    r = int(hankel_rows or default_side)
    s = int(hankel_cols or default_side)
    if r < m or s < m:
        raise BridgeAdmittanceFitError("Hankel dimensions must be >= order")
    if r + s + 1 > len(y):
        # Preserve the requested aspect ratio as much as possible while fitting.
        side = (len(y) - 2) // 2
        r = min(r, side)
        s = min(s, len(y) - r - 1)
    if r < m or s < m or r + s + 1 > len(y):
        raise BridgeAdmittanceFitError("impulse response too short for requested ERA order")

    # H0[i,j] = y[i+j+1], H1[i,j] = y[i+j+2]
    idx0 = np.add.outer(np.arange(r), np.arange(s)) + 1
    h0 = y[idx0]
    h1 = y[idx0 + 1]
    u, sing, vt = np.linalg.svd(h0, full_matrices=False)
    if len(sing) < m or sing[m - 1] <= max(1e-15, sing[0] * 1e-14):
        # Reduce to the numerically supported rank rather than inventing modes.
        support = int(np.sum(sing > max(1e-15, sing[0] * 1e-14)))
        m = max(2, min(m, support))
    um = u[:, :m]
    sm = sing[:m]
    vm = vt[:m, :].T
    root = np.sqrt(sm)
    inv_root = 1.0 / np.maximum(root, 1e-15)
    a = (inv_root[:, None] * (um.T @ h1 @ vm)) * inv_root[None, :]
    b = root * vm[0, :]
    c = root * um[0, :]
    direct = float(y[0])

    eigvals, q = np.linalg.eig(a)
    try:
        qinv = np.linalg.inv(q)
    except np.linalg.LinAlgError as exc:
        raise BridgeAdmittanceFitError("ERA realization is not diagonalizable") from exc
    b_modal = qinv @ b
    c_modal = q.T @ c
    residues = c_modal * b_modal

    stabilized = 0
    if stabilize:
        eigvals, stabilized = _stabilize_poles(eigvals, float(max_pole_radius))

    # Stable sort by modal frequency then damping so emitted JSON is deterministic.
    angles = np.mod(np.angle(eigvals), 2.0 * np.pi)
    freq = np.minimum(angles, 2.0 * np.pi - angles) * sr / (2.0 * np.pi)
    order_idx = np.lexsort((np.abs(eigvals), freq))
    eigvals = eigvals[order_idx]
    residues = residues[order_idx]

    profile = {
        "format": FORMAT,
        "method": "era",
        "reference_sample_rate_hz": sr,
        "order": int(len(eigvals)),
        "poles": _complex_pairs(eigvals),
        "residues": _complex_pairs(residues),
        "direct": direct,
        "output_scale": float(output_scale),
        "stabilized_poles": int(stabilized),
        "hankel_rows": int(r),
        "hankel_cols": int(s),
        "source": dict(source or {}),
    }
    estimate = impulse_response_from_profile(profile, min(len(y), max(2048, r + s + 1)))
    profile["fit_metrics"] = {
        "nmse_time": _nmse(y, estimate),
        "reference_samples": int(min(len(y), len(estimate))),
    }
    validate_era_profile(profile)
    return profile


def fit_era_wav(
    path: str | Path,
    *,
    order: int = 24,
    channel: int = 0,
    normalize_peak: bool = False,
    source: dict | None = None,
) -> dict:
    sr, raw = wavfile.read(str(path))
    data = np.asarray(raw)
    if data.ndim == 2:
        if not (0 <= int(channel) < data.shape[1]):
            raise BridgeAdmittanceFitError("WAV channel index out of range")
        data = data[:, int(channel)]
    if np.issubdtype(data.dtype, np.integer):
        info = np.iinfo(data.dtype)
        denom = max(abs(info.min), abs(info.max))
        y = data.astype(np.float64) / float(denom)
    else:
        y = data.astype(np.float64)
    if normalize_peak:
        peak = float(np.max(np.abs(y)))
        if peak > 0:
            y = y / peak
    src = {"path": Path(path).name}
    src.update(source or {})
    return fit_era_impulse_response(y, int(sr), order=order, source=src)


def validate_era_profile(profile: dict) -> None:
    if not isinstance(profile, dict) or profile.get("format") != FORMAT:
        raise BridgeAdmittanceFitError("invalid ERA bridge-admittance profile format")
    sr = int(profile.get("reference_sample_rate_hz", 0))
    if not (4000 <= sr <= 384000):
        raise BridgeAdmittanceFitError("invalid reference_sample_rate_hz")
    poles = _as_complex_pairs(profile.get("poles", []))
    residues = _as_complex_pairs(profile.get("residues", []))
    if not (2 <= len(poles) <= 64) or len(residues) != len(poles):
        raise BridgeAdmittanceFitError("ERA profile must contain 2..64 matching poles/residues")
    if not np.isfinite(poles.real).all() or not np.isfinite(poles.imag).all():
        raise BridgeAdmittanceFitError("ERA profile contains non-finite poles")
    if not np.isfinite(residues.real).all() or not np.isfinite(residues.imag).all():
        raise BridgeAdmittanceFitError("ERA profile contains non-finite residues")
    if float(np.max(np.abs(poles))) >= 1.0:
        raise BridgeAdmittanceFitError("ERA profile contains unstable pole")
    direct = float(profile.get("direct", 0.0))
    scale = float(profile.get("output_scale", 1.0))
    if not math.isfinite(direct) or not math.isfinite(scale) or not (0.0 < scale <= 1e6):
        raise BridgeAdmittanceFitError("invalid ERA direct/output_scale")


@dataclass
class EraAdmittanceState:
    """O(M) runtime state for a fitted ERA bridge-admittance profile."""

    poles: np.ndarray
    residues: np.ndarray
    direct: float
    output_scale: float
    state: np.ndarray

    @classmethod
    def from_profile(cls, profile: dict, runtime_sample_rate_hz: int) -> "EraAdmittanceState":
        validate_era_profile(profile)
        poles = _as_complex_pairs(profile["poles"])
        residues = _as_complex_pairs(profile["residues"])
        ref_sr = float(profile["reference_sample_rate_hz"])
        run_sr = float(runtime_sample_rate_hz)
        if not (4000 <= run_sr <= 384000):
            raise BridgeAdmittanceFitError("invalid runtime sample rate")
        if abs(run_sr - ref_sr) > 1e-9:
            # Preserve each identified continuous-time modal frequency/decay rate.
            # Residues remain in the normalized bridge-velocity domain; the caller
            # controls absolute feedback magnitude with feedback_gain/output_scale.
            exponent = ref_sr / run_sr
            poles = np.exp(np.log(poles) * exponent)
        return cls(
            poles=poles,
            residues=residues,
            direct=float(profile.get("direct", 0.0)),
            output_scale=float(profile.get("output_scale", 1.0)),
            state=np.zeros(len(poles), dtype=np.complex128),
        )

    def tick(self, excitation: float) -> float:
        u = float(excitation)
        y = self.direct * u + float(np.real(np.sum(self.residues * self.state)))
        self.state = self.poles * self.state + u
        return y * self.output_scale


def write_profile(profile: dict, path: str | Path) -> None:
    validate_era_profile(profile)
    Path(path).write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8")


__all__ = [
    "FORMAT",
    "BridgeAdmittanceFitError",
    "EraAdmittanceState",
    "fit_era_impulse_response",
    "fit_era_wav",
    "impulse_response_from_profile",
    "validate_era_profile",
    "write_profile",
]
