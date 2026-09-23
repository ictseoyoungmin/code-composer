# Capabilities

| Capability | Purpose | Public surface |
|---|---|---|
| Render | Validate and render canonical Music IR | `code-composer` |
| Song contract (CR01) | Validate seedless Composer-first Song state and exact authored fingerprint | `code-composer-song` |
| Compose (pre-refactor path) | Compile an explicit Composition Brief into Music IR | `code-composer-compose` |
| MIDI export | Export resolved/canonical note events to deterministic Type 1 MIDI | `code-composer-midi` |
| Collaboration bundle | MIDI + reference WAV + resolved IR + manifest | `code-composer-collab` |
| Internal exchange | Lossless `.ccx` checkpoint/handoff between Code Composer users | `code-composer-exchange` |
| External delivery | Reference mix + full/per-track MIDI + aligned float stems + manifest | `code-composer-delivery` |
| Analysis/QA | Produce evidence used by an agent to decide explicit revisions | Python analysis modules / render artifacts |
| Factory presets | Select/version/materialize sonic starting points without compositional content | `code-composer-presets` / `presets/CATALOG.json` |
| Violin performance realization | Plan monophonic violin and conservative synchronous double-stop string/position/finger/bow mechanics without inventing composition content | `code-composer-violin` |
| Bridge-admittance fitting | Fit an explicit measured force-to-bridge-velocity impulse response into a compact deterministic ERA profile for bowed-waveguide mechanical feedback | `code-composer-admittance-fit` |

Code Composer does not use bundled musical examples to choose style or content. Musical decisions remain agent/user/context driven.

## S29 thematic arc / cross-section motif lineage

The Composition Brief may carry explicit agent-authored motif variants and assign them to formal sections. The engine does not invent or select variants: it validates complete authored interval/rhythm material, measures structural identity against the canonical motif, enforces only an explicit hard minimum, routes the selected material through the existing deterministic arranger, and exposes section/event lineage evidence for QA. This lets repeated formal material develop recognizably without relying only on density/register changes.


## S31 destination-bound transition lineage

Performance IR harmonic anticipation can keep its historical explicit `target_degree` or, alternatively, use an explicit `arrival_binding` that points to `destination_progression` plus a concrete progression index. The runtime requires an S30 destination progression variant, validates the index, resolves the referenced scale degree, and writes lineage evidence to the realized transition event/report. It never chooses a cadence, progression, or index automatically.

| Instrument engines | Registry-routed deterministic pitched-instrument engines; current built-ins: generic, piano, bowed_string, bowed_waveguide, plucked_bass, percussion | `contracts/instrument-engines.md` |

## Factory preset system

Code Composer ships a small versioned factory preset catalog for sonic starting points. Presets expose capability/limitation metadata, support deterministic song-local overrides, and materialize completely into Music IR so future preset updates cannot silently change existing songs. Presets contain no compositional material.

## Modeled bowed-string sound

`bowed_waveguide` provides a causal sustained-bow path with a two-segment digital waveguide, nonlinear bow/string interaction and explicit body-radiativity modes. The `modeled_continuous` preset additionally preserves supported same-string waveguide state across violin-realized note boundaries and consumes planned bow-direction changes. `modeled_coupled` extends this with multi-string state retention, finite adjacent-string bow-contact transfer and short bridge/body residual coupling across crossings. `modeled_admittance` further advances the body modes causally and returns a tightly bounded modal bridge-admittance velocity into the string reflection path. `modeled_expression` is an opt-in S10 layer on the same coupled/admittance path; it adds deterministic bow-control microvariation, attack/bow-change irregularity and vibrato-coupled excitation without changing authored musical content. `modeled_realistic` is the S12 opt-in extension: it consumes violin-realization state to distinguish open/stopped strings, harden finite position shifts and string crossings, and model bow retakes after sufficiently long gaps. `modeled_articulated` is the S13 opt-in extension: it preserves the S12 arco path and adds explicit pizzicato, harmonic and spiccato rendering when those articulations are already authored. The older `bowed_string` engine remains available for its synthetic/additive character and backward compatibility.


## S17 percussion acoustic fidelity

`percussion` is now an explicit instrument-engine boundary for drum-event validation/tails while preserving the existing drum-event Music IR surface. Factory preset `drums.acoustic_kit_modeled` is an opt-in generic acoustic-kit approximation. Its kick uses bounded struck-membrane modes with velocity-dependent tension relaxation and band-limited beater impact; its snare combines membrane/body modes with deterministic stochastic wire-rattle energy; its closed hi-hat uses inharmonic metallic modes whose brightness and decay react to authored velocity. Seeded strike variation changes physical timbre without changing timing or inventing new hits. The legacy percussion renderer remains byte-identical when realism hardening is absent or disabled. See `contracts/percussion.md`.

## S26 drum-kit powerful realism / room integration

`drums.s19_core_powerful_room` preserves the S19/R5 event sources and adds an opt-in percussion track post-process rather than a new drum synthesizer. The layer combines the dry close kit with a band-limited overhead image, deterministic small-room early reflections, a four-line feedback-delay-network late field, authored-velocity-dependent room excitation, low/body reinforcement and gentle parallel feed-forward bus glue. It makes no musical decisions and bundles no measured room/microphone assets. See `contracts/percussion.md`.

