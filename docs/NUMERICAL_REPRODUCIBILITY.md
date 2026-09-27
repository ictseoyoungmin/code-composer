# Numerical reproducibility

Code Composer contains byte-exact audio regression tests. Those tests are stricter than perceptual or ordinary tolerance tests, so a public byte boundary must not inherit irrelevant CPU-specific floating-point dispatch noise.

## Pinned CI numerical stack

GitHub CI pins:

- NumPy `2.2.6`
- SciPy `1.15.3`
- Python `3.10` and `3.12`

Both Python lanes run the complete blocking regression suite and release-surface builds.

## Issue #2 — drum byte reproducibility closure

Issue #2 tracked intermittent raw SHA-256 mismatches in legacy and modeled percussion while source, seed, NumPy and SciPy versions were unchanged.

### Root cause

Fresh v1.18.0 main CI #133 reproduced the split: one hosted runner matched the historical bytes while another did not.

Dedicated diagnostic runs isolated the cause:

- pre-fix diagnostic run `36326929690`;
- exact float64 artifacts: `10934033682` (Python 3.10) and `10934242266` (Python 3.12);
- Python 3.10 and 3.12 were bit-identical when placed on the same CPU/dispatch path;
- disabling NumPy `FMA3` changed the raw SHA set in both Python versions;
- native versus FMA-disabled waveform differences were only float64 last-bit noise: max absolute sample delta `2.78e-16` full scale and relative RMS delta about `1.5e-16`.

The nondeterminism was CPU/NumPy floating-point dispatch, not RNG, authored music, or a semantic percussion change.

### Canonical percussion byte boundary

`render_drum_event()` now canonicalizes the final post-pan stereo float64 output to an exact **Q40** grid:

- grid step: `2^-40 ≈ 9.09e-13` full scale;
- maximum sample movement: `2^-41 ≈ 4.55e-13` full scale;
- maximum movement is roughly `-246.8 dBFS`;
- synthesis, seeded variation, envelopes, filters, pan and all musical parameters run before this representation boundary unchanged.

Q40 is much finer than any meaningful audio tolerance while leaving enough margin that last-bit FMA/SIMD differences cannot straddle the public byte contract.

### Cross-environment proof

Post-fix diagnostic run `36327235285` produced exact raw SHA-256 identity for legacy, modeled and S19-core kick/snare/hat across all tested combinations:

- Python 3.10 on AMD EPYC 7763;
- Python 3.12 on AMD EPYC 9V45;
- native NumPy dispatch;
- `FMA3` disabled;
- `AVX2,FMA3` disabled;
- `AVX,AVX2,F16C,FMA3` disabled.

Artifacts:

- `10934541550` — Python 3.10 feature sweep;
- `10934671124` — Python 3.12 feature sweep.

All nine captured drum arrays had one raw SHA per signal across the eight environment/dispatch combinations.

The historical cross-runner exception is removed. Canonical percussion byte hashes are normal blocking regressions again.

## Dependency policy

The project may run on other versions allowed by `pyproject.toml`, but a dependency upgrade must not silently redefine canonical byte fingerprints. Upgrade work remains an explicit compatibility/reproducibility slice with regression review.

## Policy

- Musical/engine intent is authored in Code Composer source, not delegated to dependency-specific randomness.
- Canonical public byte boundaries may remove sub-machine-noise floating-point dispatch variation only when the bound is explicit, documented, and far below meaningful signal tolerance.
- Canonical percussion hashes are blocking on every CI lane.
- Golden hashes are never rewritten merely to match an unreviewed runner; Issue #2 changes the representation boundary with measured evidence and new explicit canonical hashes.
