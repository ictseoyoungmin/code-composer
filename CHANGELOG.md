
## S27-M R2 — Ensemble / Production Integration (reopened on S28-H baseline)
- Rebuilt the previously partial S27-M slice on the complete S28-H piano-naturalism source tree after the local historical S27-M directory was found incomplete.
- Adds explicit section `role_velocity_scales` and selector-scoped `targeted_onset_yields`.
- Targeted yielding is attack-only, proximity-weighted, deterministic and never acts as global sustain ducking; `*_control` events are untouched.
- Existing S15 timing offsets, overlap-weighted yielding and role-pan offsets remain compatible and ordered.
- Full repository: **95 test files / 636/636 PASS** (partitioned); standalone self-check, skill validation, plugin distribution, compileall and Skill/Codex/Claude builds PASS.
- Status remains **ENGINEERING CANDIDATE / PERCEPTUAL GATE OPEN** pending listening.
- Full-song flagship `Crossing Meridian`: 12 bars / 24 kHz / 112 BPM / 27.91425 s; piano 121 / bass 46 / violin 42 / drums 175 events; A/B RMS 0.15855/0.15815; clipping 0.

## v1.17.0 — S28-H Piano Naturalism Production Closure — ENGINEERING CANDIDATE

- Freezes the accepted acoustic-piano chain: S28-A R2 continuous pedal + S28-B per-strike identity + S28-C authored hand-roll + S28-D phrase timing/gate + S28-G subtle treble-unison decoherence. S28-E remains rejected.
- Adopts S28-F **no automatic music-bus ducking** as the canonical source-piano baseline; light ducking stays an explicit later ensemble/mix decision.
- Adds `Quiet Mechanics of Light`, a 16-bar / 24 kHz piano-only closure dogfood spanning low 1-string, middle 2-string and treble 3-string registers, explicit repedal, wide chords, repeated treble and directional phrase timing/gate.
- Fixes a cross-surface bug: E1 phrase realization now passes `*_control` events through byte-preserved instead of adding note-only velocity/gate/timing/performance metadata or deleting them inside phrase breath.
- Closure render: 43.389125 s, 84 note events + 16 sustain-pedal controls, MIDI 31-76, peak 0.74285, clipped sample ratio 0.
- Full repository after the S28-H control-event hardening: **94 test files / 629/629 PASS** (partitioned); standalone/build validation PASS.

## v1.17.0 — S28-G Subtle Treble Unison Decoherence — LISTENING CANDIDATE

- User confirmed the artifact is present in the current high-register 3-string model but absent in 1-string / detune=0 diagnostics; those diagnostics also reduced piano realism, so string count and mean detune are preserved.
- Adds opt-in `piano.concert_grand_natural_unison_subtle@1.0.0`; canonical `piano.concert_grand_natural` remains unchanged.
- In 3-string treble only, adds tiny deterministic per-partial mistuning plus string-specific inharmonicity, decay, and level asymmetry. No random LFO, chorus, pitch sweep, detune removal, or 1-string shortcut.
- Exact-problem reproduction requires the current A path to render byte-identically to the previously evaluated problem WAV before producing B. A reproduction passed; score, seed, pedal timeline, S28-B/C/D semantics, gain, drive, ceiling, and tail are identical.
- S28-G + piano/S28/factory/provenance focused regression: 96/96 PASS; standalone/build validation PASS.

## v1.17.0 — S28-F Piano Phrase-Safe Music-Bus Ducking Audit

- User selected the exact S28-D treatment (S28-A R2 + S28-B/C/D) as the listening baseline and rejected S28-E coupled-unison sustain.
- Adds a reproducible production audit for the reported drum→music-bus ducking settings without changing `duck()` or adding genre heuristics.
- Exact A baseline + controlled modeled kick compares no-duck, current `1.8 dB / 8 ms / 150 ms / -28 dB`, and a light explicit `0.7 dB / 10 ms / 80 ms / -26 dB` alternative.
- Current settings reduce piano RMS to about `0.9360x` and keep gain reduction active about `28.7%` of the passage; light settings retain about `0.9773x` RMS with about `22.3%` activity.
- Runtime authority remains explicit in the mix plan; this slice introduces no automatic sidechain policy.

## v1.17.0 — S28-D Authored Piano Phrase Direction Timing / Gate

- Reuses the existing v1.16 E1 `timing_curve_ms` + `gate_curve` contract instead of inventing a duplicate piano timing system.
- Piano naturalism dogfood disables random microtiming/velocity variation and authors forward motion / resolution timing explicitly.
- Hardens E4 orchestration-budget realization so explicit `*_control` events pass through unchanged and are not decorated/arbitrated as sounding note events.

## v1.17.0 — S28-C Authored Piano Hand Attack / Chord Micro-roll

