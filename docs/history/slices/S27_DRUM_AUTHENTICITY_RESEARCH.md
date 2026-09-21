# S27 Drum Authenticity Research — performance-first acoustic drum reconstruction

Status: S27-B HI-HAT GATE OPEN
Date: 2026-09-20
Runtime baseline: S19 dry core + R5 cymbal source + S26 shared-kit integration

## Objective

Reconstruct the acoustic drum path from performance mechanics instead of continuing preset-only timbre tuning.
The target is not a named commercial kit. The target is a generic, physically and musically plausible acoustic drum set whose authored performance behaves like one drummer playing one kit.

The causal chain is:

`gesture -> contact/excitation -> resonator/coupling -> articulation -> player feasibility -> shared kit/room`

A change is accepted only when it survives musical-context audition. Solo spectral metrics are evidence, not closure.

## User performance model to preserve

1. Crash: phrase/section entry, transition and strong accent voice.
2. Ride: sustained timekeeping alternative to hi-hat; bow/bell/edge must remain distinct gestures.
3. Toms: high -> mid -> floor form a descending pitch/size family and support fills/transitions.
4. Hi-hat: a two-cymbal + pedal system; closed/open state is continuous control, with stick and foot articulations.
5. Snare: backbeat center in common pop/rock contexts, with ghost/rim articulations available rather than forced globally.
6. Kick: foot/beater-driven low-frequency pulse and forward propulsion.
7. Floor tom: lowest tom, important for fill endpoints and heavy sectional punctuation.

These are default performance semantics, not universal genre rules.

## Evidence from BLACK_GLASS_HORIZON_24k.wav

File: `/mnt/data/BLACK_GLASS_HORIZON_24k.wav`
- sample rate: 24 kHz stereo
- duration: ~110.03 s
- beat tracker estimate over the active body: ~125 BPM

A percussive HPSS/onset probe of the dense 80-98 s region found high-frequency-dominant onsets near 82.99 s and 92.67 s whose first-15-ms RMS is about 0.021-0.022, while nearby strong drum transients reach roughly 0.15-0.33. This does not identify instrument physics from a mastered mix, but it is consistent with the perceptual report that the cymbal has wash/high-frequency energy without enough mechanical strike authority.

## Current architecture audit

### Strong preservation anchors

- S19 `_legacy_kick`, `_legacy_snare`, `_legacy_hat`: perceptually preferred core; LOCKED.
- S26 shared overhead/room/bus layer: keep as opt-in recording layer, but never use it to hide source defects.
- R2/R3 cymbal long-tail correction: preserve the shorter tonal tail target.

### Critical gaps

1. Composer/validation rhythm vocabulary is still fundamentally `kick/snare/hat` only.
2. Ride/crash exist in render/MIDI surfaces but are not first-class authored rhythm roles end-to-end.
3. Current S19-based path has no tom family.
4. Current hi-hat is one generic `hat`; it does not represent closed/half-open/open/pedal/choke states.
5. Current ride has no bow/bell/edge articulation contract.
6. Current snare path does not expose center/ghost/rimshot/cross-stick as first-class drum articulations.
7. Current cymbal strike contact is short band-passed white noise, not a mechanically coherent stick/cymbal collision.
8. Current `_plate_bank` randomizes modal phase independently. For an impulsive strike, modal initial conditions should be correlated by one contact event; arbitrary independent phase weakens the impression of a single mechanical impact.
9. Drum performance feasibility is not modeled. A composition can request simultaneous limb actions with no hand/foot occupancy model.

## Historical S20-S24 salvage policy

Do NOT restore the S21-S24 acoustic source as the canonical sound.

Do salvage the articulation vocabulary as a semantic reference:

- kick: default
- snare: center / ghost / rimshot / cross_stick
- hi-hat: closed / half_open / open / pedal / choke
- ride: bow / bell / choke (extend research to edge/crash-zone)
- crash: crash / choke
- tom_high / tom_mid / tom_floor: center / edge

The old sound implementation is evidence only. The new sound path must be independently derived from research and listening.

## Research findings -> implementation requirements

### A. Percussion gesture and contact

Dahl and Altenmüller show that percussion sound level, attack and timbre depend on the complete striking gesture, contact force/duration and rebound. Because contact is only a few milliseconds, the player cannot correct the sound after contact begins.

Implementation consequence:
- `velocity` cannot be only an output multiplier.
- authored strike force must control contact duration, impulse shape, brightness, resonator excitation and rebound/damping state.
- normal/free-rebound and controlled/damped strokes must not share one excitation envelope.

