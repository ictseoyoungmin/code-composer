# Percussion Engine Contract

Use this contract when authoring or validating drum-kit sound design. Musical rhythm remains in explicit `event_type: "drum"` events; the percussion engine must not invent hits, fills, timing, or orchestration.

## Runtime boundary

- `kind: "percussion"` resolves to the registered `percussion` engine.
- Explicit drum events continue to name `kick`, `snare`, or `hat`.
- `audio/percussion.py` owns deterministic hit synthesis.
- The engine owns authoring/runtime validation and any extended hit tail required by an enabled modeled patch.
- Existing percussion patches without S17 realism hardening retain the legacy renderer byte-identically.

## Modeled acoustic-kit preset

Factory preset `drums.acoustic_kit_modeled@1.0.0` enables `drum_graph.realism_hardening`.

### Kick

A compact circular-membrane modal bank replaces the modeled preset's legacy single pitch-swept body. Authored velocity changes bounded tension-relaxation pitch movement and upper-mode excitation. The beater is a short band-limited impact, not a sustained independent tone.

### Snare

A small membrane/body modal bank is combined with deterministic stochastic snare-wire collision energy. Wire activity begins after a short coupling delay and decays independently from the initial batter-head strike. Do not replace this with a periodic amplitude LFO.

### Closed hi-hat

An inharmonic metallic mode cluster receives bounded deterministic strike variation. Velocity may increase high-mode excitation and decay length. The engine does not infer open-hat state, choke gestures, ride/crash selection, or extra cymbal hits.

## Authoring rules

- Use explicit factory-preset selection or an explicit `drum_graph`; never infer a kit from genre words inside the runtime.
- Keep seeded strike variation timbral only. Timing humanization belongs to authored performance/ensemble layers.
- Do not claim a named-kit emulation without separately licensed measurements/recordings and verified provenance.
- Presets remain musical-content-free: no drum pattern, groove, fill, or section template may be bundled in the preset.

## S19 preservation checkpoint and cymbal extension

For the preservation-first S25 path, the pre-S20 S19 repository is the drum-core checkpoint.
Factory preset `drums.s19_core_cymbal_extension@1.0.0` keeps the S19 legacy `kick`, `snare`, and closed `hat` renderer byte-identically and adds only explicit `ride` and `crash` rendering behind `drum_graph.cymbal_extension.enabled`.

- Do not route the preserved core voices through later coupled-head/cavity hardening.
- Ride uses a short stick-contact layer plus a compact inharmonic plate field. R4 keeps the R2 decay/tail locked while redistributing plate modes and wash bandwidth toward 2–6 kHz musical presence; it must not recover presence by lengthening sustain.
- Crash uses an immediate low plate response followed by bounded mid/high spectral bloom; R4 redistributes modal density toward 2–6 kHz while preserving that low-first onset and without lengthening the R2 tail. The full bright field must not appear at the first sample.
- R5 treats authored velocity as a performance/excitation signal, not only a level multiplier: soft ride timekeeping keeps the contact transient subdued, strong ride accents bring the stick tip forward, and strong crash accents open contact plus mid/high bloom nonlinearly while keeping the established decay/tail constants fixed.
- Musical-context validation should use drummer-plausible orchestration. In the R5 dogfood, a section-entry crash replaces the timekeeping cymbal on that downbeat and ride resumes on the following subdivision; this is validation evidence only, not an engine rule. The percussion engine still must not invent hits, fills, timing, or orchestration.
- Later articulation work must preserve the S19 core hashes unless that preservation checkpoint is explicitly reopened.

## S26 kit-level powerful realism / room integration

S26 does not reopen the approved S19/R5 event sources. Factory preset
`drums.s19_core_powerful_room@1.0.0` copies the R5 `kick`, `snare`, closed
`hat`, `ride`, `crash`, and `cymbal_extension` blocks exactly, then enables an
opt-in `drum_graph.kit_integration` post-process at the percussion-engine track
boundary.

The integration layer may:

- retain the dry close-kit signal as the timing/transient anchor;
- add a band-limited near-coincident overhead image with deterministic early reflections;
- excite a shared small-room field from the already-authored hit velocity, with stronger accents driving more room energy but without inventing hits;
- build the late field with a stable unitary-matrix feedback delay network whose feedback gains derive from a target RT60;
- add a zero-delay low/body reinforcement path for close kick/snare weight;
- apply gentle parallel feed-forward compression to ambient/kit branches so the initial close transient remains audible.

The integration layer must not:

- alter note/drum-event timing, velocity, orchestration, or create fills;
- replace the S19 close-core source with S21-S24 coupled-head/cavity synthesis;
- bundle or imply a measured microphone, room, named studio, or named-kit reproduction;
- recover "power" by reintroducing the rejected long tonal cymbal tail.

Validation should prioritize a drummer-plausible multi-bar performance over
isolated hit loudness. The first S26 dogfood is one 4-bar rock/pop groove at
24 kHz; dry and integrated renders use identical events/seeds and are compared
both raw and RMS-matched.

## S27-F drummer limb / performance evidence

S27-F is an analysis layer, not a percussion synthesizer. The public `analyze_drummer_performance()` function consumes already-resolved explicit drum events and returns deterministic evidence without mutating the score.

Default compact limb semantics:

- `kick*` -> right foot;
- `hat_pedal` / `hat_foot_splash` -> left foot;
- stick-driven snare/tom/hat/ride/crash -> one of two hands;
- generic crash may be assigned to the lower-travel left or right side;
- normalized kit positions are reach proxies only, not physical dimensions or audio pan.

HIGH evidence is reserved for exact limb-capacity contradictions such as more than two simultaneous stick hits or duplicate same-foot events. Fast repeats, near-simultaneous rudiments and large kit travel are MEDIUM/LOW strain evidence because rebound technique, expert motor skill and custom kit layout can extend practical limits. The runtime must never use this evidence to silently delete, requantize, revoice or otherwise repair the user's drum performance.


## S27-G shared-kit final integration

S27-G keeps the S27-D authenticated dry sources fixed and updates only `drum_graph.kit_integration`. The new preset may provide `articulation_room_weights` for explicit authored articulations and `overhead_predelay_ms` for a compact propagation cue. Presets that omit these fields retain the S26 fallback behavior.

Rules:

- room weighting may react to the authored drum articulation and velocity but must never choose an articulation or create a hit;
- dry close audio remains the zero-delay transient anchor;
- overhead propagation and shared early/late fields operate only after event synthesis;
- ghost/tight-hat events should not excite the room like rimshot/open-hat/floor-tom accents;
- integration must not lengthen the approved cymbal source decay to create artificial power;
- full-kit closure requires an S27-F-valid multi-section performance and raw plus RMS-matched listening evidence.

## S27-H authored hi-hat closure state

S27-H does not alter the accepted S27-B hi-hat hit synthesizer. The opt-in `drum_graph.hi_hat_state` layer only changes what happens *after* an open/half-open hi-hat has already been struck.

Rules:

- only later explicit authored hi-hat events may change the residual tail; the runtime never creates a pedal gesture;
- `hat_half_open` is a partial energy-damping transition, while `hat_closed`, `hat_tight_closed`, and `hat_pedal` progressively remove more of the prior open-plate energy;
- damping is applied to the prior hi-hat event before summing the kit, so kick/snare/tom/ride/crash are never globally gated;
- the newly authored closure hit itself is rendered unchanged by S27-B event synthesis;
- shared-room processing happens after the stateful source mix, so a room may retain a short acoustic decay even after the physical plates are choked;
- existing presets without `hi_hat_state.enabled` remain byte-identical;
- S27-H itself does not author continuous pedal position; S27-I adds an explicit control-event surface while automatic style grammar and inferred open/close gestures remain out of scope.


## S27-I explicit continuous hi-hat pedal openness

S27-I extends the accepted S27-H state layer with an authored performance-control event rather than inferring pedal motion from style or neighboring notes.

Control event shape:

```json
{
  "event_type": "drum_control",
  "control": "hi_hat_pedal_openness",
  "start_beat": 0.0,
  "duration_beats": 1.0,
  "points": [
    {"offset_beats": 0.0, "openness": 1.0},
    {"offset_beats": 0.5, "openness": 0.55},
    {"offset_beats": 1.0, "openness": 0.0}
  ]
}
```

Rules:

- openness is normalized `1=open`, `0=closed`; points are piecewise-linear, strictly ordered, and span the control duration;
- the control event emits no standalone audio and is owned by the left-foot performance surface;
- only already-ringing explicit `hat_open`, `hat_half_open`, or `hat_foot_splash` sources respond; unrelated kit voices bypass the control;
- contact-induced loss is cumulative: later re-opening may reduce future damping but cannot recreate plate energy already dissipated;
- body and high-frequency wash lose energy at different rates so the result is not implemented as one global gain fader;
- S27-H discrete pedal/closed events remain valid and may still provide an audible closure hit;
- MIDI export currently omits `drum_control` trajectories, so canonical Music IR is the authoritative representation for this control;
- runtime style inference, automatic pedal curves, and genre-specific hi-hat grammar remain forbidden.