- Adds explicit `performance.piano_attack_offset_ms` bounded to ±20 ms.
- Applies offsets to render-local piano note copies only; canonical score onsets remain unchanged.
- Supports subtle wide-chord hand rolls such as 0/4/8/11/13/15 ms without random humanization or inferred arpeggiation.

## v1.17.0 — S28-B Deterministic Per-strike Piano Identity

- Adds opt-in `piano.concert_grand_natural@1.0.0`.
- Adds bounded deterministic strike identity for string/partial/unison phase and hammer excitation.
- Same score+seed remains byte-reproducible; historical presets keep the feature disabled and remain on their prior path.
- Non-note piano controls do not consume strike ordinals.

## v1.17.0 — S28-A R2 Continuous Pedal Release Naturalism — CLOSED

- User listening reopened the first candidate because pedal-up produced a synthetic `wah/meow` tail.
- R1 was insufficient. R2 identified coherent detuned-unison beating plus lingering fixed soundboard modes as the combined cause.
- Pedal-up now uses short staggered damper contact across all unison strings and a shorter fixed-modal body state after lift, without pitch sweeping or mix masking.
- User perceptual PASS closes S28-A R2.

## v1.17.0 — S28-A Continuous Acoustic-Piano Sustain Pedal State (initial candidate; superseded by R2 closure)

- Adds explicit `piano_control / sustain_pedal` curves with persistent pedal position for acoustic piano tracks.
- Key release under pedal now sustains only until the next authored pedal-up crossing, then returns to the normal S14 damper release instead of attaching another long note-local pedal tail.
- Repedal does not resurrect already-damped prior-harmony energy.
- Track-wide sympathetic/soundboard coupling follows the same explicit pedal state.
- Legacy projects without piano-control events retain historical note-local `performance.pedal` rendering.
- 92 BPM harmony-change dogfood reduces isolated prior-chord residual RMS 300–1200 ms after the next bar from `0.05332677` to `0.00005948`.
- Full repository: **88 test files / 597/597 PASS** (partitioned).
- Initial status was **ENGINEERING CANDIDATE / PERCEPTUAL GATE OPEN**; subsequent user listening reopened this version and S28-A R2 later closed the release artifact.

## S27-L — Full-Song Authenticated Drum Chain / Production Closure (2026-09-20)

- Closed S27-B R1 and S27-K R2 after user production listening confirmed the felt/fabric hi-hat artifact was gone.
- Added no new synthesis feature; S27-L follows the roadmap rule to return to real-song listening before opening another engine slice.
- Added reproducible 24 kHz / 112 BPM / 12-bar `Cobalt Meridian` production dogfood: Intro → Verse → Pre → Chorus → Outro with piano, modeled bass, articulated violin and the full authenticated drum chain.
- Drum performance: 175 events / hands 118 / right foot 46 / left foot 11 / playable=true / strained=false / HIGH-MEDIUM-LOW=0/0/0.
- Added `tools/s27l_full_song_drum_chain.py` with separate deterministic stem rendering for command-duration-safe reproduction.
- S27-L remains listening-gated; the next engine slice must be chosen from production evidence rather than preselected.

## S27-B R1 — Resonant Metal Hi-Hat Collision Rework (2026-09-20)

- Reopened the previously accepted S27-B two-cymbal hi-hat after production listening revealed that the normalized broadband collision layer itself read as `felt/fabric/sandpaper` rather than metal.
- Added opt-in preset `drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_foot_gesture_metal_hihat@1.0.0`; earlier S27-B through S27-K presets remain available unchanged for regression.
- New `two_plate_modal_contact_v2` / `modal_plate_excitation_v2` path converts irregular edge re-contact into finite mechanical force pulses that excite a dense high-order inharmonic plate field. The contact force is never emitted as a normalized broadband audio layer.
- Retuned closed / half-open output and modal-contact energy to preserve the accepted strike presence while keeping fully open decay longer than half-open chatter.
- S27-K R2 authored pedal-motion chick/splash remains downstream-compatible; only dependent output calibration changes in the new preset.
- The original broadband S27-B path remains byte-preserved for old presets; non-hi-hat sources remain byte-exact.
- 15 s `Cobalt Pulse` production gate is rerendered at 24 kHz / 112 BPM / 7 bars with identical arrangement, seed and mix for direct R2-broadband → S27-B R1 metal-contact comparison.
- Engineering validation: S27-B R1 focused 8/8; expanded related gate 75/75; full repository 86 test files / 585/585 PASS; Skill/plugin/build validation PASS.

## S27-K R2 — Foot Contact Fabric-Noise Fix (2026-09-20)

