# MIDI Collaboration Export — v1.17 M1

Status: **CLOSED**

## Purpose

Make Code Composer output easy to hand to a musician, producer, or DAW user without turning MIDI into a
second composition engine. v1.16 remains the source-of-truth composition/performance pipeline.

## Canonical flow

```text
Composer Agent / explicit Music IR
  → deterministic Code Composer resolution
  → resolved note-event graph
     ├─ existing WAV renderer → reference_mix.wav
     └─ one-way MIDI adapter  → Type 1 .mid
                                + resolved_ir.json
                                + manifest.json
```

## MIDI contract

- Standard MIDI File format: Type 1
- Default resolution: 960 PPQ
- Track 0: conductor metadata
  - tempo
  - time signature as `beats_per_bar/4`
  - tonal description text
  - form section markers
- One subsequent MIDI track per Code Composer track
- Pitched events preserve resolved `start_beat`, `duration_beats`, `midi`, and `velocity`
- Percussion uses MIDI channel 10
  - kick → 36
  - snare → 38
  - closed hat → 42
- Note-off is ordered before same-tick retriggered note-on
- Program changes are intentionally omitted

## Why no automatic General MIDI instrument mapping

Code Composer patches describe its own deterministic synth, acoustic/electric piano, percussion and mix DSP.
A General MIDI program number would imply a sound equivalence that does not exist. The `.mid` file therefore
carries arrangement/performance interchange, while the WAV is the authoritative sound reference. Patch identity
and piano design metadata are retained in `manifest.json`.

## Time-signature limitation

The v1.16 transport contract stores `beats_per_bar` but not a denominator. Code Composer's beat unit is a quarter
note, so M1 exports the MIDI signature as `beats_per_bar/4` and records that inference in the manifest. A future
transport contract may make numerator/denominator explicit without changing the M1 writer contract.

## Collaboration bundle

`code-composer-collab` writes:

```text
<sanitized-title>.mid
reference_mix.wav
resolved_ir.json
manifest.json
```

The command invokes the existing render pipeline once, then exports MIDI from that exact resolved state. This
prevents the reference WAV and MIDI from being generated from different musical states.

## Architectural boundary

The exporter is one-way and additive. It must not:

- infer new composition material;
- consume analyzer evidence to mutate music;
- alter v1.16 arrangement/performance/render behavior;
- claim Code Composer DSP can be reconstructed from MIDI;
- become an alternate canonical IR.

## Compatibility baseline

The pre-feature v1.16 runtime/schema tree remains recorded by the closed L4/L5 evidence. Because future versions
necessarily add runtime modules, M1 adds `docs/maintenance/V116_RUNTIME_BASELINE.json`: hashes of all pre-M1
`src/` and `schemas/` files except the package version declaration. Tests require those files to remain byte-identical.
