# Composer Agent Contract

> **PRE-REFACTOR AUTHORING CONTRACT.** This document records the v1.16/S29–S31 authoring model. CR00 explicitly replaces the mandatory detailed `CompositionBrief`, seed-IR coupling, and privileged six-role authoring surface. Its useful principles—Agent musical judgment, deterministic execution, explicit constraints, and analyzer non-mutation—remain inputs to CR01. See [CR00 Composer Rebuild Boundary](CR00_COMPOSER_REBUILD_BOUNDARY.md).

## Canonical boundary

Code Composer does **not** interpret free-form natural language with a vocabulary table.

```text
User prompt
  -> Composer Agent: musical reading / judgment
  -> Composition Brief: explicit musical decisions
  -> deterministic brief validator + compiler
  -> Music IR
  -> deterministic renderer / analyzer
  -> Agent critique
  -> revised Composition Brief or Music IR
```

The Composer Agent is responsible for musical judgment. The engine is responsible for execution, validation, reproducibility and analysis.

## What the Agent must decide

The brief contains concrete decisions rather than labels that the engine expands through hidden presets:

- BPM and meter
- root / scale
- section energy targets
- progression degrees and, when needed, explicit section progression variants
- motif intervals and motif rhythm
- kick/snare/hat groove cells
- swing / humanization / bass coupling
- foreground role per section
- harmonic colors
- development stages and density/register changes
- transition entry shaping / pre-fill
- hard constraints such as forbidden roles

The engine does not map `cinematic`, `dreamy`, `garage`, or similar words to fixed motifs or progressions. Such words may exist in the original prompt and concept description, but they carry no execution semantics by themselves.

## Hard-constraint rule

`hard_constraints` are validated against the concrete brief. A contradictory brief is rejected before Music IR mutation.

Examples:

- hard BPM 90 + transport BPM 96 -> reject
- `forbidden_roles=[topline]` + a section requesting topline -> reject
- unknown form section -> reject
- unsupported harmonic color -> reject

## Agent revision loop

Analyzer findings are evidence for the Agent, not an invitation for an opaque auto-composer to rewrite the piece. The Agent decides whether the correct upstream change is in the brief, arrangement, transition, timbre, or mix.


## Section harmonic narrative

When the form needs a goal-directed harmonic arc, progression variants are authored by the Composer Agent as explicit scale-degree sequences. The deterministic engine may route and validate those sequences, but it must not invent a progression because a section is named `chorus`, `bridge`, `final`, or because an analyzer reports low contrast.