- User production-context listening rejected R1: sparse crackle was gone, but the denser broadband micro-contact layer read as a soft `felt/fabric/sandpaper` stepping noise behind chick/splash.
- Root cause: R1 converted isolated edge impulses into a denser additive collision field. In a full mix this behaved like a short friction-noise bed rather than plate contact.
- New control-derived foot model: `authored_motion_plate_contact_v3`. The additive collision layer is disabled (`gain_scale=0`) for control-derived chick/splash; audible energy comes from the existing two-plate response plus contact radiation.
- Gesture-specific output calibration (`chick_output_gain=2.0`, `splash_output_gain=1.25`) preserves audibility without restoring broadband collision noise.
- Direct `hat_pedal` / `hat_foot_splash` and S27-J locked sources remain byte-exact because the change is scoped to `render_hi_hat_pedal_control`.
- Same 15 s / 112 BPM production gate is used for listening closure; no noise gate or aggressive mastering hides the result.

## S27-K R1 — Foot Chick/Splash Crackle Fix (2026-09-20)

- Reopened S27-K after user reported a small `지직/틱` tail behind control-derived chick/splash.
- Root-caused the defect to sparse two-sample impulses in `_hat_collision_texture()` becoming exposed after the main foot gesture decayed.
- Added an opt-in micro-contact collision profile only for control-derived foot gestures: short raised contact pulses, moderately higher contact density, and lower collision gain.
- Preserved direct `hat_pedal` / `hat_foot_splash` sources byte-exact to S27-J/S27-K and kept slow pedal motion silent.
- Added regression gates for splash late-tail sample-step/crest reduction and chick edge-spike reduction.

## S27-K — Hi-Hat Foot Gesture / Chick–Splash Coupling (2026-09-20)

- Closed S27-J after user perceptual PASS.
- Coupled explicit fast pedal-close motion to physical chick excitation and fast clamped reopen motion to foot-splash release.
- Slow or non-contact pedal motion remains silent; no hidden genre/style foot gesture generation.
- Uses a deterministic control-only seed so derived foot audio does not perturb later audible drum-hit RNG identity.

## S27-J — Persistent Hi-Hat Pedal State / Strike Coupling (2026-09-20)

- Closed S27-I by user continuation to the next slice.
- Added persistent authored `hi_hat_pedal_openness` state for later stick-strike coupling.
- Added continuous interpolation across accepted S27-B stick-state mechanics anchors.
- Made non-audio pedal-control insertion RNG-neutral for later S27-J audible hits.
- No-control S27-I rendering remains byte-exact; no genre grammar or hidden foot automation added.

## S27-I — Continuous Hi-Hat Pedal Openness / Within-note Closure (2026-09-20)

- Closed S27-H by user continuation to the next slice.
- Added explicit non-audio `drum_control` events for authored `hi_hat_pedal_openness` trajectories.
- Added opt-in continuous state preset with cumulative two-band body/wash damping; no inferred pedal motion or genre grammar.
- Extended S27-F evidence so authored continuous pedal motion is visible as left-foot activity.
- Existing presets and S27-H discrete closure behavior remain opt-in and unchanged.

## S27-H — Stateful Hi-Hat Closure / Choke (2026-09-20)

- Closed S27-G after user perceptual PASS on the RMS-matched 16-bar shared-kit audition.
- Added opt-in authored state damping for already-ringing open/half-open hi-hat tails.
- Later half-open/closed/tight/pedal events damp only prior hi-hat energy; other kit voices and the closure hit itself remain untouched.
- Continuous pedal trajectories and genre-specific hi-hat grammar remain deferred.

## 2026-09-20 — S27-G Shared Kit / Room Final Integration

- Added a factory preset that preserves S27-D dry sources and changes only kit-level integration.
- Added articulation-aware room excitation for authenticated hi-hat, snare and tom events.
- Added optional overhead propagation delay; old presets default to zero and retain pre-S27-G behavior.
- Re-tuned the compact studio room toward early reflections, shorter/darker late field and lighter body/bus glue.
- Added a 16-bar 118 BPM flagship performance that passes S27-F with 269 events and zero feasibility/strain issues.
- Added `tools/s27g_shared_kit_room_flagship.py` to reproducibly regenerate dry/S26/S27-G RMS-matched closure auditions, metrics, event evidence and limb assignments without changing the approved drum sources.
- First room-heavy tuning was rejected because RMS-matched close-hit authority dropped too far; current candidate keeps whole-render RMS approximately equal to dry.

## 2026-09-20 — S27-F Drummer Limb / Performance Validator

- Closed S27-D Tom Family Authenticity after user perceptual PASS.
- Added evidence-only `analyze_drummer_performance()` with a conservative four-limb drum-set model.
- Maps kick to right foot, hi-hat pedal/splash to left foot, and stick-driven drum/cymbal events to deterministic left/right-hand assignments.
- Reports impossible simultaneous limb demand separately from demanding rate/travel evidence; never rewrites or requantizes authored events.
- Pipeline analysis now surfaces drummer-performance evidence when resolved drum events are present.
- S19/S27 sound engines remain untouched.

## S27-D — Tom family authenticity (engineering candidate)

