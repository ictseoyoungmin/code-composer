# Capabilities

| Capability | Purpose | Public surface |
|---|---|---|
| Render | Validate and render canonical Music IR | `code-composer` |
| Compose | Compile an explicit Composition Brief into Music IR | `code-composer-compose` |
| MIDI export | Export resolved/canonical note events to deterministic Type 1 MIDI | `code-composer-midi` |
| Collaboration bundle | MIDI + reference WAV + resolved IR + manifest | `code-composer-collab` |
| Internal exchange | Lossless `.ccx` checkpoint/handoff between Code Composer users | `code-composer-exchange` |
| External delivery | Reference mix + full/per-track MIDI + aligned float stems + manifest | `code-composer-delivery` |
| Analysis/QA | Produce evidence used by an agent to decide explicit revisions | Python analysis modules / render artifacts |
| Factory presets | Select/version/materialize sonic starting points without compositional content | `code-composer-presets` / `presets/CATALOG.json` |
| Violin performance realization | Plan monophonic violin and conservative synchronous double-stop string/position/finger/bow mechanics without inventing composition content | `code-composer-violin` |
| Bridge-admittance fitting | Fit an explicit measured force-to-bridge-velocity impulse response into a compact deterministic ERA profile for bowed-waveguide mechanical feedback | `code-composer-admittance-fit` |

Code Composer does not use bundled musical examples to choose style or content. Musical decisions remain agent/user/context driven.

| Instrument engines | Registry-routed deterministic pitched-instrument engines; current built-ins: generic, piano, bowed_string, bowed_waveguide, plucked_bass, percussion | `contracts/instrument-engines.md` |

## Factory preset system

Code Composer ships a small versioned factory preset catalog for sonic starting points. Presets expose capability/limitation metadata, support deterministic song-local overrides, and materialize completely into Music IR so future preset updates cannot silently change existing songs. Presets contain no compositional material.

## Modeled bowed-string sound

`bowed_waveguide` provides a causal sustained-bow path with a two-segment digital waveguide, nonlinear bow/string interaction and explicit body-radiativity modes. The `modeled_continuous` preset additionally preserves supported same-string waveguide state across violin-realized note boundaries and consumes planned bow-direction changes. `modeled_coupled` extends this with multi-string state retention, finite adjacent-string bow-contact transfer and short bridge/body residual coupling across crossings. `modeled_admittance` further advances the body modes causally and returns a tightly bounded modal bridge-admittance velocity into the string reflection path. `modeled_expression` is an opt-in S10 layer on the same coupled/admittance path; it adds deterministic bow-control microvariation, attack/bow-change irregularity and vibrato-coupled excitation without changing authored musical content. `modeled_realistic` is the S12 opt-in extension: it consumes violin-realization state to distinguish open/stopped strings, harden finite position shifts and string crossings, and model bow retakes after sufficiently long gaps. `modeled_articulated` is the S13 opt-in extension: it preserves the S12 arco path and adds explicit pizzicato, harmonic and spiccato rendering when those articulations are already authored. The older `bowed_string` engine remains available for its synthetic/additive character and backward compatibility.


## S17/S20/S21/S22/S23 percussion acoustic fidelity, articulation, core realism, voicing polish and performance timbre

`percussion` is an explicit instrument-engine boundary for drum-event validation/tails while preserving explicit drum-event musical authority. Factory preset `drums.acoustic_kit_modeled` is an opt-in generic acoustic-kit approximation. S17 established the physical core: bounded struck-membrane kick modes, snare membrane/body plus deterministic wire-rattle energy, and an inharmonic closed hi-hat whose brightness/decay react to authored velocity. S20 preserves those default kick/snare/closed-hat sounds byte-identically and adds explicit authored articulation vocabulary: snare center/ghost/rimshot/cross-stick; hi-hat closed/half-open/open/pedal/choke-contact; ride bow/bell/choke-contact; crash/choke-contact; and high/mid/floor tom center/edge. Seeded variation remains timbral only; the runtime does not invent hits, fills, timing, or sticking. S20 choke is an independent short contact response, not stateful muting of a previously ringing cymbal/hat. S21 adds the separate opt-in `drums.acoustic_kit_modeled_realistic` dry core with paired-head/cavity/shell drum coupling and dense cymbal modes. S22 adds `drums.acoustic_kit_modeled_polished`, applying dry-source contact/body/wire and cymbal voicing polish while leaving S21 unchanged. S23 adds `drums.acoustic_kit_modeled_expressive`; optional authored `strike_force` and `strike_position` change excitation/timbre while omission follows the byte-identical S22 hit path. `velocity` remains musical intensity authority. True shared-state choking remains a later state-interaction concern. The legacy percussion renderer remains byte-identical when realism hardening is absent or disabled. See `contracts/percussion.md`.

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


## S24 cymbal presence & excitation hardening

`drums.acoustic_kit_modeled_cymbal_presence@1.0.0` is an opt-in S24 percussion preset layered on S23 expressive dry-source semantics. It reinforces cymbal modal/body energy and metallic contact, colors the broadband wash, and amplitude-couples that wash to plate modal motion so it does not read as an independent static-noise tail. Kick/snare/tom rendering is byte-identical to S23 for the same authored controls. Room/reverb/mic coloration and stateful choke remain out of scope.
