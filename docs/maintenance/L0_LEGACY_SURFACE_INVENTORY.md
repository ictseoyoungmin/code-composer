# Legacy Cleanup L0 — Surface Inventory

Status: **CLOSED**

v1.16.0 remains **CLOSED**. L0 performs inventory only; it deletes no runtime/public surface.

## Root-level Python surface

Total root-level modules excluding `__init__`: **38**

- CANONICAL_RUNTIME: **2**
- COMPATIBILITY_SHIM_REFERENCED: **1**
- COMPATIBILITY_SHIM_REPO_BOUND: **22**
- REMOVE_CANDIDATE_UNREFERENCED_SHIM: **13**

### Canonical runtime

- `code_composer.render`
- `code_composer.validation_contracts`

### Repo-bound flat compatibility surfaces

These are still imported through root-level paths by current tests:

- `code_composer.arrange` → `code_composer.composition.arrange`
- `code_composer.arrangement_analysis` → `code_composer.analysis.arrangement_analysis`
- `code_composer.cli` → `code_composer.app.cli`
- `code_composer.drum_analysis` → `code_composer.analysis.drum_analysis`
- `code_composer.instrument` → `code_composer.audio.instrument`
- `code_composer.instrument_analysis` → `code_composer.analysis.instrument_analysis`
- `code_composer.ir` → `code_composer.pipeline.validation`
- `code_composer.mixer` → `code_composer.mix.mixer`
- `code_composer.percussion` → `code_composer.audio.percussion`
- `code_composer.phrase` → `code_composer.composition.phrase`
- `code_composer.phrase_analysis` → `code_composer.analysis.phrase_analysis`
- `code_composer.resolve` → `code_composer.composition.resolve`
- `code_composer.rhythm` → `code_composer.composition.rhythm`
- `code_composer.rhythm_analysis` → `code_composer.analysis.rhythm_analysis`
- `code_composer.section_analysis` → `code_composer.analysis.section_analysis`
- `code_composer.section_calibration` → `code_composer.composition.section_calibration`
- `code_composer.theory` → `code_composer.core.theory`
- `code_composer.timbre_analysis` → `code_composer.analysis.timbre_analysis`
- `code_composer.topline` → `code_composer.composition.topline`
- `code_composer.topline_analysis` → `code_composer.analysis.topline_analysis`
- `code_composer.transition_material` → `code_composer.composition.transition_material`
- `code_composer.transition_material_analysis` → `code_composer.analysis.transition_material_analysis`

L1 will distinguish “tests are legacy” from “public path is still promised”.

### Other referenced compatibility surfaces

- `code_composer.composer_cli` → `code_composer.app.composer_cli`

### Unreferenced removal candidates

These have no canonical internal inbound edge and no repository consumer in the v1.16.0 baseline. They remain candidates, not deletions, until L1 checks the installed/public compatibility contract.

- `code_composer.automation` → `code_composer.mix.automation`
- `code_composer.bass_analysis` → `code_composer.analysis.bass_analysis`
- `code_composer.composer_planner` → `code_composer.agent.composer_planner`
- `code_composer.dsp` → `code_composer.audio.dsp`
- `code_composer.form_development_analysis` → `code_composer.analysis.form_development_analysis`
- `code_composer.harmonic_analysis` → `code_composer.analysis.harmonic_analysis`
- `code_composer.orchestration_analysis` → `code_composer.analysis.orchestration_analysis`
- `code_composer.piano_design` → `code_composer.audio.piano_design`
- `code_composer.pre_hook_build` → `code_composer.composition.pre_hook_build`
- `code_composer.sound_palette_analysis` → `code_composer.analysis.sound_palette_analysis`
- `code_composer.synth` → `code_composer.audio.synth`
- `code_composer.topline_grammar_analysis` → `code_composer.analysis.topline_grammar_analysis`
- `code_composer.transition_automation` → `code_composer.mix.transition_automation`

### Noncanonical root surfaces requiring manual review

- none

## Documentation policy

Historical validation reports remain **HISTORICAL_EVIDENCE_KEEP**. Old version numbers inside those reports are provenance, not current-version drift.

## Example / fixture policy

- `examples/basic/` → **LEGACY_COMPATIBILITY_FIXTURE_LOCKED**
- `examples/v1.16/final_closure/` → **FINAL_CLOSURE_EVIDENCE_KEEP**
- `examples/v1.16/` current authoring examples → KEEP
- piano patch examples → current domain references

## Cleanup invariant

```text
old != removable

REMOVE only after:
  noncanonical
  + repo consumers migrated
  + public compatibility decision says REMOVE
  + no historical/evidence responsibility
  + clean install / compatibility gates remain green
```

## Next

**L1 — Public Import / Compatibility Audit**

Every flat surface receives one explicit decision:
`KEEP`, `DEPRECATE`, or `REMOVE`.

Actual code deletion starts in L2.