References:
- Sofia Dahl, *Striking movements: A survey of motion analysis of percussionists*, Acoustical Science and Technology 32(5), 2011. DOI 10.1250/ast.32.168.
- Sofia Dahl & Eckart Altenmüller, *Motor control in drumming: Influence of movement pattern on contact force and sound characteristics*, JASA 123(5), 2008. DOI 10.1121/1.2933043.

### B. Membrane drums: hit position, nonlinear tension and coupled heads

Avanzini/Marogna model membrane percussion as modular interaction among impact force, nonlinear membrane/tension modulation, enclosed-air coupling between heads and other coupled elements. Hit position changes modal weighting: central hits emphasize lower/symmetric modes; off-center hits excite a different modal set.

Suzuki/Hwang show that two heads coupled through the enclosed air split resonance behavior into in-phase/out-of-phase families; mild intentional mistuning changes those coupled resonances.

Implementation consequence:
- kick/toms/snare must have `strike_position`, not merely fixed mode ratios.
- tom high/mid/floor should be one model family parameterized by head size/tension/cavity, not three unrelated oscillators.
- resonant-head/cavity coupling is useful, but must be added only if it improves the dry sound; past S21 over-modeling is not a precedent.

References:
- F. Avanzini & R. Marogna, IEEE TASLP 18(4), 2010. DOI 10.1109/TASL.2009.2036903.
- H. Suzuki & Y.-F. Hwang, *Coupling between two membranes of a Japanese drum*, Acoustical Science and Technology 29(3), 2008. DOI 10.1250/ast.29.215.

### C. Snare: batter membrane + stick + snare-wire interaction

Ito/Terashima experimentally show that striking technique changes modal decay, and identify the stick and snare wire as important contributors to the generated sound. Snare-wire behavior complicates membrane vibration rather than acting as a stationary broadband noise tail.

Implementation consequence:
- preserve a membrane/body event and a collision/rattle event as distinct coupled layers.
- ghost/center/rimshot/cross-stick require different contact geometry, not one snare waveform with gains.

Reference:
- T. Ito & O. Terashima, *Experimental Study on the Vibration of Membranes and Generation of Sound in a Snare Drum with Extended Proper Orthogonal Decomposition*, Advanced Experimental Mechanics 4, 205-211, 2019. DOI 10.11395/aem.4.0_205.

### D. Cymbals: motion-driven impact, strike zone and nonlinear plate behavior

Kaselouris et al. drive cymbal FEM/BEM simulation with measured 3D drumstick motion and progressively intensified strokes. This directly supports using a mechanical contact event instead of random-noise contact.

Nguyen/Touze show that cymbal taper/shape and geometric nonlinearity are central to bell-like vs crash-like behavior; edge strikes and strong excitation generate the characteristic high-frequency crash field through nonlinear plate dynamics.

Implementation consequence:
- replace white-noise contact as the primary strike with a short force pulse/contact model.
- one impact must provide one shared mechanical time origin, but a cymbal must not collapse to a few phase-locked stable partials; localized mode-shape signs, high modal density, irregular spacing and rapid post-impact de-phasing are required to avoid bell/gong-like ringing.
- strong crash excitation should broaden toward a wide-band high-frequency field after the impact; a sparse linear modal bank is an insufficient approximation even if its initial phase is mechanically coherent.
- ride bow = tip-on-bow with clear stick definition and restrained wash.
- ride bell = different strike zone/resonator weighting, normally stronger/drier/cutting.
- crash = edge/shoulder-type excitation with strong early mechanical impact followed by nonlinear spectral bloom; do not synthesize the crash merely by opening a long noise wash.
- retain R2/R3 tail limits so authenticity does not reintroduce the old tonal `wooo` artifact.

References:
- E. Kaselouris et al., *FEM-BEM Vibroacoustic Simulations of Motion Driven Cymbal-Drumstick Interactions*, Acoustics 5(1), 165-176, 2023. DOI 10.3390/acoustics5010010.
- T. Nguyen & C. Touze, *Nonlinear vibrations of thin plates with variable thickness: Application to sound synthesis of cymbals*, JASA 145, 977-988, 2019. DOI 10.1121/1.5091013.
- M. Ducceschi & C. Touze, *Modal approach for nonlinear vibrations of damped impacted plates: Application to sound synthesis of gongs and cymbals*, Journal of Sound and Vibration 344, 313-331, 2015. DOI 10.1016/j.jsv.2015.01.029.

### S27-A1 postmortem — why the first physical strike sounded like a bell