## S27-F drummer limb / performance validation

`analyze_drummer_performance(resolved_ir)` adds evidence-only four-limb feasibility analysis for authored drum events. It maps kick to right foot, hi-hat pedal/splash to left foot, and stick-driven drum/cymbal events across two deterministic hand assignments. Exact simultaneous limb-capacity contradictions are reported separately from demanding repeat-rate or cross-kit-travel evidence. The analyzer does not delete hits, rewrite timing, infer fills, or alter sound synthesis. When render analysis is requested, the pipeline includes this report automatically for resolved drum events.

## S27-G authenticated full-kit integration

`drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated` preserves every S27-D dry event source and changes only the shared kit recording layer. The integration understands explicit hi-hat/snare/tom articulation names when calculating room excitation, adds an optional small overhead propagation delay, emphasizes compact early reflections over late wash, and uses lighter body/bus parallel processing so the close transient remains the anchor. No hit, timing, velocity, sticking or orchestration is invented.

## S16 plucked bass acoustic fidelity

`plucked_bass` is a dedicated deterministic electric-bass engine rather than the previous generic sine/triangle support patch. Factory preset `bass.electric_finger_modeled` shapes its harmonic bank from authored pluck/pickup position, bounded inharmonicity and frequency-dependent damping, then adds a low-level deterministic finger transient and pickup-bandwidth stage. Existing bass pitch-approach plus attack/release performance controls remain compatible. The preset is a generic fingerstyle capability resource; it does not claim to reproduce a named bass, pickup, amplifier or player. See `contracts/plucked-bass.md`.

## Articulation expansion

S13 adds explicit `pizzicato`, `harmonic`, and `spiccato` vocabulary through `bowed.violin.modeled_articulated`. Pizzicato uses a deterministic pluck excitation followed by free string/body decay. Harmonic events keep canonical MIDI as the sounding pitch while the violin planner attaches natural-harmonic evidence where a standard partial is close, otherwise a conservative artificial-fourth or modeled-sounding-pitch descriptor. Spiccato uses a finite bouncing-bow contact window followed by free string decay. The layer does not rewrite pitch, rhythm, harmony, form, or orchestration, and ordinary arco events continue through the S12 continuous/realism path.

## Violin realism hardening

S12 does not infer a new melody or performance style. It reads the existing violin realization and applies bounded deterministic player-mechanics detail only when `bowed.violin.modeled_realistic` is selected. The planner can mark separated groups as same-direction retakes; the physical renderer uses the realized finger/string/position transition state for open-string vibrato suppression, stopped-string damping, finite position-shift glide/contact transients, and stopped-string crossing force transfer.

## Expressive phrase modeling

S11 extends Performance IR with optional `instrument_expression_curves`. The agent can author a long-range bow/vibrato arc over a phrase while retaining the existing dynamic/timing/gate/articulation curves. The performance resolver interpolates those controls at note onsets; event-local expression remains higher priority, and absent S11 curves leave the S10 path unchanged. This is an explicit authoring surface, not an automatic style or emotion inference system.

## Measured bridge-admittance fitting

S9 can fit a provided mechanical bridge-admittance impulse response into a compact ERA pole/residue profile. The profile drives the mechanical feedback path only; it is not treated as a microphone/radiation impulse response and does not by itself identify or emulate a named violin. No measured factory preset is bundled unless the source measurement and redistribution provenance are explicitly verified.

## Ensemble interaction realism

S15 adds an explicit deterministic ensemble-performance layer after phrase/orchestration realization. Per section, the composing agent may name a `leader_role`, assign bounded per-role timing offsets, and specify overlap velocity scales for support roles. Support yielding is proportional to actual note/leader overlap rather than a whole-section gain reduction. Song-level role pan offsets add to existing mix positions. The layer does not invent notes, alter harmony/form, select instruments, or infer a leader automatically. If S15 surfaces are absent or disabled, the pre-S15 IR is preserved.

## S27-H stateful hi-hat closure

`drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_stateful_hihat` preserves S27-G hit synthesis and shared-room settings, then adds one opt-in time-domain state layer. A later authored `hat_half_open`, `hat_closed`, `hat_tight_closed`, or `hat_pedal` event may dissipate energy from an already-ringing `hat_open`/`hat_half_open` source. The transition is applied only to that earlier hi-hat event before kit summing; it is not a global track gate and it never invents pedal motion or groove events. Continuous pedal trajectories remain deferred.

## S27-I continuous hi-hat pedal openness

`drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_continuous_hihat` preserves the accepted S27-H hit sources, discrete closure behavior, and S27-G shared room, then accepts explicit `drum_control` / `hi_hat_pedal_openness` curves. The curve is a left-foot authored performance surface, not an inferred groove rule. It continuously changes the loss rate of an already-ringing open/half-open plate with separate body/wash damping and never gates the rest of the kit.
