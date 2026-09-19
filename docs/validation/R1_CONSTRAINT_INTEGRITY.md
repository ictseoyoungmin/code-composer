# R1 — Constraint Integrity

Status: CLOSED  
Version: 1.15.1

## Contract

`hard_constraints` is a core execution contract, not advisory metadata.

Supported keys:

- `bpm`
- `root`
- `scale`
- `forbidden_roles`

Supported forbidden roles:

- `lead`
- `topline`
- `pad`
- `bass`
- `drums`
- `arp`

Unknown keys, malformed role arrays, duplicate role entries, and unknown roles fail validation.
The same contract is used by Agent Brief validation and direct Music IR validation through `code_composer.core.constraints`.

## Execution invariant

A forbidden role keeps its track object so the mix graph remains stable, but its resolved event list is empty.

Constraint gates exist at three relevant boundaries:

1. after base arrangement, before cross-role topline reservation;
2. after transition/pre-build material, preventing reintroduction;
3. immediately before rendering, covering already-resolved direct IR that bypasses the arranger.

Therefore a valid forbidden role cannot reach the audio renderer.

## Regression evidence

Original v1.15 failure reproduction with one forbidden role at a time:

- pad: 35 events
- bass: 17 events
- drums: 18 events
- arp: 64 events

R1 result:

- pad: 0
- bass: 0
- drums: 0
- arp: 0
- lead: 0 when forbidden
- topline: 0 when forbidden

All six roles forbidden simultaneously, with forced transition and pre-build material:

- final event count for every role: 0
- rendered peak: 0.0
- mix track topology retained

A no-constraint fixture produces byte-identical resolved JSON before and after R1.

Regression tests were split because of the execution timeout boundary:

- constraint/composer group: 23 passed
- regression group A: 26 passed
- regression group B: 33 passed
- total: 82 / 82 passed
- import scan: 109 modules, 0 failures