The first S27-A implementation corrected the contact event but drove only a sparse set of stable modal partials from the same cosine-like initial condition. Perceptually this moved the failure from `soft/noise contact` to `pitched bell/gong`: the hit had authority, but the radiated plate field remained too low-dimensional.

The A2 correction keeps the same short mechanical force pulse and short-tail contract, but expands the authored modal anchors into a dense deterministic inharmonic field. Mode-shape signs differ, frequencies are irregularly distributed between anchors, upper modal density is increased, and bow/edge strikes suppress low-order bell radiation. This is a compact real-time approximation to the broad mode participation / energy-cascade behavior described in impacted-cymbal literature, not a full nonlinear FEM/BEM model.

### E. Hi-hat is a coupled two-cymbal system

Closed/open hi-hat is not a decay preset on one cymbal. Pedal pressure changes contact between two cymbals. Closing transfers/damps vibration; opening removes that contact and permits freer plate motion.

Implementation consequence:
- represent `openness`/clamp state independently from stick velocity.
- closed, half-open and open may remain convenient articulations, but internally they should map to a continuous contact/damping state.
- pedal chick is cymbal-cymbal collision, not a stick hit.
- open->close must be able to terminate/damp an already ringing hat state.

Architecture evidence:
- historical S20 articulation vocabulary is directionally useful, but the new coupled-state implementation must be independent.

### F. Performance semantics and limb feasibility

A convincing kit is played by one body. Sound authenticity therefore includes which limbs can produce which event and what events replace each other.

Minimum performance state:
- right/left hand occupancy
- right/left foot occupancy
- hi-hat pedal state
- ride/hat timekeeping voice
- crash accent substitution (do not automatically stack crash + ride on the same limb/timekeeping event)
- fill motion across tom_high -> tom_mid -> tom_floor
- rebound-aware dynamic hierarchy (ghost / tap / accent)

This layer belongs in authored-performance validation, not inside the deterministic DSP engine.

## S27 bottleneck sequence

### S27-A — Cymbal strike mechanics (FIRST)

Why first: it is the current audible blocker and the current code has a specific incorrect contact model.

Locked:
- S19 kick/snare/closed-hat source hashes
- R2/R3 cymbal maximum tail behavior
- S26 room disabled during source evaluation

Implement:
1. deterministic velocity-dependent stick force pulse;
2. coherent modal initial conditions for ride/crash;
3. ride bow tip contact;
4. crash edge/shoulder contact + delayed nonlinear-style bloom approximation;
5. strike-position parameter that changes modal weighting, not just EQ;
6. source-only 24 kHz A/B, then actual-groove A/B, then S26 room A/B.

Closure test:
- user hears a wooden stick striking metal before hearing the plate sustain;
- strong crash has authority but no old tonal long-tail;
- repeated ride retains individual ping definition at tempo.

### S27-B — Hi-hat coupled state · ENGINEERING CANDIDATE

Research anchor: Sekiguchi & Samejima (2023), *Physical modeling and sound synthesis of the hi-hat*, DOI `10.1250/ast.44.352`. Their two-shell/collision framing supports the key causal requirement: a hi-hat is two cymbals whose separation/contact and repeated collision are pedal-controlled.

Implemented as explicit opt-in articulations: `hat_tight_closed`, `hat_closed`, `hat_half_open`, `hat_open`, `hat_pedal`, and `hat_foot_splash`. The compact model uses distinct top/bottom dense plate fields plus an aperiodic inelastic edge-collision texture. The legacy `hat` event remains byte-preserved.

The first candidate weakened the approved S19 closed-hat onset and was retuned before audition. The current state is regression-protected against that failure. Continuous pedal trajectories and stateful close/choke of an already-ringing open hat remain deferred.

### S27-C — Snare articulation authenticity · CLOSED

Center/ghost/rimshot/cross-stick with contact geometry + wire response, preserving the preferred S19 center backbeat as the anchor. User perceptual gate passed on 2026-09-20.

### S27-D — Tom family · CLOSED

One parameterized high/mid/floor two-head model with size-specific head tuning, enclosed-air/cavity coupling, shell response and center/edge strike-position relationships. User perceptual gate passed on 2026-09-20. The dominant low body near 179/133/92 Hz for high/mid/floor and size-specific decay/center-edge response are now locked.

### S27-E — Kick gesture refinement

Beater/free-rebound vs buried/damped semantics only if musical-context audition proves the current S19 kick needs it. Do not reopen a strong anchor without evidence.

### S27-F — Drummer performance validator · CLOSED

