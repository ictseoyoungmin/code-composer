# v1.16 E0 — Contract Foundation

Status: CLOSED

## Added contracts

### ExpressiveScorePlan

Python model and validator:

`src/code_composer/agent/expressive_score_plan.py`

Validates:
- unique phrase IDs
- unique motif statement IDs
- section references
- role references
- source material / motif lineage references
- phrase containment inside section spans
- strictly ordered expression curves
- articulation / accent structure
- operation-specific motif-transform parameters
- register hard/preferred range invariants
- orchestration role-group conflicts and silence contracts
- phrase-gap decorative-role membership
- transition uniqueness and form adjacency

### PerformanceIR

Python model/compiler/validator:

`src/code_composer/agent/performance_ir.py`

E0 compilation copies authored expressive structure without creative mutation and adds only
deterministic realization bounds:

- seed
- microtiming maximum bound
- velocity-variation maximum bound
- quantization guard
- minimum note gap

No phrase contour is invented by the engine.

## Public schemas

- `schemas/expressive_score_plan.schema.json`
- `schemas/performance_ir.schema.json`

Both are packaged in the wheel under `code_composer/reference/schemas/`.

The Python validators remain authoritative for cross-reference and cross-field invariants.

## Reference fixture

`examples/v1.16/after_the_rain_expressive_score_plan.json`

The checked-in plan validates against both JSON Schema and Python contracts.

## Regression

- pytest: 126 / 126 PASS
- runtime Python modules: 106
- import edges: 112
- import cycles: 0
- runtime import failures: 0

## v1.15.6 behavior preservation

Existing canonical Composition Brief:

Plan SHA-256:
`f7f16714e9d98666ae29d27b0c183d89fdd14aa82de9d4d4869cdb45ef2ee302`

Music IR SHA-256:
`ef60c5f7388bddb0cd6eff857ee2dc937f3d819deb017a87a95d4146faa04b51`

Representative WAV SHA-256:
`589ac3efdc466a1a7c191caa0e614a63b1a28e4dea566b08164df3730f4490e0`

All are byte-identical between v1.15.6 and E0.

## Scope boundary

E0 does **not** alter note events.

The next slice, E1, is the first slice allowed to realize:
- phrase dynamic curves,
- phrase timing curves,
- note-length/gate curves,
- articulation,
- accents,
- breath/gap,
- bounded deterministic micro-variation.
