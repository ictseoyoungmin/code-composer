# v1.17 M3 — External Delivery Hardening Closure

Status: **CLOSED**  
Release line: **Code Composer v1.17.0**  
Prior closed slices: **M1 MIDI Collaboration Export, M2 Code Composer Exchange Package**

## 1. Closure target

M3 closes the external producer/DAW handoff boundary without reopening the v1.16 composition/rendering baseline or the M2 `.ccx` internal collaboration model.

The intended two-layer collaboration model is now explicit:

```text
Code Composer ↔ Code Composer
    .ccx / canonical Music IR / provenance / handoff locks

Code Composer → external collaborator
    reference mix + MIDI + stems + resolved IR + delivery metadata
```

M3 is one-way. External MIDI/stems do not become canonical Code Composer state.

## 2. Delivered command

```bash
code-composer-delivery song.json delivery/
```

Output:

```text
delivery/
├─ reference_mix.wav
├─ <song>.mid
├─ resolved_ir.json
├─ manifest.json
├─ DELIVERY_NOTES.txt
├─ midi/
│  └─ one Type 1 MIDI file per Code Composer track
└─ stems/
   └─ one aligned 32-bit float stereo WAV per Code Composer track
```

## 3. Audio stem semantics

M3 deliberately does not claim that independently exported stems add bit-for-bit to the mastered reference. Shared buses, returns, sidechains, compressors, limiters and master processing can be nonlinear or depend on multiple sources.

Graph-mode stems contain:

```text
instrument/performance render
→ track route gain
→ track gain automation
→ track pan
→ aligned 32-bit float stereo WAV
```

Shared sends/buses/sidechains/master FX are not independently baked into every stem. `reference_mix.wav` is the authoritative sound/mix reference.

Legacy non-graph stems retain track pan and per-track insert FX; S18 defines track gain as a post-instrument/post-insert linear fader. Stems stop before the shared master stage.

32-bit float WAV prevents silent clipping/normalization of isolated pre-master sources and parsed successfully with SciPy's external WAV reader.

## 4. MIDI semantics

M1's deterministic full-song Type 1 MIDI remains unchanged. M3 adds one Type 1 file per track; each isolated file has a conductor track plus one musical track.

Preserved:

- global BPM;
- `n/4` time signature under the current quarter-note engine beat contract;
- section markers;
- onset/duration/velocity from the resolved performance state;
- GM channel 10 drum mapping;
- deterministic byte output.

Not invented:

- tempo maps — current canonical IR has one global BPM;
- arbitrary denominator — current transport stores `beats_per_bar` only;
- continuous MIDI CC lanes — no canonical CC lane exists;
- pitch bend — no canonical pitch-bend lane exists;
- General MIDI program changes — Code Composer timbre is not faithfully representable by a GM patch number.

## 5. Regression and coverage

```text
Focused M3                        10 / 10 PASS
Full regression (source)        293 / 293 PASS
Full regression (installed)     293 / 293 PASS
compileall                       PASS

Source coverage                  90.6480%
export.delivery coverage         94.4828%
app.delivery_cli coverage        96.1538%
```

## 6. Clean installed-wheel validation

Wheel:

```text
code_composer-1.17.0-py3-none-any.whl
SHA256 0189fc54b7841e45a9523af394ab06cc69f9ece1aa01976ca19f6cd543129b5e
```

The wheel was installed into a separate prefix and executed outside the source import path while using the runtime's pre-provisioned NumPy/SciPy dependencies.

Installed console entrypoints:

```text
code-composer
code-composer-collab
code-composer-compose
code-composer-delivery
code-composer-exchange
code-composer-midi
```

All six are present. `code-composer-delivery` was executed from the installed wheel and produced a complete B delivery package.

A direct fresh-venv attempt was not used as the closure environment because this container's NumPy/SciPy live in the pre-provisioned `/opt/pyvenv` environment and are not inherited by a standard nested venv. That was an environment dependency-visibility issue, not a package/runtime failure; the isolated prefix method preserves wheel isolation while using the already-declared dependencies.

