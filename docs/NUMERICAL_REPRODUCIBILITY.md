# Numerical reproducibility

Code Composer contains byte-exact audio regression tests. Those tests are stricter than ordinary perceptual or numerical-tolerance tests and can expose changes in low-level floating-point/DSP behavior across Python, NumPy/SciPy, libm, SIMD, CPU, and hosted-runner environments.

## Pinned CI numerical stack

GitHub CI pins:

- NumPy `2.2.6`
- SciPy `1.15.3`
- Python `3.10` and `3.12`

Both Python lanes run the blocking regression suite and release-surface builds.

## Runner-sensitive historical drum hashes

Three historical percussion byte-hash tests have produced two different deterministic hash sets across GitHub-hosted `ubuntu-latest` runners even with unchanged source and the same pinned NumPy/SciPy versions:

- `test_s17_legacy_drum_path_is_byte_identical_to_s16_baseline`
- `test_s20_existing_modeled_kick_snare_closed_hat_are_byte_identical_to_s19`
- `test_s21_s20_preset_and_existing_default_hits_remain_byte_identical`

The behavior has appeared on both Python 3.10 and Python 3.12, so Python version alone is not a sufficient environment key.

CI therefore handles **only these three known tests** specially:

1. the blocking suite excludes these three node IDs;
2. all other regression tests remain blocking;
3. the three exact-byte tests still run on every CI lane as a visible non-blocking probe;
4. their historical golden hashes are not rewritten to match whichever hosted runner happens to execute the job.

The underlying runner/CPU numerical sensitivity remains tracked in GitHub Issue #2.

This policy prevents unrelated repository or musical changes from being blocked by a known hosted-runner fingerprint while preserving the evidence instead of deleting or silently rebasing it.

## Dependency policy

The project may run on other versions allowed by `pyproject.toml`, but a dependency upgrade must not silently redefine historical byte-exact golden hashes. Upgrade work should be treated as an explicit compatibility/reproducibility slice with listening evidence and regression review.

## Policy

- Musical/engine intent is authored in Code Composer source, not delegated to dependency-specific randomness.
- All regression tests except the three explicitly tracked runner-sensitive drum hashes remain blocking in CI.
- The three known hashes remain active probes until the environment sensitivity is reproduced and eliminated or their exact-byte contract is replaced with a better evidence-backed invariant.
- Golden hashes are not changed merely to make an unreviewed environment or dependency upgrade pass.
