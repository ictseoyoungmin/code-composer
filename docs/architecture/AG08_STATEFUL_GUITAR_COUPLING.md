# AG08 — Stateful Guitar Coupling / Continuous Performance

Status: **S1 IMPLEMENTATION CANDIDATE**

Target release: **v1.19.0**

Dependency: AG01–AG07 CANONICAL CLOSED.

Canonical upstream:
- main: `ac57c23e8d01607887a18952798014de3da3d420`
- AG01 tone identity
- AG02 string/fret authority
- AG03 right-hand excitation
- AG04 left-hand articulation
- AG05 multi-string/arpeggio authority
- AG06 strum gesture
- AG07 same-guitar percussion

## Goal

Turn the accepted acoustic-guitar event models into one continuously evolving
six-string + bridge/body instrument state without changing Composer authority.

AG08 is a reduced-order physical state model, not a full finite-element runtime.

## Physical state contract

The planned state can be written abstractly as

```
x[t+1] = A x[t] + B u[t]
y[t]   = C x[t]
```

where:
- `x` contains persistent string / bridge / body state;
- `u` is newly authored AG03–AG07 excitation/contact energy;
- passive coupling redistributes energy but does not create it;
- no-input state must decay;
- hidden sympathetic state is not a new authored MIDI note.

The project-owned S1 state contains:
- six string energy proxies;
- six string phase proxies;
- compact bridge state;
- compact body state;
- active-fret state;
- sample position.

These variables are intentionally generic and are not a measured guitar response.

## S1 — State skeleton / sample-exact bypass

S1 introduces:
- `AcousticGuitarState`;
- deterministic zero-energy state initialization;
- state energy diagnostic;
- stateful whole-track engine entrypoint;
- opt-in factory preset `acoustic_guitar.steel_stateful@1.0.0`;
- bounded `stateful_coupling` configuration.

S1 deliberately keeps all coupling/memory gains at zero:
- same_string_memory = 0
- bridge_memory = 0
- cross_string_coupling = 0
- sympathetic_gain = 0
- action_body_memory = 0

### Strict preservation invariant

When all AG08 coupling gains are zero, the whole-track entrypoint returns the
pre-AG08 event renderer path directly. **No arithmetic is inserted into audio.**

Therefore the candidate must be sample-exact against AG07 for:
- isolated note;
- real F chord strum;
- note + AG07 percussive actions.

Non-zero coupling is a hard `NotImplementedError` in S1 so incomplete state
physics cannot silently enter production.

## Planned downstream slices

- **S2 Same-string continuity:** reuse residual same-string state across sequential events.
- **S3 Shared bridge/body memory:** notes and AG07 actions excite one persistent body state.
- **S4 Sympathetic cross-string coupling:** bounded bridge-mediated energy transfer.
- **S5 Technique-transition continuity:** arpeggio→strum→mute→slap→fingerstyle etc.
- **S6 Passive energy/stability barrier:** no-input decay, finite impulse energy, no runaway feedback or body drone.
- **S7 Listening closure:** A/B against AG07 isolated-event canonical.

## Provenance

External research / OSS consulted for AG07/AG08 is recorded in `CREDITS.md`.
Current additional conceptual references include player/string collision research,
coupled-string waveguide research, hybrid modal-waveguide coupling, and University
of Edinburgh NESS architecture.

No external code, solver, mesh, measured response, body-mode table, fitted
parameter set, recording, IR, or dataset is copied into S1.

Any later AG08 slice that adopts an additional external algorithm or asset beyond
conceptual comparison must update `CREDITS.md` before canonical closure.

## S1 closure gate

1. baseline AG07 preset remains untouched;
2. stateful candidate is explicitly opt-in;
3. state initialization is deterministic and zero energy;
4. candidate advertises track-rendering capability;
5. zero coupling delegates to the exact AG07 render path;
6. isolated note A/B is sample-exact;
7. F strum A/B is sample-exact;
8. note + AG07 action A/B is sample-exact;
9. nonzero coupling is blocked in S1;
10. state configuration is bounded and validated;
11. AG01–AG07 preservation evidence and full CI pass.
