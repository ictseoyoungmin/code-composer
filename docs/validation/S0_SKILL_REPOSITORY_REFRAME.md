# S0 — Skill Repository Reframe Closure

**Status:** CLOSED  
**Date:** 2026-09-17  
**Engine baseline:** Code Composer v1.17.0 (M1–M3 unchanged)

## Purpose

Reframe Code Composer from a monolithic project package into a maintainer repository with one canonical, self-contained, installable agent skill at `skills/code-composer/`. S0 adds no music feature.

## Canonical repository boundary

```text
code-composer/
├─ .codex_plugins/          # platform adapter source only
├─ .claude_plugins/         # platform adapter source only
├─ README.md
├─ CHANGELOG.md
├─ docs/                    # maintainer-facing architecture/history/validation
├─ examples/                # maintainer-only regression/showcase/integration material
├─ skills/
│  └─ code-composer/        # canonical installable product
│     ├─ SKILL.md
│     ├─ VERSION
│     └─ kit/
│        ├─ INDEX.md
│        ├─ CAPABILITIES.md
│        ├─ COMMANDS.md
│        ├─ SOURCE_MAP.md
│        ├─ EXAMPLE_POLICY.md
│        ├─ workflows/
│        ├─ contracts/
│        ├─ templates/
│        ├─ examples/       # operation-only prose
│        ├─ fixtures/       # tiny declared-synthetic protocol probes
│        ├─ schemas/
│        ├─ scripts/
│        ├─ pyproject.toml
│        └─ src/            # low-level implementation; not default agent reading
├─ tests/
└─ tools/
```

## Agent-facing disclosure graph

```text
SKILL.md
  -> kit/INDEX.md
  -> one relevant workflow
  -> only required contract/schema
  -> documented command/script
  -> kit/src only by explicit exception
```

`kit/src/` is executable implementation, not normal operational documentation. Source inspection is reserved for implementation changes, stack-trace debugging, contract/runtime conflicts, new engine capabilities, or an explicit internal review request. `kit/SOURCE_MAP.md` must be consulted first.

## Musical-content firewall

The installed skill enforces the rule:

> **Examples teach operation, never taste.**

The skill contains no completed songs, showcase audio, polished MIDI, dogfood compositions, or stylistically meaningful exemplar arrangements. `kit/examples/` explains only how to invoke workflows. Templates are content-light scaffolds. Fixtures are declared `synthetic=true`, `musical_reference=false`, and are limited to minimal protocol events.

Maintainer musical examples remain at repository root and are not shipped in standalone skill or platform plugin artifacts.

## Self-contained rule

`skills/code-composer/` has zero parent-directory references. It can be copied alone to an arbitrary directory, validated there, and its Python runtime can be installed from `kit/`. Platform adapters inject an exact copy of this canonical skill; they do not maintain duplicate editable skill sources.

## Runtime preservation

Compared with the M3 runtime, there are 108 Python modules before and after S0. No Python module was added or removed. The only changed Python file is `reference/__init__.py`, whose docstring now states that polished musical reference examples are intentionally excluded. All composition, analysis, audio, MIDI, exchange, delivery, and rendering implementation modules remain byte-identical.

The old packaged `reference/examples/*.json` musical examples were removed from the runtime package. Maintainer copies remain outside the installed skill where needed for regression/history.

## Validation

```text
Focused S0                 7 / 7 PASS
Full regression          300 / 300 PASS
Coverage                         93%
Import sweep              108 / 108 PASS
Static dependency cycles           0
Isolated skill compileall        PASS
Standalone copy self-check       PASS
Clean wheel build/install        PASS
Synthetic runtime smoke          PASS
```

The clean-installed wheel was exercised using only the one-note synthetic protocol fixture for render, MIDI, collaboration bundle, external delivery, `.ccx` export/import, and manifest generation. The wheel contains 117 files and no packaged musical reference JSON.

## Distribution evidence

The canonical standalone skill artifact contains **262 files**. The generated Codex and Claude plugin artifacts each contain an exact byte-for-byte copy of those same 262 skill files.

```text
Standalone skill SHA-256
  d578e97613a115c6eeea1b70c0ba599bb6e2b4f31feedf15fa531787df3c4a3b

Codex plugin SHA-256
  03c21ade8d2294fd6698f19e20a9b68bff04cc7b682ded46b5fce2808df4572d

Claude plugin SHA-256
  4d8827ef07db9892eb65a30fad469f4fd9243ffbd029862e51ced17fe0dd2dad
```

Build scripts explicitly exclude caches, bytecode and `*.egg-info` metadata from agent artifacts.

## Closure

S0 is CLOSED. Future features should be added through the new boundary: maintainer implementation/change -> agent-facing contract/workflow -> standalone skill validation. No S1 maintenance slice is implied by this closure; the next feature slice should be opened explicitly.
