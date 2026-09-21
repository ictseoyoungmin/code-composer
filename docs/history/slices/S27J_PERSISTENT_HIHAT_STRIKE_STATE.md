# S27-J — Persistent Hi-Hat Pedal State / Strike Coupling

Status: **CLOSED / USER PERCEPTUAL PASS — 2026-09-20**

## Why this slice exists

S27-I made an authored `hi_hat_pedal_openness` curve continuously dissipate energy from an already-ringing open/half-open hi-hat. One causal gap remained: when that curve ended before a later stick strike, its final pedal position was forgotten by the strike source. A later authored `hat_open` therefore began from the fully-open S27-B excitation even if the drummer's foot was still holding the plates half-closed.

S27-J closes only that persistent-state / strike-coupling gap.

## Boundary

Locked: S19 kick, S27-A2 ride/crash, S27-B two-plate source family, S27-C snare articulations, S27-D tom family, S27-F evidence-only limb validator, S27-G shared room, S27-H discrete choke, S27-I continuous residual-energy loss.

New: completed pedal curves leave a persistent openness state, and later stick-driven hi-hat strikes inherit that state at their excitation time.

No genre grammar, no automatic foot motion, no hidden control generation, no commercial hi-hat emulation.

## Causal model

`hi_hat_pedal_openness` remains an explicit Composer-Agent-authored left-foot control (`1=open`, `0=closed`). S27-J resolves that control at the exact stick-strike beat. For stick-driven tight/closed/half/open articulations, pedal state may only close the physical separation relative to the articulation's natural maximum; it cannot force an authored closed hit more open.

The accepted S27-B state parameter sets are used as anchor points. `plate_decay_s`, bottom-plate transfer, collision duration/density, plate/contact gains and output response are continuously interpolated by effective openness. This changes the actual two-plate excitation/contact response, not only a post-hit fader.

Already-dissipated energy remains causal: later reopening changes future strike state and future loss, but does not recreate energy removed from an earlier ringing hit.

S27-J also makes non-audio `drum_control` events RNG-neutral for the new preset: inserting a pedal curve must not silently change the random identity of a later unrelated drum hit merely because its raw timeline index changed. Older presets retain their historical seed contract.

## Preset

`drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_persistent_hihat@1.0.0`

The preset is copied from S27-I. The only engine-semantic upgrade is `hi_hat_state.model = authored_persistent_openness_v3`; the S27-B mechanics anchors, S27-H closure block and S27-I continuous loss constants are preserved.

## Research / provenance

S27-J continues the same independent causal interpretation of Sekiguchi & Samejima (2023), *Physical modeling and sound synthesis of the hi-hat*, DOI `10.1250/ast.44.352`: two cymbals, stick impact, and cymbal-cymbal contact/collision are treated as one physical system. No paper code, FDM solver, geometry, numerical parameter table, mesh, audio, measurement or fitted commercial instrument data is copied or bundled. `CREDITS.md` records the provenance policy.

## Perceptual closure gate

1. a completed pedal curve must audibly persist into a later hi-hat stick strike;
2. open → half → near-closed persistent states must change strike/contact/decay as one physical hi-hat, not as post-hit volume presets;
3. adding a control before a hit must not change unrelated drum RNG identity or duck other kit voices;
4. a pedal state more open than an authored closed/tight articulation must not force that hit open;
5. no-control S27-I renders must remain byte-exact;
6. future S27-I-style continuous closure after a strike must remain click-free and preserve pre-contact audio;
7. shared-room integration must preserve the state distinction without creating a level-comparison illusion.

## Engineering evidence

24 kHz / 116 BPM dogfood:

- representative completed curve: openness `1.0 → 0.22`, curve ends before later `hat_open` strike;
- late RMS of the later strike: S27-J/S27-I ≈ `0.1320` in the isolated persistence probe;
- no-control S27-I → S27-J track render: byte-exact;
- direct hit API with no state override: byte-exact to S27-I;
- persistent pedal-state resolver is piecewise-linear during a curve and holds the final point after curve end;
- control event insertion is RNG-neutral for later audible S27-J hits;
- four-bar room dogfood: `48` timeline events = `43` audible hits + `5` explicit pedal controls;
- S27-F: `hands=28 / right_foot=15 / left_foot=5`, `playable=true`, `strained=false`, HIGH/MEDIUM/LOW=`0/0/0`;
- whole-room raw RMS: S27-I `0.13491873` / S27-J `0.13498884`, RMS-match gain `0.99948062`.

## Validation

- S27-J focused: **10/10 PASS**.
- S27-J + S27-I/H/G/F/B + factory/MIDI focused: **80/80 PASS**.
- Full repository validation: **84 test files / 565/565 PASS** (partitioned to avoid environment command-duration limits).
- Standalone Skill self-check, `validate_skill`, plugin distribution, compileall, Skill/Codex/Claude builds: PASS.
- GitHub write: none.