- Marks S27-C snare articulation as perceptually CLOSED and opens only the tom-family bottleneck.
- Adds opt-in preset `drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms@1.0.0`; all prior kick/snare/hat/ride/crash and S27-B/C articulations remain byte-preserved.
- Adds `tom_high`, `tom_mid`, `tom_floor` plus matching `_edge` articulations.
- Models each size with distinct batter/resonant-head tuning, enclosed-air/body coupling, shell modes, decay, output bandwidth and tail instead of pitch-shifting one oscillator.
- Center/edge strokes change modal weighting and shell/contact contribution causally rather than through gain/EQ-only variants.
- Maps high/mid/floor toms to MIDI notes 50/47/43.
- Status is **ENGINEERING CANDIDATE / PERCEPTUAL GATE OPEN** pending family-ladder and descending-fill listening.

## S27-C — Snare articulation authenticity (engineering candidate)

- Marks S27-B two-cymbal hi-hat as perceptually CLOSED and opens only the snare articulation bottleneck.
- Adds opt-in preset `drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare@1.0.0`; all prior kick/legacy-snare/legacy-hat/hi-hat/ride/crash rendering remains preserved.
- Adds explicit `snare_center`, `snare_ghost`, `snare_rimshot`, and `snare_cross_stick` events.
- Models strike-position-dependent batter-head modes, delayed resonant-head transfer, resonant-head-driven snare-wire noise, and technique-specific rim/shell excitation rather than gain/EQ-only variants.
- Retunes the first rimshot candidate so the simultaneous head+rim stroke keeps a bright crack instead of being dominated by low hoop modes.
- Maps cross-stick to MIDI side-stick note 37 while center/ghost/rimshot remain note 38.
- Status is **ENGINEERING CANDIDATE / PERCEPTUAL GATE OPEN** pending actual backbeat/ghost/rimshot/cross-stick listening.

## S27-B — Two-cymbal hi-hat mechanics (CLOSED)

- Adds opt-in preset `drums.s19_core_powerful_room_authentic_strike_v2_hihat@1.0.0` while preserving S27-A2 kick/snare/legacy-hat/ride/crash rendering byte-exactly.
- Adds explicit `hat_tight_closed`, `hat_closed`, `hat_half_open`, `hat_open`, `hat_pedal`, and `hat_foot_splash` articulation events and standard MIDI-note mappings.
- Models distinct top/bottom dense inharmonic plate fields, pedal-state-dependent transfer/damping, and seeded aperiodic inelastic edge-collision chatter rather than treating open/closed as one sample with different decay.
- Retunes the explicit two-plate closed articulation after the first candidate measured too weak against the S19 closed-hat anchor; current regression requires preservation of legacy-level strike authority.
- Research provenance follows Sekiguchi & Samejima (2023), DOI `10.1250/ast.44.352`, as a causal reference only; no paper implementation/assets are copied.
- Status: **CLOSED / PERCEPTUAL PASS** on 2026-09-20.


## S27-A — Drum authenticity / cymbal strike mechanics (engineering candidate)

- Reframed acoustic-drum work around `gesture -> contact -> resonator -> articulation -> player feasibility -> room`, then opened only the current audible blocker: ride/crash stick impact.
- Added opt-in preset `drums.s19_core_powerful_room_authentic_strike@1.0.0`; S19 kick/snare/closed-hat and S26 kit-integration blocks remain unchanged.
- Replaced noise-led cymbal contact in the new preset with a deterministic, velocity-dependent short stick-force pulse plus coherent modal excitation.
- Uses a velocity/radiation-like modal response at the acoustic output boundary so a struck cymbal radiates immediately; an earlier displacement-like sine response was measured, rejected, and not retained because it weakened the first 5 ms strike.
- Retains the R2/R3 shortened ride/crash decay and tail contracts, so stronger strike authority does not reopen the historical tonal `wooo` smear.
- Adds source-only, 125 BPM drummer-context and S26-room A/B dogfood plus focused regression for strike authority, velocity-dependent contact shape, determinism, seed sensitivity and core byte preservation.
- Research provenance covers percussion gesture/contact mechanics, coupled drumheads/snare behavior, motion-driven cymbal impact and nonlinear cymbal plate behavior; no external samples, room IRs, measured modal tables or third-party DSP source are bundled.
- Status is **ENGINEERING CANDIDATE / PERCEPTUAL GATE OPEN** until the user confirms that ride and crash now read as a wooden stick striking metal.

# Changelog

## v1.17.0 — S28-H Piano Naturalism Production Closure — ENGINEERING CANDIDATE

