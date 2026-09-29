# AG08 — Stateful Guitar Coupling / Continuous Performance

Status: **S1-S5 ENGINEERING PASS · S3 PERCEPTUAL PASS · S6 NEXT**

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

### S3 perceptual checkpoint — PASS

Human listening on 2026-09-30 accepted the curated 24 kHz A/B set:
- note → slap
- slap → note
- different-string note → note

No objection was raised for pumping, tail choking, new pitched resonance, or
artificial reverb-like swell. S3 is closed at both engineering and perceptual
checkpoint level.

## S4 — Passive sympathetic cross-string coupling

S4 adds a separate opt-in development preset:

- `acoustic_guitar.steel_stateful_sympathetic@1.0.0`
- `same_string_memory = 0.32`
- `bridge_memory = 0.46`
- `action_body_memory = 0.52`
- `cross_string_coupling = 0.20`
- `sympathetic_gain = 0.18`

S4 does not author, lower, or insert a MIDI / Render-IR note for sympathetic
response. An authored source note's accepted AG01-AG04 bridge-force signal drives
a compact target-string modal projection only when another physical string has
near-coincident partial frequencies.

The target-string resonant fundamental is the current compact fret state, or the
open-string tuning for an untouched string. Simultaneously authored strings at
one onset are excluded from sympathetic targets so a six-string chord is not
double-excited.

The transfer uses a bounded quadratic bridge-domain energy budget. If `eta_j`
is the energy fraction assigned to target string `j`, then:

```
sum(eta_j) <= min(0.12, cross_string_coupling * sympathetic_gain)
source_keep = sqrt(1 - sum(eta_j))
```

Thus the internal source/target allocation is non-amplifying before body
radiation. Compatible target state is radiated through the same accepted guitar
body path; no separate reverb, chorus, sample, impulse response, or foreground
sympathetic-note oscillator is introduced.

The S4 preset is intentionally generic. Standard steel-string tuning and
project-authored modal compatibility are used; no measured bridge admittance,
guitar geometry, material constants, fitted modal table, or named-instrument
response is imported.

### S4 engineering gate

1. S1-S3 preservation tests remain green.
2. The S4 preset is separately opt-in and leaves S3 unchanged.
3. A spectrally incompatible source/target case is sample-exact with S3.
4. A fully authored six-string same-onset chord is sample-exact with S3 and is
   not double-excited by hidden sympathetic state.
5. A compatible single-string source produces deterministic target-string state.
6. Authored Render-IR event identity and event count remain unchanged.
7. The summed target bridge-energy fraction never exceeds the configured passive
   budget or the absolute 0.12 S4 ceiling.
8. Output remains bounded at the 24 kHz evidence gate.
9. No new external implementation dependency or uncredited measured asset is
   introduced.
10. Full CI and AG01-AG08 preservation/evidence workflows pass.

### S4 engineering result — PASS

Authoritative S4 code checkpoint:

- `51b76943e63cd79e887553266c6240db8e436be7`
- CI **#255 — SUCCESS**
- Python 3.12: **894 passed**
- Python 3.10: **894 passed**
- checkout hygiene: **SUCCESS**
- AG01–AG07 and AG08 S1–S4 evidence workflows: **SUCCESS**

24 kHz S4 evidence:

- compatible E4: bridge-domain transfer fraction `0.036`
- compatible E4: S3→S4 delta RMS ratio `0.07659911267282411`
- compatible E4: target strings `[2, 3, 5, 6]`
- compatible E4: `source_keep^2 + transferred_energy = 1.0`
- compatible E4: deterministic / Render-IR event exact / one authored event
- compatible E4 peak: `0.16589707391533215`
- incompatible F4: **sample exact with S3**
- fully authored six-string same-onset chord: **sample exact with S3**

The first S4 preset draft used `cross_string_coupling = 0.22`, which correctly
failed the pre-existing engine contract `[0.0, 0.20]`. The candidate was
corrected to `0.20`; the engine bound was not widened. The authoritative S4
maximum configured bridge-domain transfer budget is therefore
`0.20 × 0.18 = 0.036`.

S4 is **ENGINEERING PASS**. Formal long-horizon no-input decay / passive
stability remains the dedicated S6 barrier, and final human listening remains S7.

## S5 — Technique-transition continuity

S5 adds the opt-in development preset:

- `acoustic_guitar.steel_stateful_performance@1.0.0`
- all S4 coupling values are retained;
- `technique_transition_memory = 0.82`.

S5 does not introduce a new note generator, hidden gesture, or separate
performance-effects bus. It extends the existing persistent six-string state in
two places.

### String-contact actions alter already-ringing string state

