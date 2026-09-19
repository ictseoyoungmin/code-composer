# Code Composer Kit Index

This is the progressive-disclosure entrypoint. Read only what the task requires.

## Primary surfaces

- `CAPABILITIES.md` — what the installed skill can do.
- `COMMANDS.md` — public CLI surfaces and artifacts.
- `surface.json` — machine-readable capability/entrypoint map.
- `SOURCE_MAP.md` — implementation routing; use only for source-level exceptions.
- `EXAMPLE_POLICY.md` — musical-content firewall.

## Workflows

- `workflows/compose.md`
- `workflows/select-preset.md`
- `workflows/violin-performance.md`
- `workflows/ensemble-interaction.md`
- `workflows/fit-bridge-admittance.md`
- `workflows/revise.md`
- `workflows/render-and-qa.md`
- `workflows/exchange.md`
- `workflows/midi-export.md`
- `workflows/deliver.md`

## Contracts

Read contracts only when authoring or validating that boundary:
- `contracts/composition-brief.md`
- `contracts/factory-presets.md`
- `contracts/music-ir.md`
- `contracts/performance-ir.md`
- `contracts/ensemble-interaction.md`
- `contracts/percussion.md`
- `contracts/violin-performance.md`
- `contracts/bridge-admittance-fit.md`
- `contracts/analysis-evidence.md`
- `contracts/exchange-ccx.md`
- `contracts/external-delivery.md`

Factory preset metadata is in `presets/CATALOG.json`. JSON Schemas are in `schemas/`. Empty/non-musical scaffolds are in `templates/`. Tiny protocol-only fixtures are in `fixtures/`.

## Installation

The Python package is self-contained in this directory:

```bash
python -m pip install ./kit
```

Do not look outside this skill directory for runtime code, schemas, examples, or instructions.

## Instrument extension

For instrument-family authoring or engine work, read `contracts/instrument-engines.md`; read `contracts/bowed-string.md` for the legacy synthetic engine, `contracts/bowed-waveguide.md` for modeled bow/string tasks, `contracts/plucked-bass.md` for modeled bass, or `contracts/percussion.md` for drum-kit authoring. Do not inspect `src/` for normal instrument use.
