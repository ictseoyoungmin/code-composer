# v1.17 M3 — External Delivery Hardening

## Purpose

M3 separates **internal Code Composer collaboration** from **external DAW / producer delivery**.

- `.ccx` (M2) is lossless, provenance-aware, editable Code Composer state.
- external delivery (M3) is a one-way handoff surface for a DAW, producer, musician, or mix engineer.

The delivery package does not become a second source of composition truth and is never imported back as canonical state.

## CLI

```bash
code-composer-delivery song.json delivery/
```

Optional full-song MIDI filename and PPQ:

```bash
code-composer-delivery song.json delivery/ --stem my_song --ppq 960
```

## Delivery surface

```text
delivery/
├─ reference_mix.wav
├─ <song>.mid
├─ resolved_ir.json
├─ manifest.json
├─ DELIVERY_NOTES.txt
├─ midi/
│  ├─ 01_<track>.mid
│  ├─ 02_<track>.mid
│  └─ ...
└─ stems/
   ├─ 01_<track>.wav
   ├─ 02_<track>.wav
   └─ ...
```

### Authority split

| Artifact | Meaning |
| --- | --- |
| `reference_mix.wav` | authoritative Code Composer sound/mix reference |
| `resolved_ir.json` | exact resolved symbolic/performance state used for delivery |
| full-song MIDI | arrangement / note / timing / velocity interchange |
| per-track MIDI | isolated DAW track interchange |
| stems | time-aligned rendered source audio for external production |
| `manifest.json` | machine-readable identity, hashes, policies and track mapping |
| `DELIVERY_NOTES.txt` | human-readable import guidance and limitations |

## Stem policy

M3 does **not** claim that independently printed stems sum bit-for-bit to the mastered reference mix.
That would be incorrect when shared buses, returns, sidechains, compressors, limiters or master effects are nonlinear or depend on other tracks.

For graph-mode projects each stem is:

```text
instrument/performance render
→ track route gain
→ track gain automation
→ track pan
→ 32-bit float stereo WAV
```

Shared sends, buses, sidechains and master FX are omitted from individual stems.
Those interactions remain represented by `reference_mix.wav` and `resolved_ir.json`.

For legacy non-graph projects, track pan and legacy track insert FX are retained and S18 applies track gain as a post-instrument/post-insert linear fader, while the shared master stage is omitted.

32-bit float WAV is intentional: an isolated pre-master source may exceed 0 dBFS even when the complete mix is safe after shared processing. Float delivery preserves that headroom instead of silently clipping or normalizing the collaborator's source.

## MIDI policy

The full-song MIDI remains the deterministic M1 SMF Type 1 representation. M3 additionally exports one SMF Type 1 file per Code Composer track. Each isolated file contains:

- conductor track;
- global tempo;
- current `n/4` time-signature declaration;
- section markers;
- exactly one musical track;
- resolved note onset, duration and velocity;
- GM channel 10 mapping for drum tracks.

Code Composer timbre is not mapped to arbitrary General MIDI program numbers.

## No invented controller data

M3 exports only information represented by the current canonical contract.

Current v1.17 limitations are stated explicitly in the manifest rather than guessed:

- the canonical transport has one global BPM, not a tempo map;
- transport stores `beats_per_bar` but not a denominator, so MIDI uses `n/4` because the engine beat is a quarter note;
- there is no canonical continuous MIDI-CC lane;
- there is no canonical pitch-bend lane.

Therefore M3 does not invent tempo curves, CC automation or pitch bend.
Future canonical contracts may extend the delivery adapter without changing this boundary.

## Architecture

```text
canonical Music IR
        ↓
existing render pipeline
        ↓
reference_mix.wav + exact resolved IR
        ↓
export.delivery (one-way adapter)
   ├─ full-song MIDI (existing M1 writer)
   ├─ per-track MIDI
   ├─ aligned float stems
   ├─ delivery manifest
   └─ human delivery notes
```

`export.delivery` does not call analyzers to make musical decisions, mutate Music IR, merge `.ccx` histories, or feed external delivery files back into the engine.

## Internal vs external collaboration

```text
Code Composer ↔ Code Composer
        .ccx / M2
        canonical editable state + provenance

Code Composer → external collaborator
        delivery / M3
        reference + MIDI + stems + resolved state
```

The two boundaries are intentionally different because MIDI/stems are useful interchange formats but are lossy with respect to Code Composer's canonical synthesis, mix graph, provenance and authoring semantics.