- Freezes the accepted acoustic-piano chain: S28-A R2 continuous pedal + S28-B per-strike identity + S28-C authored hand-roll + S28-D phrase timing/gate + S28-G subtle treble-unison decoherence. S28-E remains rejected.
- Adopts S28-F **no automatic music-bus ducking** as the canonical source-piano baseline; light ducking stays an explicit later ensemble/mix decision.
- Adds `Quiet Mechanics of Light`, a 16-bar / 24 kHz piano-only closure dogfood spanning low 1-string, middle 2-string and treble 3-string registers, explicit repedal, wide chords, repeated treble and directional phrase timing/gate.
- Fixes a cross-surface bug: E1 phrase realization now passes `*_control` events through byte-preserved instead of adding note-only velocity/gate/timing/performance metadata or deleting them inside phrase breath.
- Closure render: 43.389125 s, 84 note events + 16 sustain-pedal controls, MIDI 31-76, peak 0.74285, clipped sample ratio 0.
- Full repository after the S28-H control-event hardening: **94 test files / 629/629 PASS** (partitioned); standalone/build validation PASS.

## v1.17.0 — S26 Drum Kit Powerful Realism / Performance & Room Integration (engineering candidate)

- Opens a new kit-level realism bottleneck after the S19-core/R5 cymbal recovery path: individual drum sources remain preserved while the kit gains a shared recording/performance field.
- Adds opt-in factory preset `drums.s19_core_powerful_room@1.0.0`; its kick/snare/closed-hat/ride/crash source blocks are exactly inherited from `drums.s19_core_cymbal_extension@1.0.0`.
- Adds deterministic near-coincident overhead coloration, image-style early reflections, a compact four-line Hadamard feedback-delay-network late room, and authored-velocity-dependent room excitation.
- Adds a zero-delay low/body reinforcement path plus gentle parallel feed-forward bus compression so stronger authored performances gain weight and glue without replacing the approved dry transients.
- Adds a 4-bar drummer-plausible rock/pop dogfood: crash replaces the timekeeping cymbal on section downbeats, ride resumes on the next subdivision, and authored velocity/microtiming drive the performance.
- Research provenance is recorded in `CREDITS.md`; no third-party source, drum sample, microphone IR, room IR, or measured kit asset is bundled.
- Status remains **ENGINEERING CANDIDATE / PERCEPTUAL GATE OPEN** until the user confirms the dry-to-integrated A/B actually delivers the intended powerful realism.

## v1.17.0 — S25 S19-Core Cymbal Extension R5 (performance-context engineering candidate)

- Changes the cymbal closure gate from isolated-hit realism to drummer-like musical performance context while retaining isolated diagnostics as secondary evidence.
- Keeps the user-selected pre-S20 S19 kick/snare/closed-hat core locked and leaves the R2/R4 ride/crash decay and event-tail values unchanged.
- Adds nonlinear velocity-to-excitation response: soft ride timekeeping stays plate-forward, strong ride accents bring the short stick contact forward, and crash accents open low-mid impact plus delayed mid/high bloom without exposing the full bright field at t=0.
- Validation dogfood uses plausible hand/orchestration behavior: section-entry crash replaces the downbeat timekeeping cymbal and ride returns on the next subdivision instead of stacking crash and ride at the same instant.
- R5 high-vs-soft onset hierarchy is intentionally wider than R4 while soft hits remain bounded; long-tail regressions remain blocked.
- Status remains **ENGINEERING CANDIDATE** pending listening against R4 and current GitHub main in the same authored performance.

## v1.17.0 — S25 S19-Core Cymbal Extension R4 (engineering candidate)

- Keeps the user-selected pre-S20 S19 drum core locked; kick/snare/closed-hat and S17 modeled core function bodies remain source-identical to S19.
- Retains R2/R3 ride/crash decay and tail limits that removed the long tonal smear.
- Redistributes ride modes toward 2–6 kHz and narrows the wash band from 3.5–9.8 kHz to 3.2–8.5 kHz.
- Redistributes crash mid/high modal density toward 2–6 kHz while preserving the low-first delayed-bloom contract.
- Moderately restores cymbal output level without matching GitHub-main long-tail energy.
- Focused S17/S18/S19/S25 + factory/engine/MIDI regression: 65/65 PASS.
- Status remains **ENGINEERING CANDIDATE** pending musical-context listening.

## v1.17.0 — S25 S19-Core Cymbal Extension R3 (closure candidate)

- Re-anchored drum preservation to the user-selected pre-S20 S19 repository checkpoint.
- Preserved S19 legacy kick, snare and closed hi-hat byte-identically; S17 modeled kick/snare/hat function bodies also remain source-identical to S19.
- Added opt-in ride/crash extension without routing preserved core voices through later coupled-head/cavity drum changes.
- R2 removed the long tonal cymbal smear by shortening sparse low/mid modal decay while retaining bounded crash bloom.
- R3 leaves crash unchanged from R2 and shifts ride energy from excessive upper-air wash toward clearer 2–6 kHz stick/plate presence without lengthening decay.
- Focused S17/S18/S19/S25 + factory/engine/MIDI regression: 64/64 PASS. Full-suite run reached ~15% with no failures before execution timeout.
- Status remains **CLOSURE CANDIDATE** pending final musical-context listening.

