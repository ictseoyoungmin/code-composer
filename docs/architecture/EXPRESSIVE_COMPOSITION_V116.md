# v1.16 — Expressive Composition & Performance Grammar

Status: DESIGN OPEN

## Problem

v1.15.6 can:
- author structured harmony/form/orchestration,
- render deterministic piano and other instruments,
- analyze broad section energy and audio output.

It still under-specifies how a musical idea is *performed and developed*.

The missing layer is not another style preset system. It is an explicit expressive score layer authored by the Composer Agent.

## Canonical pipeline

```text
User intent
  ↓
Composer Agent
  ↓
Composition Brief
  ↓
Musical Narrative
  ↓
Expressive Score Plan
  ├─ motif development
  ├─ phrase expression
  ├─ register / voicing
  ├─ orchestration budget
  └─ musical transitions
  ↓
Performance IR
  ↓
Music IR events
  ↓
Deterministic renderer
  ↓
Expressive + acoustic QA
  ↓
Agent revises the structured plan
```

## Responsibility boundary

### Composer Agent owns

- phrase shape and expressive intent,
- motif identity and transformations,
- where tension grows/releases,
- register and voicing intent,
- role priority and orchestration density,
- transition strategy,
- articulation intent,
- local timing/velocity curves,
- what should remain silent.

### Deterministic engine owns

- validating the plan,
- expanding transformations into notes/events,
- deterministic microtiming realization,
- deterministic velocity realization,
- note-length/articulation realization,
- range enforcement,
- voice allocation,
- collision measurement,
- rendering and analysis.

The engine must not infer "beautiful", "warm", "emotional", "cinematic" or similar words into fixed numeric values.

---

# E1 — Phrase Expression

A phrase is a musical unit with internal shape.

```text
PhraseExpression
├─ phrase_id
├─ role
├─ source_material
├─ start_beat / duration_beats
├─ dynamic_curve
├─ timing_curve
├─ articulation_curve
├─ gate_curve
├─ accent_points
├─ apex
├─ instrument_expression_curves (optional; S11)
└─ breath_after
```

## Curves

Curves are explicit normalized control points.

Example:

```json
{
  "dynamic_curve": [[0.0,0.58],[0.55,0.82],[1.0,0.52]],
  "timing_curve_ms": [[0.0,0.0],[0.75,4.0],[1.0,9.0]]
}
```

The engine interpolates; it does not decide the musical shape.

S11 optionally extends the same phrase with instrument-expression curves such as bow pressure/speed/contact position and vibrato depth/rate/onset. These curves are explicit authoring instructions and are interpolated at note onsets. Event-local expression wins when both surfaces author the same control. With the optional field absent, pre-S11 realization is unchanged.

## Deterministic micro-variation

Small variation may be added only inside Agent-authored bounds:

```text
resolved timing
= phrase timing curve
+ metric placement
+ deterministic bounded micro-variation
```

Randomness is never the phrase model itself.

---

# E2 — Motif Development

A motif has identity and explicit transformation lineage.

```text
MotifStatement
├─ statement_id
├─ source_motif_id
├─ section_id
├─ transform_chain
├─ cadence_rule
└─ identity_weight
```

Initial transform vocabulary is structural, not stylistic:

- `exact`
- `fragment`
- `sequence`
- `transpose`
- `register_shift`
- `rhythm_scale`
- `rhythm_rewrite`
- `inversion`
- `retrograde`
- `cadence_rewrite`
- `ornament`
- `call`
- `response`

A transform must serialize its parameters.

Example:

```json
{
  "op":"fragment",
  "start":0,
  "length":4
}
```

No transform may be selected automatically from natural-language keywords.

---

# E3 — Register & Voicing

Each role can define soft and hard range constraints.

```text
RegisterPlan
├─ hard_range
├─ preferred_range
├─ center
├─ max_span
├─ min_intervoice_distance
├─ overlap_policy
└─ motion_policy
```

