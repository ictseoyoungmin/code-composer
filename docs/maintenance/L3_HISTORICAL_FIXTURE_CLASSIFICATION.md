# Legacy Cleanup L3 — Historical Documentation / Fixture Classification

Status: **CLOSED**

v1.16.0 remains **CLOSED**. L3 changes documentation/reference classification only; no runtime module, public import, schema, fixture payload, Music IR, or audio evidence is removed.

## Goal

L2 removed superseded analyzer-driven mutation code. L3 creates a hard boundary between:

- **CURRENT** — present release/repository authority,
- **ACTIVE_DOMAIN** — live domain contracts and executable authoring references,
- **HISTORICAL_EVIDENCE** — closed design, validation, dogfood, and maintenance evidence,
- **COMPATIBILITY_FIXTURE** — stable regression inputs that must not drift,
- **PACKAGE_MIRROR** — wheel-shipped synchronized copies,
- **L4_CANDIDATE** — files allowed to enter the next deletion review.

The classification is exhaustive over root status/navigation files plus `docs/`, `examples/`, `schemas/`, `tests/fixtures/`, and `src/code_composer/reference/`.

## Current authority cleanup

Two stale statements in current navigation were corrected without rewriting historical documents:

1. the root README no longer says the v1.16 final release is still open;
2. the root README no longer lists `transition_material_analysis` as an L2 removal target, because L2 proved the canonical E5 provenance analyzer is still live.

`STRUCTURE.md` now distinguishes active references, legacy compatibility fixtures, final-closure evidence, and package mirrors. Historical documents keep their original status text as evidence.

## L4 candidate boundary

Exactly **12 files / 37,197,041 bytes (~37.2 MB)** are marked for L4 review and nothing is deleted in L3.

For each of the three final-closure cases:

- `after_repeat.wav` — byte-identical to retained `after.wav`,
- `analysis_after_repeat.json` — byte-identical to retained `analysis_after.json`,
- `resolved_after_repeat.json` — byte-identical to retained `resolved_after.json`,
- `before_vs_after.wav` — derived listening convenience; canonical `before.wav` and `after.wav` remain.

The candidate set is review authorization, **not deletion authorization**. L4 must separately prove references/tests/docs no longer require a candidate before removing it.

## Machine evidence

- `docs/INDEX.md` — human navigation by role.
- `docs/maintenance/L3_HISTORICAL_FIXTURE_CLASSIFICATION.json` — exhaustive per-file classification, size, digest, and candidate evidence.
- `tests/test_legacy_cleanup_l3.py` — guards exhaustiveness, candidate count/bytes, exact duplicate claims, package-mirror identity, and release-closed status.

The L3 inventory includes its own report/index surfaces so the earlier meta-classification omission cannot recur. The JSON manifest's own digest is intentionally `null` because a file cannot contain a stable hash of itself.

## Compatibility boundary

L3 does not modify runtime code. Existing L2 behavior remains authoritative:

```text
Analyzer → evidence
        ↓
Composer Agent
        ↓
explicit structured transition / revision
        ↓
deterministic engine
```

`code_composer.analysis.transition_material_analysis` remains live; its flat alias remains deprecated-but-supported through the v1.16 maintenance line.

## Verification

### Tests

- focused L3 classification guards: **9 / 9 PASS**
- cross-boundary L2/H5/reference/final-closure + L3 guards: **42 / 42 PASS**
- full regression: **244 / 244 PASS**
- coverage: **88%**
- `compileall`: **PASS**

### Runtime graph

L3 changes no runtime Python module or schema. A byte-level comparison against the uploaded L2 package found **0 changes under `src/` and `schemas/`**. The L2 runtime graph remains:

```text
import sweep modules   98
static modules         99
static edges          121
cycles                  0
import failures         0
```

### v1.16 final dogfood rerender

All three canonical `music_ir_after.json` files were rendered again under L3:

- A lyrical piano: `93aa85955b7aa8715b65721bc6388310be87006666cb9d7241889d66993116ba`
- B rhythm-centered: `7d18321f4986c324b75e2ae45e88cc061e8409dcaa16ae0b051bf4998b368377`
- C sparse chamber/electronic: `db524b79b30fbd3d79fa97b157ddb83bb84c71d71cbf09d7c48c391aa3a3834f`

Each hash is byte-identical to the closed v1.16 evidence; all rerenders have clipped frame ratio `0.0`.

### Legacy representative WAV

`examples/basic/demo_ir.json` was rendered again and remains byte-identical to the established v1.15 compatibility WAV baseline:

`589ac3efdc466a1a7c191caa0e614a63b1a28e4dea566b08164df3730f4490e0`

The L2 recorded Composer Plan / Music IR baseline hashes remain untouched; L3 does not mutate runtime or compatibility fixture payloads.

## Next

**L4 — Dead Test / Reference Cleanup**

L4 may review only the 12 files explicitly marked `L4_CANDIDATE` by this closure unless L3 is formally reopened with new evidence.
