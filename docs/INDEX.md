# Code Composer documentation

Start with the root [`README.md`](../README.md) if you are new to Code Composer.

## Current pre-release rebuild

- [`architecture/CR00_COMPOSER_REBUILD_BOUNDARY.md`](architecture/CR00_COMPOSER_REBUILD_BOUNDARY.md) — authoritative breaking-rebuild boundary.
- [`maintenance/CR00_PRE_REFACTOR_FREEZE.json`](maintenance/CR00_PRE_REFACTOR_FREEZE.json) — machine-readable KEEP / REBUILD / DELETE / evidence freeze.
- The existing v1.16/S29–S31 CompositionBrief architecture is historical for CR01+ authoring design; validated runtime/DSP remains reusable.

## Use Code Composer

- [`../skills/code-composer/kit/COMMANDS.md`](../skills/code-composer/kit/COMMANDS.md) — command-line interfaces.
- [`../skills/code-composer/kit/CAPABILITIES.md`](../skills/code-composer/kit/CAPABILITIES.md) — public capability overview.
- [`../skills/code-composer/kit/contracts/`](../skills/code-composer/kit/contracts/) — runtime and musical contracts.
- [`../skills/code-composer/kit/schemas/`](../skills/code-composer/kit/schemas/) — canonical schemas.
- [`../skills/code-composer/kit/presets/`](../skills/code-composer/kit/presets/) — factory-preset metadata.

## Agent skill

- [`../skills/code-composer/SKILL.md`](../skills/code-composer/SKILL.md) — canonical agent-skill entry point.
- [`../skills/code-composer/kit/INDEX.md`](../skills/code-composer/kit/INDEX.md) — progressive-disclosure routing.
- [`../skills/code-composer/kit/EXAMPLE_POLICY.md`](../skills/code-composer/kit/EXAMPLE_POLICY.md) — musical-content firewall.
- [`../skills/code-composer/kit/SOURCE_MAP.md`](../skills/code-composer/kit/SOURCE_MAP.md) — source map for implementation work.

## Develop and package

- [`BUILD.md`](BUILD.md) — build, packaging, wheel, skill, and plugin flow.
- [`STRUCTURE.md`](STRUCTURE.md) — repository/source-of-truth structure.
- [`NUMERICAL_REPRODUCIBILITY.md`](NUMERICAL_REPRODUCIBILITY.md) — canonical numerical regression stack.
- [`architecture/`](architecture/) — architecture decisions and engine design.

## Validation and maintenance

- [`validation/`](validation/) — closure and validation reports.
- [`maintenance/`](maintenance/) — legacy cleanup and compatibility evidence.
- [`roadmap/`](roadmap/) — historical/planning material.

## Historical development evidence

Older slice reports and machine evidence are intentionally kept away from the repository root:

- [`history/slices/`](history/slices/) — slice reports, manifests, test/package summaries.
- [`history/checksums/`](history/checksums/) — historical release checksum lists.
- [`history/status/`](history/status/) — version-era design/status snapshots.
- [`internal/REPOSITORY_STATUS.json`](internal/REPOSITORY_STATUS.json) — current maintainer-oriented machine status.

Historical files may mention paths or terminology that were current when that evidence was produced. They are records, not current user navigation authority.

## Current engineering slice

- **CR00 — Composer Rebuild Boundary / Pre-refactor Freeze** — **CLOSED**.
- [**CR01 — Minimal Song Model + Contract Foundation**](architecture/CR01_MINIMAL_SONG_MODEL.md) — **CLOSED**.
- [**CR02 — Song → Execution Plan Lowering**](architecture/CR02_SONG_EXECUTION_LOWERING.md) — **CLOSED**.
- [**CR03 — First Artistic Bottleneck: Piano + Violin**](architecture/CR03_PIANO_VIOLIN_BOTTLENECK.md) — **ENGINEERING / PERCEPTUAL CANDIDATE**.