## v1.17.0 — S19 Track Pan / Stereo Integrity Hardening

- Corrected legacy/non-graph `track.pan` so non-zero pan no longer collapses stereo instrument output to mono before repanning.
- Legacy track pan is now applied once after instrument rendering, engine post-processing, and legacy per-track insert FX using the same stereo-balance operator as graph routing.
- Preserved explicit event pan as an event-local control and preserved `track.pan=0` stereo output.
- Added 7 focused regressions across piano, articulated violin, modeled bass, modeled percussion, insert-FX ordering, graph parity, and event-pan composition.
- Matched full-song dogfood raised global stereo width from 0.05493 to 0.06869 and `open_field` width from 0.03560 to 0.06131 with master mono correlation 0.99793.
- Closed at source **467/467** and clean-installed **467/467** across 72 test files.

## v1.17.0 — S18 Track Gain Semantics / Mixer Predictability Hardening

- Corrected legacy/non-graph `track.gain` from a pre-synthesis velocity multiplier to a post-instrument linear fader.
- Preserved event velocity and instrument-expression authority, preventing track-level mix changes from altering piano/violin excitation or timbre.
- Kept graph-mode route gain semantics unchanged.
- Added 7 focused gain-semantics regressions across piano, articulated violin, modeled bass, modeled percussion, legacy inserts, and unity compatibility.
- Post-S17 real-song excerpt now matches requested gain ratios exactly across all four tracks.
- Closed at source **460/460** and clean-installed **460/460**.

## v1.17.0 — S17 Percussion Acoustic Fidelity Hardening

- Added registered `percussion` engine boundary while preserving explicit drum-event Music IR.
- Added opt-in factory preset `drums.acoustic_kit_modeled@1.0.0`.
- Modeled kick uses compact membrane modes, bounded strike-dependent tension relaxation and band-limited beater impact.
- Modeled snare combines membrane/body modes with deterministic stochastic wire-rattle energy.
- Modeled closed hi-hat uses inharmonic metallic modes with velocity-dependent brightness/decay and bounded seeded strike variation.
- Legacy percussion remains byte-identical when S17 realism hardening is absent/disabled.
- Added drum factory-preset selection to Composition Brief.
- S17 focused 10/10, source 453/453, clean-installed 453/453 PASS.

## v1.17 S16 — Bass Acoustic Fidelity Hardening

- Added the dedicated `plucked_bass` engine and `bass.electric_finger_modeled@1.0.0` factory preset instead of relying on a generic sine/triangle support patch.
- Added pluck-position and pickup-position harmonic shaping, bounded stiffness-like inharmonicity, frequency-dependent upper-partial damping, deterministic finger attack texture, pickup bandwidth, and low-width centered stereo output.
- Reused existing bass pitch-approach and attack/release performance controls without changing authored note content or arrangement authority.
- Added S16 acoustic-fidelity regression for determinism, damping, pluck/pickup spectral behavior, pitch approach, expression response, and invalid physical parameters.
- Dogfooded the new engine in **Last Light on Platform Three** at 24 kHz with all track events byte-equivalent at the IR-event level; only the bass patch changed.
- Closed at source **443/443** and clean-installed **443/443**.

## v1.17 S15 — Ensemble / Orchestration Realism

- Added explicit section-level ensemble interaction with authored leader roles, bounded role timing offsets, overlap-weighted support yielding, and additive role pan offsets.
- Preserved note content and existing orchestration/register authority; S15 does not automatically arrange music or apply random humanization.
- Added multi-track-per-role support so layered piano/bass/etc. tracks sharing one arrangement role receive the same interaction.
- Integrated explicit dynamic yielding with expressive masking QA as managed overlap evidence rather than automatic musical mutation.
- Added 24 kHz **Blue Hour Ensemble Rehearsal** A/B dogfood with identical note content and deterministic inter-player realization.
- Closed at source **435/435** and clean-installed **435/435**.

## v1.17 S14 — Acoustic Piano Release & Resonance Hardening

- Fixed the no-pedal acoustic-piano release-tail artifact at engine level instead of bypassing resonance in presets.
- Split the shared modal soundboard into a short damper-down body response plus a longer pedal-authorized response, preventing fixed soundboard modes from singing after ordinary note-off.
- Removed non-harmonic ratio tones from no-pedal per-note resonance; the historical 1.5× fundamental component can no longer emerge as an unplayed release pitch.
- Added release-only damping of secondary detuned unison strings so attack/sustain width is retained without exposing chorus/wah beating after the damper falls.
- Added spectral/RMS regressions over concert grand, studio grand and upright single notes, dyads and triads; pedal-on shared body resonance remains active.

## v1.17 S13 — Articulation Expansion

