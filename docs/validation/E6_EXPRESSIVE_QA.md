# v1.16 E6 — Expressive QA + Revision Loop

Status: CLOSED

## Analyzer contract

E6 implements seven evidence codes:

1. `MECHANICAL_TIMING`
2. `FLAT_DYNAMICS`
3. `MOTIF_IDENTITY_LOSS`
4. `REGISTER_COLLISION`
5. `ORCHESTRATION_MASKING`
6. `TRANSITION_DISCONTINUITY`
7. `PHRASE_NO_BREATH`

The analyzer is read-only. It does not alter Music IR or Expressive Score Plan.

## Revision loop

```text
render
→ analyze
→ evidence
→ Composer Agent critique
→ structured plan revision
→ recompile
→ rerender
```

`compare_expressive_qa()` compares before/after evidence only.

## Dogfood A — Lyrical piano

Target: timing and dynamics.

- targeted issues before: 2
- targeted issues after: 0
- resolved: 2
- sample rate: 44.1 kHz
- clipping: 0.0
- repeatable: True

The Agent revised phrase dynamic/timing/gate curves. Pitch material and synth remained unchanged.

## Dogfood B — Rhythm-centered transition

Target: transition discontinuity.

First render discontinuity: 1.0000.
First structured revision: 0.6060 (improved, but still above E6 threshold).
Second Agent-authored transition-plan revision: 0.5294.

- targeted issues before: 1
- targeted issues after: 0
- clipping: 0.0
- repeatable: True

No automatic rewrite occurred.

## Dogfood C — Sparse chamber/electronic

Targets: register collision and orchestration masking.

- targeted issues before: 4
- targeted issues after: 0
- resolved: 4
- clipping: 0.0
- repeatable: True

The Agent revised pad/arp register plans and restricted the arp to phrase gaps.

## Regression

- pytest: 182 / 182 PASS
- runtime modules: 113
- import edges: 132
- import cycles: 0
- import failures: 0

## Backward compatibility

Representative legacy/direct IR WAV remains byte-identical to E5:

`589ac3efdc466a1a7c191caa0e614a63b1a28e4dea566b08164df3730f4490e0`

E6 changes analysis output only when expressive performance context exists. It does not change audio rendering for unchanged Music IR.

## Scope boundary

E6 closes the implementation slice.

It does **not** by itself close the full v1.16 release. The architecture-level final closure still requires integrated multi-section dogfoods where each example also demonstrates motif lineage and at least two musical transitions.
