# v1.16 H2 — Contract Parity

Status: CLOSED

## Fixed

The public schemas were previously weaker than the Python runtime contract.

H2 strengthens:

- phrase dynamic/timing/gate value ranges
- curve endpoint presence
- non-empty transform rhythm/interval arrays
- complete enabled harmonic anticipation payload
- complete enabled pickup payload
- bass-approach conditional fields
- cadence-extension all-or-empty structure
- texture-subtraction all-or-empty structure
- rhythm-fill all-or-empty structure
- positive register-preparation duration
- unique role pairs
- full nested `PerformanceIR` phrase / motif / register / orchestration / transition structures

`PerformanceIR` no longer exposes generic `object` placeholders for those fields.

## Explicit Python-only invariants

Some rules are intentionally not duplicated in JSON Schema because they require runtime context or relational arithmetic:

- section/role/source-material cross references
- form adjacency
- unique phrase/statement IDs across objects
- phrase/breath temporal overlap
- monotonic control-point ordering
- range low <= high / preferred containment / center containment / max-span width
- orchestration group disjointness and role membership
- max-role budget versus active role cardinality
- reverse-order overlap-pair duplicate detection
- pickup rhythm length equality and total duration <= pickup window
- transform rhythm/interval length relationships
- source-material-dependent motif execution

These are declared in the schema's `x-python-only-invariants` field and remain mandatory in the Python validator.

## Audit counterexamples

The structural failures found by the full audit now fail at both layers:

```text
incomplete enabled anticipation    schema FAIL / runtime FAIL
incomplete enabled pickup          schema FAIL / runtime FAIL
partial cadence extension          schema FAIL / runtime FAIL
out-of-range dynamic curve         schema FAIL / runtime FAIL
duplicate primary role             schema FAIL / runtime FAIL
```

Expected Python-only cases remain:

```text
unknown contextual role            schema PASS / runtime FAIL
reversed hard range                schema PASS / runtime FAIL
pickup rhythm sum > window         schema PASS / runtime FAIL
```

## Verification

- focused contract tests: 32 PASS
- full regression: 202 / 202 PASS
- coverage: 87%
- import failures: 0
- H1 -> H2 Composer Plan: byte-identical
- H1 -> H2 Music IR: byte-identical
- H1 -> H2 representative WAV: byte-identical

Representative legacy hashes:

- Composer Plan: `f7f16714e9d98666ae29d27b0c183d89fdd14aa82de9d4d4869cdb45ef2ee302`
- Music IR: `ef60c5f7388bddb0cd6eff857ee2dc937f3d819deb017a87a95d4146faa04b51`
- WAV: `589ac3efdc466a1a7c191caa0e614a63b1a28e4dea566b08164df3730f4490e0`

## Remaining hardening

H2 closes the audit's schema/runtime parity defect.

Next:
- H3 E2 semantic closure (`call`, identity-floor semantics)
- H4 canonical revision-surface cleanup
- H5 reference/package hygiene
