# Percussion Engine Contract

Use this contract when authoring or validating drum-kit sound design. Musical rhythm remains in explicit `event_type: "drum"` events; the percussion engine must not invent hits, fills, timing, or orchestration.

## Runtime boundary

- `kind: "percussion"` resolves to the registered `percussion` engine.
- Drum events name a kit element in `drum` and may name an explicit S20 `articulation`.
- `audio/percussion.py` owns deterministic hit synthesis.
- The engine owns authoring/runtime validation and any extended hit tail required by an enabled modeled patch.
- Existing kick/snare/closed-hat events without an articulation preserve the pre-S20 modeled sound exactly.
- Existing percussion patches without S17 realism hardening retain the legacy renderer byte-identically.

## S17 modeled acoustic-kit core

Factory preset `drums.acoustic_kit_modeled@1.0.0` enables `drum_graph.realism_hardening`.

- **Kick**: compact circular-membrane modal bank with bounded tension relaxation and a short band-limited beater impact.
- **Snare center**: membrane/body modal bank plus deterministic stochastic snare-wire collision energy.
- **Closed hi-hat**: inharmonic metallic mode cluster with velocity-sensitive high-mode excitation and decay.

## S20 articulation foundation

The same factory preset enables `drum_graph.articulation_foundation`. The runtime still renders only explicitly authored events.

| `drum` | supported `articulation` | default when omitted |
|---|---|---|
| `kick` | `default` | `default` |
| `snare` | `center`, `ghost`, `rimshot`, `cross_stick` | `center` |
| `hat` | `closed`, `half_open`, `open`, `pedal`, `choke` | `closed` |
| `ride` | `bow`, `bell`, `choke` | `bow` |
| `crash` | `crash`, `choke` | `crash` |
| `tom_high`, `tom_mid`, `tom_floor` | `center`, `edge` | `center` |

`choke` in S20 is an explicit short hand/contact articulation. It does **not** terminate a previously rendered cymbal or open hi-hat tail; shared kit state and true choke interaction remain a later state-interaction slice (currently S24 candidate).

## S21 acoustic-core realism

Factory preset `drums.acoustic_kit_modeled_realistic@1.0.0` is a separate opt-in preset. It preserves the S20 articulation surface while replacing the sparse dry core with reduced-order paired heads/cavity/shell responses for drums and dense paired inharmonic plate modes for cymbals. The S20 preset remains unchanged.

## S22 acoustic voicing & timbre polish

Factory preset `drums.acoustic_kit_modeled_polished@1.0.0` is another separate opt-in preset layered on the S21 core. `drum_graph.voicing_polish` smooths contact/body/wire integration and cymbal peakiness without adding room, overhead, reverb, microphone coloration, new hits, or performance grammar. S21 remains unchanged for exact A/B and compatibility.

## S23 performance-to-timbre dynamics

Factory preset `drums.acoustic_kit_modeled_expressive@1.0.0` is a separate opt-in preset layered on S22. Drum events may optionally author `strike_force` and `strike_position`, both normalized to `0..1`. Omitting both controls follows the exact S22 hit path. `velocity` remains musical intensity/level authority; S23 controls deterministic excitation/timbre only. `strike_position=0` denotes center/bell-side and `1` edge-side.

## Authoring rules

- Use explicit factory-preset selection or an explicit `drum_graph`; never infer a kit from genre words inside the runtime.
- Keep seeded strike variation timbral only. Timing humanization belongs to authored performance/ensemble layers.
- Use `articulation` for technique identity rather than encoding technique by abusing velocity or pan.
- Do not claim a named-kit emulation without separately licensed measurements/recordings and verified provenance.
- Presets remain musical-content-free: no drum pattern, groove, fill, or section template may be bundled in the preset.
