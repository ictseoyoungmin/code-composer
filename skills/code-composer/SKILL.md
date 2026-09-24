---
name: code-composer
description: Use for composing, revising, rendering, validating, exchanging, or delivering music with the deterministic Code Composer engine. Use when work should remain editable as canonical Music IR, when evidence-driven musical revision is needed, when two Code Composer users exchange lossless .ccx checkpoints, or when exporting MIDI/stems/reference audio for an external collaborator.
---

# Code Composer

Code Composer is an agent-directed, deterministic music composition and rendering system. The agent makes musical decisions from the user's brief and the current composition; the engine validates and realizes explicit structured instructions.

## Operating boundary

The user's explicit instructions take precedence over this skill.

Use this skill as an operational control surface, not as a source of musical taste. **Examples teach operation, never taste.** Never copy or treat bundled fixtures, note values, rhythms, chord choices, instrumentation, or test data as compositional references.

Analyzers produce evidence. They do not mutate music. The normal loop is:

`current state -> analysis/evidence -> agent decision -> explicit structured revision -> deterministic engine -> render -> compare`

## Start here

1. Read `kit/INDEX.md`.
2. Open only the workflow relevant to the user's request.
3. Open only the contracts/schemas required by that workflow.
4. Prefer documented commands and machine-readable surfaces over source inspection.
5. Do **not** inspect `kit/src/` by default.

Open `kit/src/` only when one of these exceptions applies:
- the user asks to change Code Composer itself;
- a stack trace points into implementation code;
- documented behavior conflicts with runtime behavior;
- a new engine capability must be implemented;
- the user explicitly requests internal algorithm review.

When source inspection is necessary, read `kit/SOURCE_MAP.md` first and inspect the narrowest relevant module.

## Workflow routing

- Composer-first Song contract validation: `kit/workflows/song-contract.md`
- Historical Music IR composition/render path: `kit/workflows/compose.md`
- Factory sound selection: `kit/workflows/select-preset.md`
- Human-playable violin realization: `kit/workflows/violin-performance.md`
- Measured violin bridge-admittance fitting: `kit/workflows/fit-bridge-admittance.md`
- Revision/hardening: `kit/workflows/revise.md`
- Rendering and QA: `kit/workflows/render-and-qa.md`
- Two Code Composer users exchanging work: `kit/workflows/exchange.md`
- MIDI-only/collaboration export: `kit/workflows/midi-export.md`
- External DAW/producer delivery: `kit/workflows/deliver.md`

## Authority rules

- CR01 Song is the canonical authored-state contract for the Composer-first rebuild.
- CR02 Execution Plan is the deterministic runtime-planning authority for Song timeline/material/instrument resolution. It does not invent note/voicing content.
- Canonical Music IR remains the historical render authority until the new execution path reaches audio rendering.
- Resolved IR is the exact deterministic realization state.
- Reference WAV is the timbre/mix authority for external collaborators.
- MIDI is an interchange representation, not a faithful representation of Code Composer synthesis/DSP.
- `.ccx` is the lossless Code Composer-to-Code Composer handoff format.
- External delivery is one-way; do not infer unsupported DAW edits back into canonical IR.

## Musical-content firewall

The installed skill intentionally excludes polished songs, polished MIDI, dogfood compositions, showcase WAVs, and stylistically meaningful completed examples. `kit/examples/` contains usage explanations only. `kit/fixtures/` contains tiny synthetic protocol fixtures only.

When composing or revising, derive musical choices from:
1. the user's current brief and constraints;
2. the current song's own material and provenance;
3. analysis of the current render/IR;
4. explicit theory/engineering constraints where relevant.

Do not derive them from bundled examples or tests. Factory presets are allowed sonic resources, but they provide **sound capability only**, never melodic/rhythmic/harmonic/arrangement content.

## Completion discipline

Before reporting completion, use the relevant workflow's validation gates. Preserve existing closed baselines unless the user explicitly opens them. For exchange/delivery tasks, verify hashes/manifests and inspect the produced package rather than assuming export success.