- Added `bowed.violin.modeled_articulated@1.0.0` as an opt-in eighth violin factory preset layered on the S12 realistic physical-performance path.
- Added deterministic pizzicato with pluck-position partial weighting, bounded finger transient, and free string/body decay.
- Added explicit harmonic realization metadata while keeping canonical MIDI as sounding pitch; rendering uses lighter bow/vibrato/harmonic voicing without rewriting authored pitch.
- Added detached spiccato with finite bow-contact followed by off-string/free string decay.
- Preserved ordinary arco events on the S12 path and preserved S12 rendering byte-identically when S13 articulation expansion is disabled.
- Preserved all existing S5-S12 factory presets and kept special articulation selection explicit rather than automatically inferred.


## v1.17 S12 — Violin Realism Hardening

- Added `bowed.violin.modeled_realistic@1.0.0` as an opt-in seventh violin factory preset layered on the existing S10/S11 physical-expression path.
- Added open-string vibrato suppression and slightly stronger stopped-string finger-end damping derived from violin realization state.
- Added finite same-string position-shift glide/contact transients scaled by realized position distance.
- Hardened stopped-string crossings with a slightly longer contact-transfer window and bounded incoming-string bow-force preload.
- Added deterministic same-direction bow retakes after sufficiently long gaps; S12-disabled realization remains byte-identical to `modeled_expression`.
- Preserved all existing S5-S11 presets and authored pitch/onset/duration/velocity content.


## v1.17 S11 — Expressive Phrase Modeling

- Added optional Performance IR `instrument_expression_curves` for phrase-scale bow/vibrato shaping.
- Supported controls: bow pressure, speed, contact position, bow noise, vibrato rate/depth/onset.
- Event-local instrument expression overrides phrase values control-by-control.
- No S11 curve means no new event metadata and preserves the S10 realization path.
- No new violin preset or synthesis architecture; S11 drives the existing S10 `modeled_expression` engine with authored long-range controls.


## v1.17 S10 — Violin Performance-to-Timbre Expression Hardening

- Added `bowed.violin.modeled_expression@1.0.0` as an opt-in sixth violin factory preset layered on the S8/S9 coupled physical model.
- Added deterministic microvariation of bow pressure, speed and contact point, plus attack/reversal transient shaping and vibrato-to-excitation/amplitude coupling.
- Expression hardening changes player-control trajectories only; it does not invent notes, pitch choices, rhythm, form, arrangement or orchestration.
- The hardening layer is deterministic and seeded; repeated renders with identical IR/preset are identical.
- Disabling `expression_hardening` on the new preset returns to the S9 `modeled_admittance` path byte-identically for matched note and realized-track tests.
- Preserved all S5-S9 factory presets unchanged.

## v1.17 S9R1 — Credits / Provenance Documentation

- Added root `CREDITS.md` separating research acknowledgement from bundled third-party-license obligations.
- Recorded major bowed-string/violin research and software references used across S5-S9.
- Recorded that S9 ships no third-party source code or raw measured violin asset.
- Added an explicit provenance checklist that must be satisfied before a measured asset can become a redistributable factory resource.

## v1.17 S9 — Measured Bridge-Admittance ERA Fitting

- Added a deterministic Eigensystem Realization Algorithm (ERA) fitter for explicit force-to-bridge-velocity impulse responses.
- Added `code-composer-admittance-fit` and a versioned `code-composer-bridge-admittance-era/v1` pole/residue profile contract.
- `bowed_waveguide` can consume an optional fitted response in the existing weak bridge-feedback loop while preserving the separate radiation stage.
- No named measured-violin factory preset is shipped: this slice verifies the ingestion/fitting/runtime path without fabricating unverified measurement provenance.
- Preserved the S8 `modeled_admittance` render byte-identically when no fitted response is supplied.

## v1.17 S8 — Bridge Admittance & Body Feedback Hardening

- Added `bowed.violin.modeled_admittance@1.0.0` as a separate factory preset; S5/S6/S7 presets remain unchanged.
- Added a causal modal body state with separate radiation and bridge-admittance taps.
- Added tightly bounded one-sample-delayed body velocity feedback into each physical string's bridge reflection.
- Limited factory feedback to a conservative weak-coupling region and capped authoring gain to protect stability.
- Preserved S7 `modeled_coupled` output byte-identically and preserved v1.16 A/B/C closure WAV hashes.

## v1.17 S7 — Physical String-Crossing Continuity & Coupling

- Added `bowed.violin.modeled_coupled@1.0.0` as a separate factory preset; S5/S6 presets remain unchanged.
- Added a four-string waveguide state bank for violin-realized monophonic phrases.
- Adjacent-string crossings now move bow contact over a finite overlap instead of destroying the outgoing string state.
- Released strings retain short residual bridge contribution into the common violin-body stage.
- S6 `modeled_continuous` output remains byte-identical for the same realized crossing phrase.
- Existing v1.16 A/B/C closure WAVs remain byte-identical.

## v1.17 S6 — Continuous Bowed-String State & Bow-Change Transients