`muted_strum`, `dead_strum`, and `string_slap` now have a state consequence
in the S5 preset in addition to their already-accepted AG07 contact sound.

For muted/dead strums, physical-string contacts are scheduled deterministically
in traversal order. A down stroke contacts strings 6→1; an up stroke contacts
1→6. The requested traversal time is divided across those physical contacts.
At each contact, the already-existing string buffer remains continuous at the
contact sample and then undergoes a bounded decay toward a technique-dependent
retained-energy state.

A dead strum removes more residual string energy than a muted strum at otherwise
equal settings. `string_slap` applies simultaneous string-contact damping. Body
actions such as `top_slap` and `body_tap` do not arbitrarily reset individual
strings; they continue to interact through the S3 shared-body state.

### Same-string left-hand transitions preserve technique semantics

When a new authored event reuses the same physical string, S5 modifies only the
decay time of the already-existing residual waveform:

- slide / hammer-on / pull-off: longer residual carry;
- palm mute / fretting mute / dead note: shorter residual carry;
- ordinary re-attack: unchanged S4/S2 behavior.

The authored destination note, fret, AG04 realization, and injected excitation
remain unchanged. The transition layer therefore changes state continuity, not
musical authority.

### S5 preservation contract

- `technique_transition_memory = 0` is inert;
- S1-S4 presets remain unchanged;
- an isolated note with no technique transition must remain sample-exact with S4;
- no hidden MIDI, Render-IR note, or inferred hand gesture may be created;
- the reference performance chain is
  `arpeggio → strum → muted_strum → top_slap → fingerstyle`;
- candidate output must be deterministic, event-exact, bounded, and identical to
  S4 before the first technique-state transition;
- formal long-horizon passivity remains the dedicated S6 gate.

No new external algorithm, measured impedance, contact dataset, recording, IR,
solver, or code was introduced for S5. The already-recorded AG07/AG08
player-contact and coupled-string references remain the provenance basis.

### S5 engineering gate

1. S1-S4 preservation/evidence remains green.
2. S5 preset is separately opt-in.
3. isolated no-transition note is sample-exact with S4.
4. muted/dead traversal contact order is deterministic and physical-string ordered.
5. dead contact removes more existing residual state than muted contact.
6. legato left-hand transitions lengthen residual carry while mute/dead contact shortens it.
7. mixed arpeggio→strum→mute→slap→fingerstyle output is exact with S4 before the
   mute boundary and differs only after state-changing contact begins.
8. mixed performance remains deterministic and Render-IR event exact.
9. no hidden event is added and peak remains bounded.
10. full CI and AG01-AG08 evidence workflows pass.

### S5 engineering result — PASS

Authoritative S5 code checkpoint:

- `c517ab274ec76e57010529cdc1d7f0853ccd2471`
- CI **#265 — SUCCESS**
- Python 3.12: **901 passed**
- Python 3.10: **901 passed**
- checkout hygiene: **SUCCESS**
- AG01–AG07 and AG08 S1–S5 evidence workflows: **SUCCESS**

24 kHz S5 mixed-transition evidence:

- chain: `arpeggio → strum → muted_strum → top_slap → fingerstyle`
- S4/S5 prefix before mute boundary: **sample exact**
- post-mute S4→S5 delta RMS ratio: `0.2699174850911716`
- deterministic: **true**
- Render-IR events: **exact**
- Render-IR event count: **12**, unchanged
- peak: `0.5538963645245608`
- muted-strum long-term residual retain: `0.5155180837078245`
- dead-strum long-term residual retain: `0.2512547200029794`
- hammer-on same-string carry-time scale: `2.3120000000000003`
- dead-note same-string carry-time scale: `0.22100000000000009`

These values are state-transition controls, not newly authored notes or hidden
performance events. The S5 preset remains independently opt-in and S4 remains
unchanged.

S5 is **ENGINEERING PASS**. The next barrier is S6: passive energy / no-input
decay / long-horizon stability for the combined S1-S5 state.

## Planned downstream slices

- **S2 Same-string continuity:** implementation candidate in this branch; close after the S2 engineering gate above.
- **S3 Shared bridge/body memory:** engineering PASS on `43c03e8a131ad1de6b0c5f2530f1e6b42d35ebca`; CI #245 and S3 evidence #8 SUCCESS.
- **S4 Sympathetic cross-string coupling:** ENGINEERING PASS on `51b76943e63cd79e887553266c6240db8e436be7`; CI #255 SUCCESS.
- **S5 Technique-transition continuity:** ENGINEERING PASS on `c517ab274ec76e57010529cdc1d7f0853ccd2471`; CI #265 SUCCESS.
- **S6 Passive energy/stability barrier:** NEXT — no-input decay, finite impulse energy, no runaway feedback or body drone.
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
