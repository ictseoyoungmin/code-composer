# Numerical reproducibility

Code Composer contains byte-exact audio regression tests. Those tests are stricter than ordinary perceptual or numerical-tolerance tests and can expose changes in low-level floating-point/DSP behavior across Python, NumPy/SciPy, libm, SIMD, and runner environments.

## Canonical byte-exact CI lane

Historical byte-exact golden hashes are authoritative on:

- Python `3.10`
- NumPy `2.2.6`
- SciPy `1.15.3`
- GitHub Actions `ubuntu-latest` x86_64 runner family

The Python 3.10 lane runs the complete regression suite and is the canonical byte-exact compatibility gate.

## Python 3.12 compatibility lane

Python 3.12 is retained as a supported functional-compatibility lane on the same pinned NumPy/SciPy versions.

Three historical percussion tests have shown environment-sensitive byte hashes on Python 3.12 while the same source passes the canonical Python 3.10 lane:

- `test_s17_legacy_drum_path_is_byte_identical_to_s16_baseline`
- `test_s20_existing_modeled_kick_snare_closed_hat_are_byte_identical_to_s19`
- `test_s21_s20_preset_and_existing_default_hits_remain_byte_identical`

Those three tests are excluded from the blocking Python 3.12 functional suite and are still executed as a visible non-blocking probe. The discrepancy is tracked in GitHub Issue #2.

This is **not** permission to change the historical golden hashes. The probe remains visible until the underlying environment sensitivity is reproduced and eliminated or the exact-byte contract is further narrowed with evidence.

## Dependency policy

The project may run on other versions allowed by `pyproject.toml`, but a dependency upgrade must not silently redefine historical byte-exact golden hashes. Upgrade work should be treated as an explicit compatibility/reproducibility slice with listening evidence and regression review.

## Policy

- Musical/engine intent is authored in Code Composer source, not delegated to dependency-specific randomness.
- Byte-exact legacy baselines remain stable on the canonical CI lane.
- Broader supported Python/dependency ranges are tested separately for functional compatibility.
- Known environment-sensitive byte probes remain visible rather than being deleted or silently rebaselined.
- Golden hashes are not changed merely to make an unreviewed environment or dependency upgrade pass.