## Collision model

A collision is measured from simultaneous events:

```text
collision score
= pitch-range overlap
× shared duration
× sustain factor
× role-weight
```

The analyzer reports collisions; the Composer Agent decides how to fix them.

No universal fixed range such as "bass must be C1-C2" is canonical.

---

# E4 — Orchestration Budget

The section plan explicitly separates role importance.

```text
SectionOrchestration
├─ primary_roles
├─ secondary_roles
├─ decorative_roles
├─ max_simultaneous_roles
├─ allowed_overlaps
├─ phrase_gap_only_roles
└─ silence_roles
```

The purpose is to prevent "development = add more layers".

Decorative roles can be restricted to phrase gaps or transitions.

---

# E5 — Musical Transitions

Transitions become compositional objects.

```text
TransitionPlan
├─ from_section
├─ to_section
├─ harmonic_anticipation
├─ pickup
├─ bass_approach
├─ cadence_extension
├─ texture_subtraction
├─ silence_beats
├─ register_preparation
└─ rhythm_fill
```

Existing entry-gain / soften / fill controls remain lower-level execution controls, not the entire transition model.

---

# E6 — Expressive QA

New analyzers:

1. `MECHANICAL_TIMING`
   - repeated identical timing deltas over a phrase.

2. `FLAT_DYNAMICS`
   - velocity/dynamic curve lacks intended motion.

3. `MOTIF_IDENTITY_LOSS`
   - transformed statement diverges beyond Agent-authored identity threshold.

4. `REGISTER_COLLISION`
   - sustained overlapping roles in the same register.

5. `ORCHESTRATION_MASKING`
   - too many simultaneously active subordinate roles around a primary role.

6. `TRANSITION_DISCONTINUITY`
   - abrupt density/register/harmony jump not explained by TransitionPlan.

7. `PHRASE_NO_BREATH`
   - phrase groups contain no intended gap or release where the plan requires one.

These are measurements, not creative decisions.

---

# Performance IR

Performance IR is the execution bridge between compositional intent and note events.

```text
PerformanceIR
├─ phrases[]
├─ motif_statements[]
├─ register_plans{}
├─ orchestration_sections{}
├─ transitions[]
└─ realization
```

`realization` contains deterministic engine policy only:

```json
{
  "seed": 260916,
  "microtiming": {
    "enabled": true,
    "max_abs_ms": 12.0
  },
  "velocity_variation": {
    "enabled": true,
    "max_abs": 0.025
  }
}
```

Bounds exist to realize an authored phrase naturally; they do not author the phrase.

---

# Backward compatibility

If no Expressive Score Plan exists:
- v1.15.6 Composition Brief behavior remains available.
- Existing Music IR remains renderable.
- Existing performance/event fields remain readable.

v1.16 should add a new canonical path without invalidating legacy deterministic inputs.

---

# Closure criteria

v1.16 cannot be CLOSED merely because unit tests pass.

Required dogfood:

1. one piano-centered lyrical piece,
2. one rhythm-centered piece,
3. one sparse chamber/electronic piece.

For each:
- Agent authors motif lineage,
- phrase curves are visible in serialized plan,
- register plan is explicit,
- section orchestration budget is explicit,
- at least two transitions are musical transitions rather than gain fades,
- expressive QA reports are inspected,
- Agent performs at least one structured revision,
- final render is 44.1 kHz minimum.

The primary quality test is whether the same motif is perceived as intentionally developed rather than copied or randomly mutated.


## E1 implementation checkpoint

E1 realizes PhraseExpression after arrangement/resolution and before audio synthesis.

Event provenance records:
- `base_start_beat`
- `base_duration_beats`
- `base_velocity`
- `dynamic_target`
- `authored_timing_ms`
- `microtiming_ms`
- `timing_offset_ms`
- `gate_curve`
- `gate_multiplier`
- `articulation`
- `accent_amount`