- Added optional whole-track rendering to the instrument-engine boundary without changing existing engine behavior.
- Added `bowed.violin.modeled_continuous@1.0.0`; `modeled_open@1.0.0` remains the S5 note-reset preset.
- Connected S3/S4 violin bow group/direction evidence to persistent same-string waveguide state.
- Bow reversals now pass through zero signed bow velocity instead of restarting the string.
- Same-string short gaps can decay naturally; physical string changes intentionally reset state in this slice.
- Existing v1.16 A/B/C closure WAVs remain byte-identical.

## v1.17 S5 — Bowed-String Sound Hardening

- Added a new `bowed_waveguide` engine without changing the existing synthetic `bowed_string` engine.
- Added a two-segment fractional-delay string, nonlinear relative-velocity bow junction, feedback loss, explicit bridge/body modal-radiativity filtering, and subtle amplitude/spectral vibrato coupling.
- Added `bowed.violin.modeled_open` as a separate factory preset; `bowed.violin.synthetic_warm` remains unchanged.
- Added long-bow and register-sweep validation audio outside the installed Skill.
- The narrow S5 closure is sustained-bow causality/stability; continuous cross-note waveguide state and advanced bow/string physics remain future work.

## v1.17 S4 — Violin Double-Stop Realization

- Extended the S3 physical-realization planner with conservative synchronous two-note violin double stops.
- Added adjacent-string fingering search, hand-frame/position/span constraints, stopped-fifth support, shared bow contact evidence, and single↔double gesture transition planning.
- Kept S3 monophonic event realization/playability identical for the existing dogfood and preserved legacy A/B/C WAV hashes.
- Explicitly rejects triple stops, staggered overlapping voices, unequal-duration double stops, and mismatched articulation instead of silently approximating them.
- Split common fingering/transition mechanics into `performance/violin_mechanics.py` to keep the import graph acyclic.

## v1.17 S3 — Violin Performance Model

- Added deterministic monophonic violin physical-realization planning for standard tuning.
- Added contextual string/position/finger path selection with shift/string-crossing playability evidence.
- Added legato bow grouping, alternating bow direction, normalized bow usage and bow force/speed targets.
- Added strict comfort gating; challenging paths require explicit opt-in instead of being silently labeled playable.
- Preserves authored instrument expression and does not invent melody, rhythm, vibrato style, or special techniques.
- Added `code-composer-violin` CLI plus agent-facing workflow, contract, schema and surface routing.

## v1.17 S2 — Factory Preset System

- Added a small versioned factory preset registry for generic, piano, and bowed-string engines.
- Added capability/limitation metadata and an agent-facing catalog that omits raw patch values.
- Composition Brief roles may select `preset_id` plus optional exact version and song-local patch overrides.
- Presets fully materialize into canonical Music IR with exact provenance; later preset updates cannot silently change existing songs.
- Factory preset payloads are forbidden from containing notes, events, melody, rhythm, harmony/progression, form, arrangement, or MIDI content.
- Added `code-composer-presets` list/show/materialize CLI.

## S1 — Instrument Engine Extensibility (2026-09-17)

- Added a registry-routed pitched-instrument engine boundary.
- Migrated generic synth and piano render/tail/post-process/validation behind registered engines without changing existing A/B/C WAV output.
- Added a deterministic `bowed_string` family engine as the first extension dogfood.
- Added engine contracts/schema without shipping a polished violin preset in the agent Skill.
- Added explicit post-v1.16 source-change provenance so historical runtime hashes remain meaningful.

## Repository S0R1 — Canonical Skill Hygiene (2026-09-17)

- Removed persisted `kit/build/` output from the canonical installable Skill.
- Builders now exclude `build/`, `dist/`, package metadata, bytecode and cache artifacts.
- Standalone self-check rejects persistent build/dist/egg-info state inside the canonical Skill.
- Release tests validate both the canonical tree and emitted ZIP boundary.

## Repository S0 — Skill Repository Reframe (2026-09-17)

- Made `skills/code-composer/` the canonical self-contained installable product.
- Moved Python runtime into `skills/code-composer/kit/src/`.
- Added progressive-disclosure agent surfaces (`INDEX`, workflows, contracts, command/capability maps).
- Added source-inspection guard and source map.
- Added the musical-content firewall: **Examples teach operation, never taste.**
- Removed polished/reference musical examples from the installed runtime package.
- Added tiny declared-synthetic protocol fixtures only.
- Added Codex/Claude plugin adapter sources and reproducible build tooling.
- Preserved root examples/dogfood as maintainer-only regression evidence outside the installed skill.

## v1.17.0

- M1: deterministic Type 1 MIDI / collaboration export.
- M2: lossless `.ccx` internal collaboration exchange.
- M3: external delivery with reference mix, full/per-track MIDI, aligned stems and manifest.

## v1.16.0

- Expressive performance/revision closure and subsequent L0-L5 legacy cleanup baseline.