## 7. External parser validation

External `mido` parsing:

```text
full B MIDI      Type 1 / 960 PPQ / 5 tracks
lead MIDI        Type 1 / 960 PPQ / 2 tracks
pad MIDI         Type 1 / 960 PPQ / 2 tracks
bass MIDI        Type 1 / 960 PPQ / 2 tracks
drums MIDI       Type 1 / 960 PPQ / 2 tracks
```

External SciPy WAV parsing of B stems:

```text
01_lead.wav    44100 Hz / float32 / stereo
02_pad.wav     44100 Hz / float32 / stereo
03_bass.wav    44100 Hz / float32 / stereo
04_drums.wav   44100 Hz / float32 / stereo
```

All stems have exactly 800,021 aligned frames in the B fixture.

## 8. v1.16 reference-render preservation

Clean-installed `code-composer-delivery` re-rendered all three v1.16 final dogfood pieces.

```text
A reference WAV
93aa85955b7aa8715b65721bc6388310be87006666cb9d7241889d66993116ba

B reference WAV
7d18321f4986c324b75e2ae45e88cc061e8409dcaa16ae0b051bf4998b368377

C reference WAV
db524b79b30fbd3d79fa97b157ddb83bb84c71d71cbf09d7c48c391aa3a3834f
```

All three are byte-identical to the v1.16 closure baseline.

## 9. M1 MIDI preservation

The M3 full-song MIDI path is the existing M1 writer, and A/B/C remain byte-identical to the M1 closure hashes:

```text
A 134a387503ef4c7e7d851bb1545e3357049e527f2f40f5eebfba8c3b625e3931
B 027486521afa5e44d5143998a6f41c5332f3c84824c9cbf268f9f061ac839d47
C 0a472f11458e3eb30214972cb766758dcda83782105947387f1caba86bd0e926
```

## 10. Architecture delta

Using the same static/import audit method on the M2 baseline and M3:

```text
                         M2      M3
Python modules           106     108
Import failures            0       0
Internal import edges     138     145
Cycles                      0       0
```

New runtime modules are only:

```text
src/code_composer/export/delivery.py
src/code_composer/app/delivery_cli.py
```

Existing M2 `src/code_composer/**/*.py` files changed: **0**.

The `pyproject.toml` delta adds only the `code-composer-delivery` console entrypoint. Documentation/status/tests are additive or status updates.

## 11. Dogfood delivery evidence

Clean-installed M3 package counts:

```text
A  2 tracks  /  9 delivery files
B  4 tracks  / 13 delivery files
C  3 tracks  / 11 delivery files
```

B per-track evidence:

```text
lead  MIDI ca7d0cddb1011be11e4f41d2c5444d0bf616d5b765b34456d83a957ad449de6b
      STEM fc38c91d16cf7f052d0246c105b1417db045b5c3ffb580c6061cc091cc942c97
pad   MIDI badf2b3f8c2565bf9097c9484d3371a396a9ca30dbcd1180fa0b4f43deb176a9
      STEM 34d43a10110a2dcb34aa064afb05d39b18c2cf8b39bb97ca1f67255a4a6d5ed0
bass  MIDI 3f9fd2c054241ef88d52d890f6d44c5bab7d5f2e396bf87fc4ab3e820ffd3816
      STEM a2fa66280ac793b0091d03214393022e97b54956d02fdf646aa116d25c67c139
drums MIDI f34c3ea3ca7a470faed5aece56d30462a4544085c2db5ee945ff30f5e079ad20
      STEM b54d3492d89cde07347455b3cfdc3526c2d0170f7c7af85e2a431e874afd8af1
```

## 12. Closure

```text
v1.17 M1 MIDI Collaboration Export        CLOSED
v1.17 M2 Code Composer Exchange Package   CLOSED
v1.17 M3 External Delivery Hardening      CLOSED

v1.17 planned collaboration/delivery chain COMPLETE
v1.16.0 historical release baseline       CLOSED / unchanged
```

Further collaboration/delivery work should open a new slice with an explicit new contract rather than silently extending M3.
