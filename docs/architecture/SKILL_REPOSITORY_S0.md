# S0 — Skill Repository Reframe

## Decision

`skills/code-composer/` is the canonical installable product. It must be copyable by itself to an arbitrary directory and remain operational without reading repository-parent files.

The repository root is a maintainer workspace. Root docs/examples/tests are not part of normal agent context.

## Progressive disclosure

`SKILL.md -> kit/INDEX.md -> one workflow -> needed contract/schema -> command/script -> source only by exception`.

This prevents the agent from learning normal operation by broad-scanning implementation modules.

## Musical-content firewall

**Examples teach operation, never taste.** The installed skill contains no completed music, showcase audio, polished MIDI, dogfood songs or stylistically meaningful exemplar arrangements. Operational examples are prose; templates are content-empty; fixtures are tiny synthetic protocol probes declared `musical_reference=false`.

Maintainer regression/showcase material remains under repository `examples/` and is excluded from skill/plugin build artifacts except for the synthetic skill fixtures.

## Platform adapters

`.codex_plugins/` and `.claude_plugins/` contain platform metadata source. Release tooling injects an exact copy of the canonical skill into a generated plugin ZIP, avoiding a second editable source of truth.
