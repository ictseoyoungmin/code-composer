# S15 — Ensemble / Orchestration Realism

Status: **CLOSED**  
Date: 2026-09-19  
Engine: Code Composer v1.17.0

## Goal

Improve the realism of an already-authored arrangement when multiple roles perform together, without inventing new notes, rewriting orchestration, or applying random humanization.

S15 makes ensemble relationship an explicit Performance IR surface: the agent authors who leads, which roles sit slightly ahead/behind, which support roles yield during real overlap, and small role-level pan offsets. The runtime executes those instructions deterministically.

## Implemented interaction model

- Section-level `leader_role`.
- Authored per-role onset offsets bounded to **±30 ms**.
- Overlap-weighted support velocity yielding: support is reduced only by the fraction of a note that actually overlaps the leader.
- Song-level role pan offsets that add to, rather than replace, the existing mix graph pan.
- Multiple tracks sharing one `arrangement_role` receive the same ensemble interaction.
- Interaction realization is idempotent and leaves pre-S15 IR unchanged when the surface is absent or disabled.
- Existing orchestration budgets, register plans, note content, section form, and instrument-engine choices remain authoritative.

## QA integration

Explicit S15 dynamic yielding is visible to expressive QA. A role pair that is intentionally managed through authored overlap yielding is not blindly reported as unmanaged `ORCHESTRATION_MASKING` merely because the notes overlap.

This does not make the analyzer an arranger: QA reports evidence; the composing agent still authors the ensemble relationship.

## Dogfood — Blue Hour Ensemble Rehearsal

A 13-bar excerpt of **Blue Hour, Empty Platform** was re-realized at 24 kHz without changing note content.

- violin: **66 events**
- piano: **77 events**
- bass: **13 events**
- drums: **104 events**
- note-content identity: **true**
- clipping: control **0.0**, treatment **0.0**
- treatment/control mono waveform correlation: **0.71377**
- treatment difference RMS: **0.01418**

Section behavior:

- `spiccato_pulse`: piano +8 ms, bass +11 ms, drums −4 ms; 25 support events yielded.
- `long_rise`: piano +10 ms, bass +13 ms, drums −2 ms; 34 support events yielded.
- `harmonic_apex`: piano +6 ms, bass +9 ms, drums −3 ms; 31 support events yielded.

The treatment therefore changes inter-player realization while preserving the authored pitches, durations, section structure, and instrument content.

## Validation

- S15 focused: **15 / 15 PASS**
- source regression: **435 / 435 PASS** across 68 test files
- clean-installed wheel regression: **435 / 435 PASS** across 68 test files
- self-check: **PASS**
- isolated Skill validation: **PASS**
- compileall: **PASS**
- import sweep: **127 / 127**, 0 failures
- static graph: **127 modules / 185 edges / 0 cycles**
- public entrypoints: **9**

## Compatibility

- No S15 surface → pre-S15 IR remains unchanged.
- `ensemble_interaction.enabled=false` → no interaction mutation.
- No new factory preset is required; factory preset count remains 13 and violin preset count remains 8.
- S14 acoustic-piano release hardening remains the piano baseline.
- S13 violin articulation/physical-performance paths remain unchanged.

## Research provenance

S15 uses ensemble-performance literature only as a conceptual reference for role-dependent timing, leader/follower relationships, and interpersonal adaptation. The implementation is independent and does not copy research code, performance data, or recordings. See `CREDITS.md`.

## Next

Do not automatically open a new feature slice. First compose a full multi-role flagship with S14 piano + S13 violin + S15 ensemble interaction and identify the next audible bottleneck from listening evidence.
