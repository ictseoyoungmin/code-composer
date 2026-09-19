# S6 — Continuous Bowed-String State & Bow-Change Transients — CLOSED

Date: 2026-09-17

## Closure

S6 adds stateful whole-track rendering to the instrument-engine boundary and a new `bowed.violin.modeled_continuous@1.0.0` factory preset. The previous `modeled_open` preset remains note-reset and unchanged in purpose.

The violin planner now accepts both `bowed_string` and `bowed_waveguide` violin-family patches. Its left-hand/bow realization is not rewritten by the renderer.

## Validation

- focused S5/S6/violin tests: **22 / 22 PASS**
- full source regression: **354 / 354 PASS**
- clean-installed full regression: **354 / 354 PASS**
- bowed-waveguide focused coverage: **93%**
- standalone self-check: **PASS**
- isolated skill validation / compileall: **PASS**
- import sweep: **124 modules / 0 failures**
- static graph: **124 modules / 180 internal import edges / 0 cycles**
- clean wheel: **PASS**
- legacy v1.16 A/B/C WAV identity: **PASS / byte-identical**

Full-suite coverage instrumentation was intentionally not used as a closure blocker in S6 because tracing the Python per-sample physical-model loops expands runtime dramatically; the changed bowed-waveguide module was measured directly at 93% while the full functional suite was executed normally both from source and a clean install.

## Audio evidence

Repository-only validation includes:

- S5 note-reset phrase;
- S6 continuous phrase with the same musical material;
- S5→S6 A/B phrase;
- isolated repeated-note bow-change comparison;
- realized bow/fingering JSON and transition metrics.

These audio files are validation artifacts and are not bundled in the installed Skill.
