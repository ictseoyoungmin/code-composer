# Numerical reproducibility

Code Composer contains byte-exact audio regression tests. Those tests are stricter than ordinary perceptual or numerical-tolerance tests and can expose changes in low-level floating-point/DSP behavior across Python, NumPy/SciPy, libm, SIMD, CPU, and hosted-runner environments.

## Pinned CI numerical stack

GitHub CI pins:

- NumPy `2.2.6`
- SciPy `1.15.3`
- Python `3.10` and `3.12`

Both Python lanes run the blocking regression suite and release-surface builds.

## Runner-sensitive historical drum hashes

GitHub-hosted `ubuntu-latest` runners have produced different byte-exact drum hashes with unchanged source and the same pinned NumPy/SciPy stack.

Earlier evidence involved the S17, S20, and S21 byte-hash tests. The later S25-S27 lineage deliberately re-anchors on the S19 core, so the superseded S20-S24 runtime tests are now preserved under `docs/history/superseded/s20-s24/` rather than executed against the current runtime.

On PR #6 / CI #25, Python 3.12 passed the active suite while Python 3.10 passed **633 functional/blocking tests** and differed only in these two S25 historical byte hashes:

- `test_s25_preserves_s19_legacy_core_byte_exactly`
- `test_s25_does_not_change_existing_s17_modeled_preset_hashes`

The active runner-sensitive probe set is therefore:

- `test_s17_legacy_drum_path_is_byte_identical_to_s16_baseline`
- `test_s25_preserves_s19_legacy_core_byte_exactly`
- `test_s25_does_not_change_existing_s17_modeled_preset_hashes`

Python version alone is not treated as a sufficient environment key; the earlier mismatch appeared on Python 3.12 and the current S25 mismatch appeared on Python 3.10.

CI handles **only these active known byte-exact tests** specially:

1. the blocking suite excludes the three active node IDs above;
2. every other active regression test remains blocking;
3. the three exact-byte tests still execute on every CI lane as visible non-blocking probes;
4. historical golden hashes are not rewritten to match whichever hosted runner executes the job.

The underlying runner/CPU numerical sensitivity remains tracked in GitHub Issue #2.

This policy prevents unrelated repository or musical changes from being blocked by a hosted-runner fingerprint while preserving the evidence instead of deleting or silently rebasing it.

## Dependency policy

The project may run on other versions allowed by `pyproject.toml`, but a dependency upgrade must not silently redefine historical byte-exact golden hashes. Upgrade work should be treated as an explicit compatibility/reproducibility slice with listening evidence and regression review.

## Policy

- Musical/engine intent is authored in Code Composer source, not delegated to dependency-specific randomness.
- All active regression tests except the three explicitly tracked runner-sensitive byte hashes remain blocking in CI.
- Known byte hashes remain active probes until environment sensitivity is reproduced and eliminated or their exact-byte contract is replaced with a better evidence-backed invariant.
- Superseded runtime tests are historical evidence, not blockers for the current engine lineage.
- Golden hashes are not changed merely to make an unreviewed environment or dependency variation pass.
