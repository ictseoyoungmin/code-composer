# Legacy Cleanup L2 — Superseded Analyzer-Driven Mutation Removal

Status: **CLOSED**

v1.16.0 remains **CLOSED**. L2 removes only the legacy mutation paths authorized by L1, with one evidence-driven correction.

## Removed implementation stacks

### 1. Legacy transition material generator

Removed:

- `code_composer.composition.transition_material`
- `code_composer.transition_material`

The removed generator consumed analyzer discontinuity measurements and automatically invented musical content such as pad tails, drum pickups, bass anticipation and topline pickups.

Canonical replacement:

```text
Composer Agent
→ explicit E5 Musical Transition
→ deterministic transition realization
```

### 2. Legacy pre-hook build generator

Removed:

- `code_composer.composition.pre_hook_build`
- `code_composer.pre_hook_build`

The old path consumed analysis evidence and automatically authored withdrawal, drum pickup, pad swell and melodic pickup material.

### 3. Adaptive transition automation

Removed:

- `code_composer.mix.transition_automation`
- `code_composer.transition_automation`

The old path converted measured transition RMS/direction directly into master gain automation.

Generic explicit automation remains intact at `code_composer.mix.automation`.

### 4. Section gain calibration

Removed:

- `code_composer.composition.section_calibration`
- `code_composer.section_calibration`

The old helper converted measured-vs-expected section energy into automatic arrangement gain changes.

Explicit authored `section_gain` execution remains available; only the analyzer→automatic-mutation helper was removed.

## Arrange runtime cleanup

Removed from `composition.arrange`:

```text
transition_analysis
→ generate_transition_material(...)

pre_hook_analysis / pre_hook_build
→ add_pre_hook_build_material(...)
```

The arranger no longer consumes analyzer output to invent composition material.

## Removed-field behavior

The following top-level IR controls are now explicitly rejected by aggregate/runtime validation instead of being silently ignored:

```text
transition_analysis
transition_material
pre_hook_build
pre_hook_analysis
```

Error guidance directs callers to author explicit v1.16 transition/performance state.

## L1 correction — transition provenance analyzer retained

During L2 we verified that canonical E5 itself emits event provenance:

```text
transition_material = pickup
transition_material = harmonic_anticipation
transition_material = bass_approach
transition_material = rhythm_fill
```

Therefore the original L1 assumption that `transition_material_analysis` was legacy-only was false.

Retained:

- `code_composer.analysis.transition_material_analysis`

Its flat alias:

- `code_composer.transition_material_analysis`

remains available but is classified **DEPRECATE_FLAT_IMPORT**, consistent with the rest of the v1 flat compatibility layer.

The retained analyzer successfully reads all four provenance types from the final rhythm-centered E5 dogfood.

## Test cleanup

Removed tests that only asserted superseded behavior:

- `test_transition_material.py`
- `test_pre_hook_build.py`
- `test_section_calibration.py`

`test_automation.py` remains and continues to test the generic explicit automation engine; only its adaptive analysis-driven automation section was removed.

The old hard-constraint test that injected legacy transition/pre-hook generators was removed. Canonical hard-constraint and E5/orchestration tests remain.

New L2 regression tests verify:

- all 8 removed module paths are unimportable,
- all 4 removed IR controls fail validation,
- `arrange.py` contains no analyzer→music generation branch,
- canonical E5 transition provenance analysis remains functional,
- the flat provenance-analyzer compatibility alias still works.

## Verification

### Tests

- focused L2 regression: **48 / 48 PASS**
- full regression: **235 / 235 PASS**
- coverage: **88%**
- compileall: **PASS**

### Graph

Before L2:

```text
import sweep modules  106
static modules        107
static edges          127
cycles                  0
```

After L2:

```text
import sweep modules   98
static modules         99
static edges          121
cycles                  0
import failures         0
```

Exactly 8 Python surfaces were removed: four superseded implementations plus four flat shims.

### Legacy baseline compatibility

The v1.15 compatibility baseline is unchanged:

- Composer Plan: `f7f16714e9d98666ae29d27b0c183d89fdd14aa82de9d4d4869cdb45ef2ee302`
- Music IR: `ef60c5f7388bddb0cd6eff857ee2dc937f3d819deb017a87a95d4146faa04b51`
- WAV: `589ac3efdc466a1a7c191caa0e614a63b1a28e4dea566b08164df3730f4490e0`

All match the pre-cleanup baseline byte-for-byte.

### v1.16 final closure compatibility

Re-rendering the three canonical final Music IRs under L2 produces the exact previously closed WAV hashes:

- A lyrical piano: `93aa85955b7aa8715b65721bc6388310be87006666cb9d7241889d66993116ba`
- B rhythm-centered: `7d18321f4986c324b75e2ae45e88cc061e8409dcaa16ae0b051bf4998b368377`
- C sparse chamber/electronic: `db524b79b30fbd3d79fa97b157ddb83bb84c71d71cbf09d7c48c391aa3a3834f`

All are byte-identical and have clipped sample ratio `0.0`.

## Compatibility boundary

L2 does **not** remove generic flat v1 imports. Those remain deprecated-but-supported during the v1.16 maintenance line.

`code_composer.resolve` remains explicitly compatibility-locked.

## Next

**L3 — Historical Documentation / Fixture Classification**

L3 will organize historical material without erasing evidence:
- current canonical docs,
- historical validation evidence,
- compatibility fixtures,
- current executable references,
- obsolete duplicated documentation candidates.
