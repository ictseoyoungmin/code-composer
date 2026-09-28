# AG01 — Single-String Steel Acoustic Core Closure

Status: **CANONICAL CLOSED · HUMAN LISTENING PASS**

Target release: **v1.19.0**

## Canonical result

AG01 establishes the accepted single-string steel-string acoustic baseline:

```text
steel string
  ↓
bridge drive
  ↓
guitar body / air radiation
  ↓
stereo output
```

Canonical preset: `acoustic_guitar.steel_single_string@1.0.0`.

The AG00 `acoustic_guitar.steel_foundation@1.0.0` path remains available as the historical routing/listening A baseline.

## Closure evidence

- GitHub Issue #54 — closed / completed.
- PR #55 — merged.
- final listening HEAD: `926b7197f547601919daff990dea8bd48b04840a`.
- PR CI #154 — SUCCESS.
- merge main: `921253594224d44b331dc394f31cf9c199616368`.
- Python 3.10 / 3.12 blocking regression and build — PASS on the accepted R2 HEAD.
- listening protocol: E2 / E3 / E4 × soft / mid / hard at 24 kHz.
- one global B-side RMS match preserved relative velocity and register dynamics.
- explicit user human listening verdict: **PASS**.

## R2 correction retained

R1 exposed excessive E2→E4 output-level collapse before human listening. R2 added one bounded body-radiation key-tracking slope, `radiation_keytrack=1.10` around E3. A blocking regression keeps the E2/E3/E4 mid-velocity RMS max/min ratio below 1.35.

This is a radiation-balance correction, not automatic composition or voicing logic.

## Scope boundary

AG01 closes only the single-string audible core. It does **not** close:

- six-string identity or string/fret authority — AG02;
- finger/nail/pick excitation semantics — AG03;
- left-hand articulation/damping — AG04;
- multi-string fingerstyle/arpeggio — AG05;
- strum traversal — AG06;
- body percussion — AG07;
- persistent six-string/body coupling — AG08.

## Provenance

The model remains independently implemented and uses generic project-authored modal body values. It bundles no third-party guitar code, recordings, IRs, measured modal tables, FEM meshes, or named-instrument fitted responses.
