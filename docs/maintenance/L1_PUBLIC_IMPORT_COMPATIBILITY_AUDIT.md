# Legacy Cleanup L1 — Public Import / Compatibility Audit

Status: **CLOSED**

v1.16.0 remains **CLOSED**. L1 makes compatibility decisions; actual deletions begin in L2.

## Decision policy

The repository already states:

> Root `src/code_composer/*.py` paths are explicit v1 compatibility shims.

and:

> Historical flat imports that still represent the current architecture may remain as explicit symbol shims. Removed architectural paths are not retained merely for import compatibility.

Therefore cleanup uses two different rules:

```text
flat alias to a live/current domain
→ DEPRECATE, but do not break during 1.16.x maintenance

legacy behavior that conflicts with current architecture
→ REMOVE as a superseded architectural path
```

## Decisions

### KEEP_CANONICAL — 2

- `code_composer.render`
- `code_composer.validation_contracts`

### KEEP_COMPAT_V1 — 1

- `code_composer.resolve`

`resolve` is explicitly named as a retained compatibility shim in current README, STRUCTURE and ARCHITECTURE. It stays for the v1 compatibility line.

### DEPRECATE_FLAT_IMPORT — 30

These root imports remain available in v1.16.x, but current source/tests should migrate to their nested domain paths. They are candidates for removal only at a future compatibility-breaking release.

- `code_composer.arrange` → `code_composer.composition.arrange`
- `code_composer.arrangement_analysis` → `code_composer.analysis.arrangement_analysis`
- `code_composer.automation` → `code_composer.mix.automation`
- `code_composer.bass_analysis` → `code_composer.analysis.bass_analysis`
- `code_composer.cli` → `code_composer.app.cli`
- `code_composer.composer_cli` → `code_composer.app.composer_cli`
- `code_composer.composer_planner` → `code_composer.agent.composer_planner`
- `code_composer.drum_analysis` → `code_composer.analysis.drum_analysis`
- `code_composer.dsp` → `code_composer.audio.dsp`
- `code_composer.form_development_analysis` → `code_composer.analysis.form_development_analysis`
- `code_composer.harmonic_analysis` → `code_composer.analysis.harmonic_analysis`
- `code_composer.instrument` → `code_composer.audio.instrument`
- `code_composer.instrument_analysis` → `code_composer.analysis.instrument_analysis`
- `code_composer.ir` → `code_composer.pipeline.validation`
- `code_composer.mixer` → `code_composer.mix.mixer`
- `code_composer.orchestration_analysis` → `code_composer.analysis.orchestration_analysis`
- `code_composer.percussion` → `code_composer.audio.percussion`
- `code_composer.phrase` → `code_composer.composition.phrase`
- `code_composer.phrase_analysis` → `code_composer.analysis.phrase_analysis`
- `code_composer.piano_design` → `code_composer.audio.piano_design`
- `code_composer.rhythm` → `code_composer.composition.rhythm`
- `code_composer.rhythm_analysis` → `code_composer.analysis.rhythm_analysis`
- `code_composer.section_analysis` → `code_composer.analysis.section_analysis`
- `code_composer.sound_palette_analysis` → `code_composer.analysis.sound_palette_analysis`
- `code_composer.synth` → `code_composer.audio.synth`
- `code_composer.theory` → `code_composer.core.theory`
- `code_composer.timbre_analysis` → `code_composer.analysis.timbre_analysis`
- `code_composer.topline` → `code_composer.composition.topline`
- `code_composer.topline_analysis` → `code_composer.analysis.topline_analysis`
- `code_composer.topline_grammar_analysis` → `code_composer.analysis.topline_grammar_analysis`

No deprecation warning is injected into runtime imports in this maintenance cycle because warning side effects would alter a previously closed public behavior surface. The deprecation is architectural/documentary.

### REMOVE_IN_L2 — flat surfaces

- `code_composer.pre_hook_build`
- `code_composer.section_calibration`
- `code_composer.transition_automation`
- `code_composer.transition_material`
- `code_composer.transition_material_analysis`

These are not ordinary aliases. They belong to superseded analyzer-driven mutation semantics.

## Superseded semantic stacks

### Legacy transition material

`composition.transition_material.generate_transition_material()` consumes measured transition discontinuity and automatically invents:
- pad tails,
- drum pickups,
- bass anticipations,
- topline pickups.

`composition.arrange` still conditionally activates this path when `transition_analysis` is present.

This conflicts with v1.16 E5:

```text
Composer Agent authors explicit Musical Transition
→ deterministic engine realizes it
```

Decision: **REMOVE_IN_L2**.

### Legacy pre-hook build

`composition.pre_hook_build.add_pre_hook_build_material()` consumes analysis evidence and automatically creates withdrawal, drum pickup, pad swell and melodic pickup material.

Decision: **REMOVE_IN_L2**.

### Legacy transition automation

`mix.transition_automation.build_adaptive_transition_automation()` converts measured before/after RMS and direction directly into master-gain automation.

This is analyzer-driven automatic revision.

Decision: **REMOVE_IN_L2**.

### Legacy section calibration

`composition.section_calibration` converts measured-vs-expected section energy into arrangement `section_gain`.

This is another analysis→automatic mutation path, while v1.16 requires Agent-authored structured revision.

Decision: **REMOVE_IN_L2**.

### Legacy transition-material analyzer

`analysis.transition_material_analysis` only analyzes provenance from the superseded transition-material path.

Decision: **REMOVE_IN_L2** together with that stack.

## L2 migration scope

L2 will:

1. remove the five root legacy surfaces above,
2. remove their nested superseded modules,
3. remove `transition_analysis / pre_hook_build / pre_hook_analysis` execution branches from `composition.arrange`,
4. retire or rewrite tests that exist only for those legacy semantics,
5. migrate surviving tests away from unrelated flat shims to canonical nested imports where practical,
6. verify legacy v1.15 baseline Plan / Music IR / WAV and v1.16 Final Closure dogfoods remain unchanged,
7. keep `code_composer.resolve` intact.

## Compatibility boundary

L1 does **not** authorize removal of generic flat imports such as:

```text
code_composer.theory
code_composer.instrument
code_composer.phrase
code_composer.arrange
code_composer.mixer
...
```

They are deprecated, not L2 deletion targets.

## Next

**L2 — Proven-unused / Superseded Legacy Removal**


## L2 amendment

L2 found evidence that the original L1 classification of `analysis.transition_material_analysis` was too aggressive.

Canonical E5 also writes `transition_material` provenance tags such as:
- `pickup`
- `harmonic_anticipation`
- `bass_approach`
- `rhythm_fill`

Therefore:
- `code_composer.analysis.transition_material_analysis` → **KEEP**
- `code_composer.transition_material_analysis` → **DEPRECATE_FLAT_IMPORT**
- it is **not** an L2 deletion target.

This amendment follows the cleanup rule that an upstream decision is reopened when new architectural evidence invalidates its assumption.
