# Numerical reproducibility

Code Composer contains byte-exact audio regression tests. Those tests are stricter than ordinary perceptual or numerical-tolerance tests and can expose changes in low-level floating-point/DSP behavior across NumPy/SciPy releases.

## Canonical CI stack

The GitHub CI regression stack pins:

- NumPy `2.2.6`
- SciPy `1.15.3`

The project may run on other versions allowed by `pyproject.toml`, but a dependency upgrade must not silently redefine historical byte-exact golden hashes. Upgrade work should be treated as an explicit compatibility/reproducibility slice with listening evidence and regression review.

## Policy

- Musical/engine intent is authored in Code Composer source, not delegated to dependency-specific randomness.
- Byte-exact legacy baselines remain stable on the canonical CI numerical stack.
- Broader supported dependency ranges may be tested separately for functional compatibility.
- Golden hashes are not changed merely to make an unreviewed dependency upgrade pass.
