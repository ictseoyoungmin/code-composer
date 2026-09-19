# S0R1 — Canonical Skill Hygiene Closure

Date: 2026-09-17  
Status: **CLOSED**  
Engine feature baseline: **v1.17.0 unchanged**

## Purpose

S0R1 closes a packaging hygiene defect found after S0: the canonical skill still contained a persisted `kit/build/lib` tree produced by an earlier wheel build. Those files duplicated the real `kit/src` implementation and violated the intended single-source skill design.

S0R1 is packaging-only. It adds no music capability and does not reopen v1.17 M1-M3.

## Changes

- Removed `skills/code-composer/kit/build/` from the canonical skill.
- Removed persistent `dist/` / `*.egg-info` state from the canonical skill.
- Updated standalone and plugin builders to exclude `build`, `dist`, bytecode, caches, `.coverage`, and `*.egg-info`.
- Updated standalone self-check to reject persistent `kit/build`, `kit/dist`, or `*.egg-info` state.
- Added repository tests for canonical-tree and emitted-ZIP hygiene.
- Preserved the S0 musical-content firewall: **Examples teach operation, never taste.**

## Canonical boundary

The installable product remains:

```text
skills/code-composer/
├─ SKILL.md
├─ VERSION
└─ kit/
   ├─ agent-facing docs/contracts/workflows/templates/fixtures
   ├─ pyproject.toml
   └─ src/code_composer/     # single implementation source
```

The following are not canonical skill content:

```text
kit/build/       forbidden
kit/dist/        forbidden
*.egg-info/      forbidden
__pycache__/     excluded from release artifacts
*.pyc            excluded from release artifacts
.coverage        excluded from release artifacts
```

## Engine preservation

The previous S0 standalone skill was unpacked and its `kit/src` tree compared file-by-file to S0R1.

- source files compared: **113**
- added: **0**
- removed: **0**
- changed: **0**

Therefore the music engine is byte-identical to S0.

## Validation

- S0/S0R1 focused: **8 / 8 PASS**
- Full regression: **301 / 301 PASS**
- Coverage: **90%**
- Import sweep: **108 / 108 PASS**, 0 failures
- Previous static dependency graph remains **108 modules / 145 edges / 0 cycles** because `kit/src` is byte-identical
- Standalone self-check: **PASS**
- Standalone ZIP → wheel → isolated install: **PASS**
- Synthetic render: **PASS**
- Synthetic MIDI export: **PASS**
- Synthetic collaboration bundle: **PASS**
- Synthetic external delivery: **PASS**
- Synthetic `.ccx` export/import: **PASS**
- Codex plugin skill subtree == standalone skill: **exact**
- Claude plugin skill subtree == standalone skill: **exact**

## Artifact reduction

S0 standalone skill: **262 files**  
S0R1 standalone skill: **150 files**

Exactly **112 duplicated `kit/build/lib` files** were removed from the distributed skill. No runtime source was removed.

## Closure

S0R1 is **CLOSED**. Future wheel/plugin builds must occur in temporary/staging locations and must not persist build output under the canonical skill.
