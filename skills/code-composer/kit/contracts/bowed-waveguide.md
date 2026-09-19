# Modeled bowed-waveguide contract

Use `engine: bowed_waveguide` when the requested sound needs causal bow/string interaction rather than the older additive `bowed_string` engine.

The patch owns `bowed_waveguide_graph` with string-loop, nonlinear bow-junction, vibrato, envelope, body/radiativity and stereo/output controls. `continuous` is optional.

## Note mode

With no `continuous.enabled`, the engine renders each symbolic note independently. This preserves the S5 `bowed.violin.modeled_open@1.0.0` behavior and remains useful for isolated notes and validation.

## Continuous phrase mode

With `continuous.enabled=true`, whole-track rendering activates only when events already carry `performance.violin_realization` from the violin planner. The renderer:

- retains waveguide state across contiguous same-string notes;
- changes delay length continuously when the stopped pitch changes;
- consumes the planned bow `group_id` and `direction`;
- reverses signed bow velocity through zero over `bow_change_s` rather than restarting the string;
- preserves authored bow pressure/speed/contact-point and vibrato controls;
- lets short same-string gaps decay without reinitializing the string;
- in `modeled_continuous`, resets state when the physical string changes or the gap exceeds the configured state limit.

Unsupported polyphonic/double-stop material falls back to the ordinary per-note path.

### Coupled string-crossing mode

When `continuous.string_crossing.enabled=true`, the renderer retains independent G/D/A/E waveguide states. For adjacent-string changes it crossfades bow contact over `contact_overlap_s`, leaves the outgoing string free to decay, and mixes that residual bridge motion into the same body/radiativity stage for `residual_decay_s`. `residual_bridge_mix` controls only that residual contribution; it does not add notes or alter the violin planner. Non-adjacent jumps do not claim a physical simultaneous crossing when `adjacent_only=true`.


### Bridge-admittance/body-feedback mode

When `body.bridge_feedback.enabled=true`, the coupled multi-string renderer advances the body modes causally sample by sample. The body exposes two taps from the same modal state: a radiation output and a tightly bounded bridge-admittance velocity. The latter is fed back one sample later into each physical string's bridge reflection. `feedback_gain` controls this load strength, `max_feedback_velocity` is a hard stability bound, and `admittance_gains` weights the existing body modes without introducing musical material.

Factory preset `bowed.violin.modeled_admittance` enables this S8 path. It is a generic violin-family physical approximation, not a fitted or sampled named violin. Setting its feedback gain to zero removes the string<-body closed loop while retaining the causal body stage. Older S5/S6/S7 presets do not enable this path and retain their previous render behavior.

Factory preset `bowed.violin.modeled_coupled` enables S7 coupling. `bowed.violin.modeled_continuous` remains the S6 same-string preset and `bowed.violin.modeled_open` remains the S5 note-reset preset. Continuous double-stop waveguide state remains outside this contract. S13 special articulations are described below and are enabled only by `bowed.violin.modeled_articulated`.

Schema: `kit/schemas/bowed_waveguide.schema.json`.

## S10 expression-hardening mode

`expression_hardening.enabled=true` is an opt-in control layer. It does not alter the authored score or violin realization. It perturbs only the modeled player's bow-control trajectory in a deterministic, bounded way:

- slow pressure/speed/contact-point drift plus per-event microvariation;
- finite attack-pressure/noise transients;
- bow-reversal pressure dips/noise transients;
- vibrato coupling back into excitation pressure/energy and the existing body-output amplitude coupling.

The variation is seeded and repeatable. With the block absent or `enabled=false`, the S5-S9 paths retain their previous arithmetic. `bowed.violin.modeled_expression@1.0.0` is the factory S10 preset and is based on the S9 `modeled_admittance` physical configuration. Matched regression tests require the new preset with hardening disabled to be byte-identical to `modeled_admittance` for both isolated-note and supported realized-track rendering.

This is conservative player-control modeling, not random EQ, sample-layer variation, or a claim of reproducing a specific violinist. S10 itself does not enable special articulations; S13 adds them in a separate preset. Continuous double-stop waveguide state remains outside this contract.
## S12 violin-realism hardening mode

`realism_hardening.enabled=true` is a separate opt-in physical-technique layer used by `bowed.violin.modeled_realistic@1.0.0`. It consumes existing `performance.violin_realization` evidence instead of inventing new notes or style:

- open-string notes suppress left-hand vibrato while stopped strings retain authored vibrato;
- stopped strings receive slightly stronger finger-end damping than open strings;
- same-string position shifts use a finite pitch/contact transition scaled by the realized position distance;
- stopped-string crossings extend the contact-transfer window and preload bow force before full incoming-string motion;
- sufficiently separated bow groups may be marked as retakes, reset bow velocity off-string, then recontact through a finite attack window.

The layer is deterministic. When absent or disabled, the S5-S11 renderer arithmetic and violin realization remain unchanged; regression requires `modeled_realistic` with S12 disabled to be byte-identical to `modeled_expression` for supported realized tracks. The controls are generic violin-family mechanics, not a claim of reproducing a particular player.

## S13 articulation-expansion mode

`articulation_expansion.enabled=true` is the opt-in S13 technique layer used by `bowed.violin.modeled_articulated@1.0.0`. It is evaluated only for explicitly authored `pizzicato`, `harmonic`, or `spiccato` events. Ordinary arco events continue through the existing S12 `modeled_realistic` path.

- `pizzicato`: deterministic finger-pluck excitation with pluck-position-dependent partial weighting, a short bounded finger-noise burst, and free string/body decay after release;
- `harmonic`: canonical MIDI remains the sounding pitch; planner evidence identifies a nearby natural partial when available, otherwise a conservative artificial-fourth or modeled-sounding-pitch realization. Rendering reduces bow pressure/vibrato and shifts bow/contact voicing toward a lighter harmonic response;
- `spiccato`: finite bow contact with S12/S10 physical controls followed by an off-string/free-decay interval. This is one detached bouncing-bow gesture per authored note, not a ricochet sequence generator.

The layer is deterministic and does not compose or rewrite musical content. With the S13 block absent or `enabled=false`, the S5-S12 rendering paths are unchanged; regression requires `modeled_articulated` with S13 disabled to be byte-identical to `modeled_realistic` for supported arco rendering. Ricochet/sautillé sequence generation, col legno, explicit sul ponticello/sul tasto notation, and continuous double-stop special-articulation state remain out of scope.