`breath_after_beats` removes same-role events in the authored post-phrase silence window.
Overlapping phrase envelopes/breath windows on one role are rejected during validation.


## E3 implementation checkpoint

Execution order is now:

```text
Motif Development
→ Register / Voicing Allocation
→ Phrase Expression
→ Renderer
```

Register allocation may change only octave-equivalent placement. It may not change pitch class to satisfy a range. If no octave-equivalent candidate satisfies the hard plan, execution fails.

Semantics:
- `hard_range`: mandatory MIDI boundary.
- `preferred_range`: soft optimization target.
- `center`: secondary gravity point.
- `max_span`: simultaneous voicing span, not whole-phrase melodic range.
- `min_intervoice_distance`: minimum simultaneous note spacing.
- `motion_policy`: deterministic octave-allocation objective.
- `overlap_policy`: retained as Agent-authored intent and exposed in collision evidence; E3 does not silently rewrite another role to enforce it.

A contour guard penalizes octave choices that reverse an upstream melodic/voice-leading direction when a contour-preserving candidate exists.

Register Collision Analyzer measures:

```text
time overlap × within-octave pitch proximity × authored role importance
```

This score is evidence for Agent revision rather than an automatic creative decision.


## E4 implementation checkpoint

Orchestration budget execution happens after arrangement, generated transition/build material, motif development, and register/voicing, but before E1 phrase expression.

Semantics:
- `silence_roles` is a hard gate. A prior sustain is truncated at the boundary of a section where that role becomes silent.
- `phrase_gap_only_roles` may sound only outside authored primary phrase bodies.
- `max_simultaneous_roles` counts unique sounding roles, not note count. Chords therefore count as one role.
- priority during arbitration is `primary > secondary > decorative`.
- `allowed_overlaps` protects explicitly intended role pairs when otherwise-equal choices compete for the budget. It is not a blanket prohibition on every unlisted pair.

The engine chooses no role importance itself; all importance classes and budgets are Agent-authored.


## E5 implementation checkpoint

E5 strengthens the transition contract so the engine does not invent missing material.

- harmonic anticipation requires role, scale-degree chord intervals, velocity and gate plus exactly one target source: legacy explicit `target_degree` or S31 `arrival_binding={source: destination_progression, progression_index: N}`
- pickup requires role, explicit degrees/rhythm/octave/velocity
- bass approach requires an authored operation type and, when relevant, direction/step count
- cadence extension names the affected roles and maximum extension
- texture subtraction names roles and a pre-boundary window
- register preparation names semitone shift and destination window per role
- rhythm fill contains explicit drum events relative to the section boundary

Existing material is subtracted/silenced first; explicitly authored transition material is then placed into the gap. Register/voicing and orchestration constraints run afterward.


## E6 implementation checkpoint

`analysis/expressive_qa.py` is evidence-only. It reads resolved Music IR and the existing section/audio analysis report; it never mutates a phrase, motif, register plan, orchestration budget or transition.

Integrated pipeline:

```text
render
→ section/audio analysis
→ register collision evidence
→ expressive QA
→ issue report
→ Composer Agent critique
→ revised Expressive Score Plan
→ recompile
```

The pipeline appends expressive QA issues to the normal analysis surface with `source="expressive_qa"`.

E6 slice closure uses three category dogfoods with explicit before/after structured plans. Full v1.16 release closure remains stricter and is intentionally not declared by E6 alone.


## v1.16 final integrated closure

The architecture is closed only after integrated composition evidence, not merely per-slice unit tests.

Canonical final evidence:

```text
structured base IR
→ Agent-authored Expressive Score Plan
→ Performance IR
→ E2 motif development
→ E5 musical transitions
→ E3 register/voicing
→ E4 orchestration budget
→ E1 phrase performance
→ deterministic render
→ E6 evidence
→ Agent-authored structured revision
→ rerender
```

The three checked-in final dogfoods each execute this full chain and pass the closure manifest.
