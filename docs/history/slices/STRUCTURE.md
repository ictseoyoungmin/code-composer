# Code Composer Repository Structure — S0

```text
code-composer/
├─ .codex_plugins/
├─ .claude_plugins/
├─ README.md
├─ CHANGELOG.md
├─ STRUCTURE.md
├─ REPOSITORY_STATUS.json
├─ docs/
├─ examples/                  # maintainer only; never bundled into the skill
├─ tests/
├─ tools/
└─ skills/
   └─ code-composer/          # canonical standalone installable skill
      ├─ SKILL.md
      ├─ VERSION
      └─ kit/
         ├─ INDEX.md
         ├─ CAPABILITIES.md
         ├─ COMMANDS.md
         ├─ SOURCE_MAP.md
         ├─ EXAMPLE_POLICY.md
         ├─ surface.json
         ├─ workflows/
         ├─ contracts/
         ├─ schemas/
         ├─ templates/
         ├─ examples/         # operation only; no finished music
         ├─ fixtures/         # tiny synthetic protocol data only
         ├─ scripts/
         ├─ pyproject.toml
         └─ src/              # implementation; read only by exception
```

The skill tree has no dependency on paths above `skills/code-composer/`.

## Canonical hygiene

Build outputs are never canonical skill content. `kit/build/`, `kit/dist/`, `*.egg-info`, bytecode and cache artifacts must not ship in standalone/plugin artifacts. Wheel/plugin builds use temporary or release staging locations.

## S1 instrument-engine boundary

Pitched instruments resolve through `kit/src/code_composer/audio/engines/registry.py`. The central renderer knows only the engine interface: note render, optional stateful whole-track render, tail, optional track post-process and engine-owned validation. Built-ins are `generic`, `piano`, `bowed_string`, and `bowed_waveguide`. New instrument families must extend through the registry rather than adding family-specific branches to `render.py`.

S1 originally kept polished presets outside the installed Skill while the engine boundary was being proven. S2 supersedes that temporary restriction: the installed Skill may ship a small factory preset library as versioned **sonic resources**, provided presets contain no notes, rhythms, chords, progressions, form, arrangement, MIDI, or completed musical material.

## S2 preset boundary

`skills/code-composer/kit/presets/CATALOG.json` is the agent-facing metadata catalog. Runtime versioned preset payloads live under the installed Python package resources and are accessed through `code_composer.presets`; normal composition should not inspect those low-level files.

## S3/S4 violin performance boundary

`kit/src/code_composer/performance/violin.py` is the public violin realization surface. Shared conventional-violin mechanics live in `violin_mechanics.py`; synchronous adjacent-string double-stop planning lives in `violin_double_stop.py`. S3 monophonic event realization remains byte-stable at the planning-evidence level. S4 dispatches to the double-stop planner only when two pitches share an onset.

S4 is deliberately conservative: at most two simultaneous pitches, adjacent strings, equal duration, shared articulation, no staggered overlap, and no silent rewriting of notes or intervals. Triple/quadruple stops, rolled chords, harmonics, pizzicato/arco switching, scordatura and notation export remain outside this slice.

## S5 bowed-string sound boundary

`bowed_string` remains the stable additive/synthetic family engine. `bowed_waveguide` is a separate physically-inspired two-segment string model with a nonlinear bow junction and body-radiativity filter. The modeled factory preset is a sonic starting point only and carries no composition content. S5 closes sustained-note causality/stability, not continuous legato state across note events.


## S6 continuous bowed-state boundary

`bowed.violin.modeled_continuous` enables the `bowed_waveguide` whole-track path. The waveguide state persists only for supported same-string violin realization, while bow group/direction controls come from S3/S4 planning. `modeled_open` remains the S5 note-reset preset. Unsupported double-stop/polyphonic state continuity falls back rather than being silently approximated.

## S7 physical string-crossing boundary

`bowed.violin.modeled_coupled` activates a multi-string state bank inside the existing `bowed_waveguide` engine. Physical G/D/A/E waveguide memories survive string changes; adjacent crossings use a finite bow-contact overlap and the released string contributes a short decaying bridge residual into the shared body/radiativity stage. S7 remains monophonic at the continuous renderer boundary and does not claim continuous double-stop physics or a full finite-element body-feedback model.


## S8 bridge-admittance/body-feedback boundary

`bowed.violin.modeled_admittance` retains the S7 four-string/crossing path but advances the violin-body modes causally sample by sample. The same modal state supplies radiation output and a separately weighted, tightly bounded bridge-admittance velocity that is returned one sample later into the physical-string bridge reflection. This creates weak string↔body feedback without replacing the stable S5/S6/S7 presets. The model is a generic violin-family approximation, not a fitted named instrument or finite-element body simulation.

## S9 measured bridge-admittance fitting boundary

`kit/src/code_composer/audio/bridge_admittance_fit.py` converts an explicitly supplied mechanical bridge-admittance impulse response into a compact ERA pole/residue profile (`code-composer-bridge-admittance-era/v1`). `bowed_waveguide` may consume that profile only inside the weak mechanical bridge-feedback path. The existing radiation/body output model remains separate because bridge input admittance is not a microphone/radiation transfer function. S9 intentionally ships no named measured-instrument preset until the source measurement identity and redistribution provenance are independently verified.
