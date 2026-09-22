# Code Composer slices

## CLOSED — S0 Canonical IR
## CLOSED — S1 Deterministic render
## CLOSED — S2 Theory kernel
## CLOSED — S3 Phrase composer
## CLOSED — S4 Section arranger
## CLOSED — S5 Rhythm engine
## CLOSED — S6 Instrument engine
## CLOSED — S7 Mix graph
## CLOSED — S8 Analysis
## CLOSED — S9 Revision loop

## SUPERSEDED — historical S10 keyword intent surface

The early deterministic Korean/English keyword parser was removed in v1.15.3 R3.
Its approach was superseded by the Agent-authored Composition Brief architecture.

It is not a canonical runtime path.

## CLOSED — Composer Agent boundary

Canonical architecture:

```text
User prompt
→ external Composer Agent
→ explicit CompositionBrief
→ validation
→ deterministic ComposerPlan / Music IR compiler
```

Closure properties:
- Code Composer runtime contains no keyword/alias natural-language intent parser.
- Agent-authored musical decisions are explicit structured data.
- hard constraints are machine-validated and execution-enforced.
- direct Music IR and Brief-generated Music IR share validation contracts.
- renderer remains deterministic.


## CLOSED — v1.15 hardening R1–R4

- R1 Constraint Integrity — hard forbidden roles enforced at the final event graph.
- R2 Validation Closure — schema/parameter errors fail at validation boundaries.
- R3 Canonical Surface Cleanup — one Agent-authored Composition Brief architecture.
- R4 Reference Hygiene — executable examples, synchronized schemas, packaged references.


## CLOSED — v1.17 M1 MIDI Collaboration Export

Resolved/performance IR can be exported as deterministic SMF Type 1 plus reference WAV/resolved IR collaboration bundle. This is the external interchange/delivery surface.

## CLOSED — v1.17 M2 Code Composer Exchange Package

Code Composer users can exchange lossless `.ccx` checkpoints containing canonical Music IR, exact resolved/reference state, revision provenance, handoff intent, and scope locks. Imports are clean fast-forward only; dirty workspaces and divergent siblings are rejected rather than overwritten or auto-merged.

## CLOSED — v1.17 M3 External Delivery Hardening

External delivery now exports the authoritative reference mix, deterministic full-song and per-track MIDI, time-aligned 32-bit float track stems, exact resolved IR, machine-readable manifest, and human delivery notes. The adapter exports controller/tempo data only where canonical state represents it; it does not invent tempo maps, CC lanes, pitch bend, or additive stem reconstruction across shared nonlinear mix processing.

The planned v1.17 M1–M3 collaboration/delivery chain is complete. Further work should open a new slice rather than extending M3 implicitly.


## CLOSED — v1.17 S5 Bowed-String Sound Hardening

Causal sustained bowed-waveguide note rendering and `modeled_open` preset.

## CLOSED — v1.17 S6 Continuous Bowed-String State & Bow-Change Transients

Same-string waveguide state persists across realized notes and planned bow direction changes are rendered as finite velocity reversals. Double-stop continuous state and physical string-crossing overlap remain future slices.


## CLOSED — v1.17 S29 Thematic Arc / Cross-Section Motif Lineage

Composer Agent-authored cross-section motif variants with deterministic identity measurement, explicit section routing, and lineage evidence. The engine does not generate or auto-select variants.

Engineering gate: **96 test files / 644/644 PASS**, distribution/build validation PASS.

Perceptual gate: `Threadline at First Light` controlled full-song A/B — USER PASS / CLOSED 2026-09-22. Merged to GitHub `main` via PR #9; post-merge CI #40 SUCCESS.


## CLOSED — v1.17 S30 Harmonic Narrative / Section Progression Lineage

Composer Agent-authored section progression variants with deterministic reference validation, shared pad/bass/arp routing, local section indexing, and progression-lineage evidence. The engine does not generate or auto-select progressions.

Engineering gate: **97 test files / 651/651 PASS**, distribution/build validation PASS.

Perceptual gate: `Threadline at First Light` RMS-matched S29 baseline vs S30 harmonic treatment — USER PASS / CLOSED 2026-09-23.

## CLOSED — v1.17 S31 Destination-Bound Transition / Boundary Arrival Lineage

Performance IR may bind an explicitly authored E5 harmonic anticipation to a specific index of the destination section's explicit S30 progression variant. The runtime validates and resolves only that authored pointer; it does not infer or generate cadential harmony. Legacy explicit `target_degree` remains supported.

Engineering gate: **98 test files / 659/659 PASS**; focused S31+E5+S30+S29+S15+S27-M R2 **52/52 PASS**; distribution/build validation PASS.

Perceptual gate: `Threadline at First Light` S30 baseline vs destination-bound transition A/B — USER PASS / CLOSED 2026-09-23.

## Canonical status normalization after S31

There is **no pre-reserved implementation slice after S31**. The next slice must be selected from fresh full-song production evidence.

Older S27-L/S28 status labels are historical checkpoint facts, not active gates:

- S27-L was an engineering/listening checkpoint. Its active production gate was superseded by S27-M R2, which used the authenticated drum chain in full-song context and received USER PASS / CLOSED.
- S28-B/C/D are integrated parts of the accepted piano-naturalism chain; they are not active "reopenable" tasks.
- S28-F resolved to the canonical policy of **no automatic music-bus ducking**. Any later ducking is an explicit arrangement/mix decision.
- S28-G was accepted sufficiently to stop further treble-unison tuning and proceed.
- S28-H remains a historical piano-only closure checkpoint; its standalone listening gate is not retroactively relabeled PASS. Its accepted chain was carried into S27-M R2 and later S29-S31 full-song closures, so it is not an active gate.

Canonical S31 runtime closure commit: `1f820e682420e9e01ee31aadff024561c88f404d`, PR #11 merged, post-merge CI #44 SUCCESS. Later documentation-only commits do not change that runtime baseline.
