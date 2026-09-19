# Public Commands

Install first with `python -m pip install ./kit` from the skill root.

## Render

```bash
code-composer INPUT_IR.json OUTPUT.wav [RESOLVED.json] [ANALYSIS.json]
```

Validates canonical Music IR, resolves it deterministically, renders WAV, and can emit resolved/analysis JSON.

## Compose

```bash
code-composer-compose SEED_IR.json COMPOSITION_BRIEF.json OUTPUT_IR.json [PLAN.json]
```

The brief is explicit structured intent authored by the agent/user boundary. The deterministic compiler does not infer taste from prose.

## MIDI

```bash
code-composer-midi INPUT_IR.json OUTPUT.mid
```

Exports deterministic SMF Type 1. MIDI is interchange, not the sound authority.

## Collaboration bundle

```bash
code-composer-collab INPUT_IR.json OUTPUT_DIR/
```

Produces MIDI, reference mix, resolved IR and manifest.

## Internal Code Composer exchange

```bash
code-composer-exchange export INPUT_OR_WORKSPACE OUTPUT.ccx --author "NAME"
code-composer-exchange import INPUT.ccx WORKSPACE/
code-composer-exchange inspect INPUT.ccx
```

`.ccx` preserves editable canonical state, provenance, handoff intent and locks. Imports are fast-forward only; divergence is explicit rather than silently merged.

## External delivery

```bash
code-composer-delivery INPUT_IR.json OUTPUT_DIR/
```

Produces authoritative reference mix, full-song MIDI, per-track MIDI, aligned float stems, resolved IR, manifest and delivery notes.

## `code-composer-presets`

- `code-composer-presets list [--engine ...] [--family ...] [--role ...]` — list factory preset metadata without raw patch values.
- `code-composer-presets show <preset-id> [--version x.y.z]` — inspect one preset's capability metadata.
- `code-composer-presets materialize <preset-id> [...]` — output the fully materialized patch when operationally necessary.

## Violin performance realization

```bash
code-composer-violin INPUT_IR.json TRACK_ID OUTPUT_IR.json [--allow-challenging]
```

Resolves one `bowed_string` / `family=violin` track into explicit left-hand fingering and bow mechanics. S4 supports monophonic notes plus conservative synchronous adjacent-string double stops; triple stops and staggered overlapping voices remain out of scope. Default mode rejects a path that exceeds the comfortable transition/gesture threshold. `--allow-challenging` preserves the path with a playability report instead. This command does not invent melody, intervals, rhythm, or vibrato style.

## Bridge-admittance fitting

```bash
code-composer-admittance-fit BRIDGE_ADMITTANCE_IR.wav OUTPUT_PROFILE.json --order 24 [--channel 0] [--source-id ID]
```

The input is expected to be an already prepared **force-to-bridge-velocity impulse response**, not ordinary recorded violin audio. Measurement preprocessing belongs upstream and should remain explicit in provenance: repeated impact measurements may be averaged; bridge velocity should be normalized by applied force; noisy tails may be cropped; and minimum-phase conversion may be used when that is part of the measurement methodology. The fitter does not silently perform these measurement-specific steps.

The emitted `code-composer-bridge-admittance-era/v1` profile contains stable poles/residues plus fit metadata. Embed it under `bowed_waveguide_graph.body.bridge_feedback.fitted_response` when a measured mechanical response is intentionally being used. This affects mechanical bridge feedback only; radiation/microphone response remains a separate modeling problem.