Adds an evidence-only four-limb feasibility analyzer over resolved drum events. It preserves authored timing/content and deterministically assigns stick events across two hands while treating kick as right-foot and hi-hat pedal/splash as left-foot work. Exact capacity contradictions are HIGH evidence; fast repetition and large cross-kit moves are technique/strain evidence rather than automatic deletion. Pipeline analysis surfaces the report when drum events are present. Sound synthesis remains locked.

### S27-G — Shared kit/room final integration · CLOSED

Re-tunes S26 overhead/room/bus against the corrected source. The new room path is articulation-aware, adds a small overhead propagation delay, prioritizes early reflections over late wash, and uses lighter parallel glue. A 16-bar / 269-event flagship passed S27-F with zero issues before rendering. Room must enhance a good kit, never manufacture realism for a weak source.

User perceptual gate passed on 2026-09-20 after RMS-matched S26→S27-G flagship listening. S27-G is now the accepted shared-kit/room integration baseline.

### S27-H — Stateful hi-hat closure / choke · CLOSED

Adds an opt-in authored state transition so a later half-open/closed/tight/pedal event can dissipate the residual energy of an already-ringing open hi-hat. The accepted S27-B hit source is unchanged and non-hi-hat voices are never gated. User continuation to S27-I on 2026-09-20 closes this discrete-event state slice.

### S27-I — Continuous hi-hat pedal openness · CLOSED

Adds an explicit non-audio `drum_control` event for piecewise-linear `hi_hat_pedal_openness`. The control is authored left-foot performance evidence, affects only residual open/half-open hi-hat energy, uses separate body/wash cumulative loss, and never infers a style or hidden pedal gesture. S27-H discrete closure remains byte-exact when no curve is authored. User continuation to S27-J closes this slice.

### S27-J — Persistent hi-hat pedal state / strike coupling · CLOSED

Carries the final authored pedal openness beyond the end of a control curve and applies it at subsequent stick-strike time. The accepted S27-B tight/closed/half/open mechanics are interpolated at the source, so a pedal-held half-closed hat does not start from a fully-open excitation and get faded afterward. User perceptual gate passed on 2026-09-20.

### S27-K — Hi-hat foot gesture / chick–splash coupling · ENGINEERING CANDIDATE

Closes the remaining disconnect between the explicit pedal trajectory and the existing foot articulations. A sufficiently fast authored close that crosses the contact threshold now produces the physical two-cymbal chick consequence; a fast release from a genuinely clamped state produces the longer foot-splash release. Slow pressure changes and partial motion that never reach contact remain mechanically silent. No genre/style foot gesture is inferred, and the authored control remains the sole left-foot performance event for S27-F evidence.

## Research hygiene

- Research papers/open source may inform equations, architecture and validation targets.
- Do not copy third-party implementation source into Code Composer.
- Do not ship samples, IRs, meshes, measured modal tables or datasets unless licensing/provenance is explicitly audited.
- The production engine remains deterministic and user/Composer-Agent controlled.
- No trained ML model is required for the drum path.


## S27-B closure / S27-C implementation checkpoint

- S27-B two-cymbal hi-hat passed the user perceptual gate and is CLOSED.
- S27-C opens only the snare articulation bottleneck while preserving legacy `snare`.
- Explicit techniques: center, ghost, rimshot, cross-stick.
- Current causal implementation couples batter head -> delayed resonant head -> motion-driven wire response, with rim/shell excitation for rim techniques.
- Next gate is drummer-context listening before any S27-D tom work begins.


## S27-D implementation checkpoint

- S27-C snare articulation passed the user perceptual gate and is CLOSED.
- S27-D adds explicit high/mid/floor center and edge tom events without modifying legacy event paths.
- Equal-velocity source evidence shows ordered family pitch and ordered decay/body length, not pitch-shift-only behavior.
- Next gate is user listening to family ladder, center/edge pairs and descending fills before any S27-E kick work.


## S27-G implementation checkpoint

- S27-D tom family user gate passed and is CLOSED.
- S27-F performance validator was accepted by proceeding to S27-G and is CLOSED.
- S27-G changes no dry percussion source block.
- New integration consumes explicit authenticated articulation names for room excitation and adds a preset-only 2.9 ms overhead propagation cue.
- First room-heavy tuning was rejected because RMS matching weakened close-hit authority; current candidate keeps whole-render RMS approximately equal to dry while retaining early room support.
- 16-bar flagship: 269 events, S27-F `playable=true`, no HIGH/MEDIUM/LOW issues.
- S27-G full-kit RMS-matched A/B passed the user perceptual gate on 2026-09-20 and is CLOSED; later hi-hat state slices build on this accepted shared-room baseline.
