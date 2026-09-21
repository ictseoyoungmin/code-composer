# S27-I — Continuous Hi-Hat Pedal Openness / Within-note Closure

Status: **CLOSED / USER PROCEEDED TO S27-J — 2026-09-20**

## Why this slice exists

S27-H proved that a later explicit pedal/closed hit can choke a previously ringing open hi-hat. Real foot control is also continuous: a drummer can gradually bring the plates together while the original strike is still ringing, without producing a new stick hit at every intermediate openness. S27-I adds only that authored control trajectory.

## Boundary

Locked: S19 kick, S27-A2 ride/crash, S27-B hit synthesis, S27-C snare, S27-D toms, S27-F four-limb evidence, S27-G room, S27-H discrete closure events.

New: explicit `event_type: drum_control`, `control: hi_hat_pedal_openness` with normalized piecewise-linear openness points. No automatic curve generation and no genre grammar.

## Causal model

A control curve does not synthesize a new hit. It changes how quickly residual plate energy is dissipated after an accepted open/half-open source has already been struck. Openness `1.0` leaves the accepted source untouched; moving toward `0.0` increases contact loss. Low/body and high/wash regions use separate loss constants, and energy loss is cumulative, so opening the pedal again cannot resurrect energy already removed.

The control is explicit left-foot performance evidence. Other drums do not pass through the hi-hat state envelope. Shared-room processing still occurs after the stateful dry kit, allowing a short acoustic decay to remain outside the physically choked plates.

## Preset

`drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_continuous_hihat@1.0.0`

It is the S27-H patch with only `hi_hat_state.model` upgraded to `authored_continuous_openness_v2` and one `continuous` parameter block added.

## Perceptual closure gate

1. gradual open→half→closed motion must sound like progressive plate contact, not a simple volume fade;
2. closure onset must remain click-free and the waveform before authored contact must remain unchanged;
3. re-opening may lengthen remaining decay but must not bring lost energy back;
4. continuous foot motion must not duck kick/snare/tom/ride/crash;
5. discrete S27-H pedal/closed events must still work exactly as before when no continuous curve is authored;
6. room integration should leave plausible short ambience without restoring open-hat wash;
7. four-limb evidence must count the explicit pedal curve as left-foot activity and keep the authored dogfood playable.

## Engineering evidence

24 kHz / 116 BPM audition evidence:

- gradual open→closed: control-before-contact max abs diff `0.0`; late RMS S27-I/S27-H ≈ `0.1433`; 6–11 kHz late energy ≈ `0.1330` of S27-H;
- strong partial-close→reopen: pre-contact diff `0.0`; late RMS ratio ≈ `0.0672`; re-opening reduces future loss but does not restore removed energy;
- move-to-half-open and hold: pre-contact diff `0.0`; late RMS ratio ≈ `0.2994`;
- S27-H discrete open→pedal path with no continuous control remains exact (`max_abs_diff=0.0`).

Four-bar dogfood: `56` timeline events = `52` audible drum hits + `4` explicit continuous pedal controls. S27-F reports `hands=36 / right_foot=16 / left_foot=4`, `playable=true`, `strained=false`, HIGH/MEDIUM/LOW=`0/0/0`. Whole-room raw RMS is essentially level-neutral (`0.13101795` S27-H vs `0.13101792` S27-I), so the comparison is driven by residual hi-hat state rather than master-level change.

## Validation

- S27-I focused: **10/10 PASS**.
- S27-I + S27-H/G/F + factory/MIDI/pipeline focused: **78/78 PASS**.
- Full repository: **83 test files / 555/555 PASS** (partitioned to avoid environment command-duration limits).
- Standalone Skill self-check, `validate_skill`, plugin distribution, compileall, Skill/Codex/Claude build: PASS.
- Source candidate contains no generated WAV and no persistent build/cache residue.
- GitHub write: none.
