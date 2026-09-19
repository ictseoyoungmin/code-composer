# v1.17 M1 — MIDI Collaboration Export Closure

Status: **CLOSED**  
Version: **1.17.0**  
Prior release: **v1.16.0 remains CLOSED; not reopened**

## Scope

M1 adds a one-way delivery adapter after Code Composer's resolved musical state. It does not add a second composer,
does not consume analyzer evidence for mutation, and does not change the v1.16 render path.

```text
resolved / canonical Music IR
  → code-composer-midi
  → deterministic SMF Type 1

canonical Music IR
  → existing render pipeline
  → exact resolved state + reference WAV
  → code-composer-collab
  → MIDI + reference_mix.wav + resolved_ir.json + manifest.json
```

Implemented:

- Standard MIDI File Type 1
- default 960 PPQ
- conductor track with tempo, inferred `beats_per_bar/4` signature, tonal text and section markers
- one MIDI track per Code Composer track
- resolved onset, duration, pitch and velocity preservation
- same-tick note-off-before-retrigger ordering
- GM percussion channel 10: kick 36, snare 38, closed hat 42
- no automatic General MIDI program changes
- ASCII-safe MIDI meta text for cross-DAW interoperability; Unicode metadata retained in JSON manifest
- deterministic MIDI SHA256 and bundle file hashes

## CLI surface

```text
code-composer-midi <ir.json> <out.mid> [--ppq N]
code-composer-collab <ir.json> <out_dir> [--ppq N] [--stem NAME]
```

The collaboration command renders once through the existing pipeline, then exports MIDI from that exact resolved
state so the MIDI and reference WAV cannot silently diverge.

## Validation

```text
Focused M1             16 / 16 PASS
Full regression       268 / 268 PASS
Coverage               88.79% (pytest summary: 89%)
compileall              PASS
External mido parser    PASS

Static modules          103
Static import edges     132
Cycles                     0
Import failures            0

v1.16 baseline files   116 checked / 0 changed
```

The external parser opened the produced file as Type 1 / 960 PPQ, read the conductor/section markers, and observed
the drum track on zero-based MIDI channel 9 (channel 10 in user-facing numbering).

## Clean wheel validation

Wheel: `code_composer-1.17.0-py3-none-any.whl`  
SHA256: `2e1aa1141e04dc17b4eae65f705f0215eaf0ecc602ab0856730e96eb791dc300`

Installed into a separate target and executed from `/tmp`, outside the repository. Metadata version and runtime
version both reported `1.17.0`. Wheel entry points:

```text
code-composer
code-composer-compose
code-composer-midi
code-composer-collab
```

A clean-installed `code-composer-midi` converted `examples/basic/high_level_ir.json` to a valid 7-track MIDI file.

## Final dogfood collaboration bundles

| Case | MIDI SHA256 | MIDI tracks | Reference WAV compatibility |
| --- | --- | ---: | --- |
| A lyrical piano | `134a387503ef4c7e7d851bb1545e3357049e527f2f40f5eebfba8c3b625e3931` | 3 | byte-identical to v1.16 closure |
| B rhythm centered | `027486521afa5e44d5143998a6f41c5332f3c84824c9cbf268f9f061ac839d47` | 5 | byte-identical to v1.16 closure |
| C sparse chamber electronic | `0a472f11458e3eb30214972cb766758dcda83782105947387f1caba86bd0e926` | 4 | byte-identical to v1.16 closure |

All three bundles contain MIDI, `reference_mix.wav`, `resolved_ir.json`, and `manifest.json`. The reference mixes were
produced by the clean-installed v1.17 wheel and match the existing final closure WAV hashes exactly.

## v1.16 runtime preservation

`docs/maintenance/V116_RUNTIME_BASELINE.json` records every pre-M1 `src/` and `schemas/` file except the package
version declaration. M1 checks all **116 files** and found **0 changes**. New runtime code is additive under
`code_composer.export` and two CLI adapters.

Using the currently checked-in L5 fixtures, an untouched L5 tree and the clean-installed v1.17 wheel also generate
byte-identical legacy outputs:

```text
Plan      417b3fde1e5a9621668f6a8f0b7e43c6a0f64ecc37ec3a0c0f2dfbf88af61cf4
Music IR  ea6738eaa6699922f6e59b278bdcb9356d26c5bc296f914343627ceac0721526
WAV       589ac3efdc466a1a7c191caa0e614a63b1a28e4dea566b08164df3730f4490e0
```

### Historical provenance note

Closed v1.16 documents record Plan/Music IR hashes `f7f167...` and `ef60c5...`. Those two hashes cannot be reproduced
from the **current checked-in** L5 seed/brief pair even when running the untouched L5 tree itself; the recorded WAV
hash *is* reproducible. This is therefore pre-existing historical provenance/fixture drift rather than an M1 engine
regression. M1 does not rewrite the historical v1.16 documents. Direct L5→v1.17 comparison on identical current
fixtures is byte-identical for Plan, Music IR and WAV.

## Closure

```text
v1.16.0 / E0-E6 / H1-H5          CLOSED (unchanged)
Legacy Cleanup L0-L5              CLOSED (unchanged)
v1.17 M1 MIDI Collaboration Export CLOSED
```

A future collaboration feature should open a new v1.17 slice rather than widening M1.
