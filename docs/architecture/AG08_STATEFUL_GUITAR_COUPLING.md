# AG08 — Stateful Guitar Coupling / Continuous Performance

Status: **S1-S3 ENGINEERING PASS · S4 NEXT**

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

S1 itself remains a strict zero-coupling preservation baseline. The later S2
candidate activates only `same_string_memory`; bridge/body memory, cross-string
coupling, sympathetic gain and action/body memory remain hard-blocked.

## S2 — Same-string residual continuity

S2 adds a second opt-in development preset:
- `acoustic_guitar.steel_stateful_continuity@1.0.0`
- `same_string_memory = 0.32`
- all shared-body / cross-string / sympathetic / action-memory gains remain zero.

The track renderer keeps one rendered buffer per resolved AG02 physical string.
When a later authored note re-attacks the same string:
1. the previous waveform is continuous at the new onset sample;
2. that already-existing residual is then exponentially damped with a bounded
   carry time derived from the S2 memory amount and measured residual RMS;
3. the accepted AG01-AG07 note renderer produces the new authored excitation;
4. no new oscillator, pitch, MIDI event, or hidden sympathetic note is created.

S2 deliberately delegates to AG07 unchanged when a track contains instrument
actions, explicit event pan, unresolved fingering, or simultaneous notes on the
same physical string. Those interactions belong to S3-S5.

### S2 closure gate

1. S1 zero-coupling preset and preservation evidence remain valid;
2. an isolated note is sample-exact with AG07;
3. a note moved to a different physical string is sample-exact with AG07;
4. repeated use of one physical string changes only after the re-attack boundary;
5. same-string output is deterministic and bounded;
6. authored/resolved event identity remains exact;
7. AG07 instrument-action tracks still delegate to canonical AG07;
8. bridge/body, cross-string, sympathetic and action-memory gains remain blocked;
9. AG01-AG07 preservation workflows and full CI pass.

## S3 — Shared bridge/body memory

S3 adds the opt-in development preset:
- `acoustic_guitar.steel_stateful_body@1.0.0`
- `same_string_memory = 0.32`
- `bridge_memory = 0.46`
- `action_body_memory = 0.52`
- cross-string coupling and sympathetic gain remain zero.

S3 does **not** add another body resonator. The actual accepted AG01/AG07
already-rendered residual waveform is the shared body state. New authored notes
and AG07 actions enter that same state. At a later excitation/contact boundary,
the prior residual is kept sample-continuous and receives only a bounded weak
loading curve; no new modal frequency, oscillator, sample, IR, or hidden pitch is
created.

AG07 action seeds are attached only to render-local event copies using the exact
legacy deterministic formula. Canonical Render IR remains unchanged.

S3 groups simultaneous events at one onset so a chord or note+slap does not
artificially load the body multiple times before its same-onset excitations are
added.

### S3 engineering gate

1. isolated note remains sample-exact with AG07;
2. isolated AG07 action remains sample-exact, including deterministic action identity;
3. simultaneous note + action with no prior body state remains sample-exact;
4. sequential note→action and action→note differ only after the second excitation;
5. a different-string second note may change the existing body residual but must not create a hidden string/note event;
6. repeated S3 render is deterministic and peak remains bounded;
7. authored/resolved events remain exact;
8. S1-S2 evidence and AG01-AG07 preservation remain green;
9. cross-string sympathetic coupling remains blocked until S4.

## Planned downstream slices

- **S2 Same-string continuity:** implementation candidate in this branch; close after the S2 engineering gate above.
- **S3 Shared bridge/body memory:** engineering PASS on `43c03e8a131ad1de6b0c5f2530f1e6b42d35ebca`; CI #245 and S3 evidence #8 SUCCESS.
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
9. S1 preset remains zero-coupling and sample-exact; non-S2 coupling remains blocked;
10. state configuration is bounded and validated;
11. AG01–AG07 preservation evidence and full CI pass.
