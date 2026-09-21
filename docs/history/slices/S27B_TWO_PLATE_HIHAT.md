# S27-B — Two-Cymbal Hi-Hat Mechanics

Status: CLOSED / PERCEPTUAL PASS
Date: 2026-09-20
Baseline: S19 preserved kick/snare/legacy closed-hat + S27-A2 dense cymbal plate field

## Problem

The existing canonical `hat` is one metallic voice. It cannot represent the defining mechanics of a hi-hat: a top cymbal, a bottom cymbal, pedal-controlled separation/contact, repeated edge collisions, and distinct stick/foot articulations. Simply changing decay/gain for `closed/open` would not be a hi-hat model.

## Research anchor

Shu Sekiguchi and Toshiya Samejima, “Physical modeling and sound synthesis of the hi-hat,” *Acoustical Science and Technology*, 44(5), 352–359, 2023, DOI `10.1250/ast.44.352`. The paper models two cymbals and explicitly studies cymbal–cymbal collision with spring and algorithmic inelastic-collision models. S27-B uses that causal picture only; no paper code, mesh, FDM solver, measurement, or audio is copied.

## Preservation rule

- `kick`, `snare`, legacy `hat`, `ride`, and `crash` event rendering remain byte-preserved between the S27-A2 preset and the S27-B preset.
- The approved S19 legacy closed-hat remains the compatibility anchor.
- The new model is opt-in through explicit hi-hat articulations.

## New authored articulation surface

- `hat_tight_closed`
- `hat_closed`
- `hat_half_open`
- `hat_open`
- `hat_pedal`
- `hat_foot_splash`

MIDI export maps closed/tight to note 42, half/open to 46, and pedal/splash to 44 while preserving the richer authored articulation inside Code Composer.

## Compact causal model

Each articulation renders:

`stick/foot force -> top plate + transferred bottom plate -> inelastic edge-collision texture -> state-dependent damping`

Top and bottom plates use distinct deterministic dense inharmonic fields rather than one pitch-shifted copy. Pedal state controls separation/contact indirectly through bottom transfer, decay, collision duration/density, and contact losses. Collision times are seeded but aperiodic so the interaction reads as rattle/chatter rather than another stable metallic pitch.

## State behavior

- **tight_closed**: strongest damping and shortest collision field.
- **closed**: preserves a strong S19-like stick authority while retaining a small amount of two-plate motion.
- **half_open**: longer repeated edge interaction and obvious rattle/chatter.
- **open**: plates radiate more independently, collision density drops, and the tail extends.
- **pedal_chick**: foot-driven plate collision with very short decay.
- **foot_splash**: foot-driven collision/release with a longer plate tail.

## Preservation-first retune

The first two-plate candidate was rejected internally because `hat_closed` onset was only about half the S19 legacy anchor. The model was retained but tight/closed gain/contact/decay were retuned. At 24 kHz, velocity 0.78, seed 17:

- legacy closed overall RMS: ~0.00645
- S27-B closed overall RMS: ~0.00617 (~96%)
- legacy first-20-ms RMS: ~0.01670
- S27-B first-20-ms RMS: ~0.01399 (~84%)

This is now regression-protected so additional physics cannot silently repeat the S20–S24 “more detail, less authority” failure.

## Closure gate

S27-B may close only if listening confirms all of the following:

1. `hat_closed` is not perceptually weaker than the approved S19 closed-hat anchor.
2. tight/closed/half-open/open sound like different contact/separation states of one two-cymbal instrument, not gain/decay presets.
3. half-open contains convincing irregular edge chatter.
4. open has an independent plate tail without bell-like ringing or the old long tonal smear.
5. pedal chick and foot splash are recognizably distinct foot gestures.
6. an actual 8-beat groove benefits from the state changes; solo-hit metrics alone cannot close the slice.
7. S19 kick/snare/legacy-hat source preservation and existing ride/crash behavior remain intact.

## Deferred

- continuous within-note pedal trajectory
- choke transition that modifies an already-ringing open hat in stateful time
- full drummer limb/foot occupancy validation
- genre-specific hi-hat performance grammar

Those belong to later performance/state slices rather than being hidden inside S27-B.


## Closure

- User listening gate passed on 2026-09-20.
- S27-B is now the accepted hi-hat articulation foundation for subsequent drum-authenticity slices.
- Existing legacy `hat` compatibility remains preserved; continuous pedal trajectory and stateful close/choke remain deferred rather than silently folded into this closure.
