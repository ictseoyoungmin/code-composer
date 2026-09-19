## S24 — Cymbal Presence & Excitation Hardening (2026-09-19)

- Added opt-in `drums.acoustic_kit_modeled_cymbal_presence@1.0.0`; S23 expressive preset remains unchanged.
- Reinforced hi-hat/ride/crash modal body and metallic-contact presence rather than boosting broadband wash.
- Replaced the independent static-like wash balance with colored, plate-envelope-correlated excitation.
- Rebalanced cymbal output against kick/snare/tom while preserving authored articulation and S23 `strike_force` / `strike_position` semantics.
- Source and clean-installed regressions: 518/518 PASS across 77 test files.

## S23 — Drum Performance-to-Timbre Dynamics (2026-09-19)

- Added opt-in `drums.acoustic_kit_modeled_expressive@1.0.0`; S22 polished preset remains unchanged.
- Added normalized optional `strike_force` and `strike_position` percussion-event controls.
- Controls change deterministic excitation/timbre while event velocity remains musical intensity/level authority.
- Omitting both controls follows the S22 hit path byte-identically.
- Propagated controls through rhythm-fill validation/schema/transition realization without inventing values.
- Source and clean-installed regressions: 508/508 PASS across 76 test files.

## S22 — Drum Acoustic Voicing & Timbre Polish (2026-09-19)

- Added opt-in `drums.acoustic_kit_modeled_polished@1.0.0`; S21 realistic preset remains unchanged.
- Smoothed kick contact, snare body/wire/impact blend, tom impact/body balance, and dense cymbal modal/contact voicing.
- No room/reverb/mic model, new articulation, stateful choke, or drummer grammar added.
- 498/498 source and clean-installed regression PASS.

# Changelog

## v1.17.0 S20 — Drum Articulation Foundation (2026-09-19)

- Preserved S17/S19 kick, snare-center and closed-hi-hat defaults byte-identically.
- Added explicit snare, hi-hat, ride, crash and high/mid/floor tom articulation vocabulary without auto-generating rhythm.
- Added articulation-aware MIDI mapping and rhythm-fill propagation.
- Source and clean-installed regressions: 478/478 PASS.
- S20 choke remains a short explicit contact response; stateful muting is deferred to later kit-state work.


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
