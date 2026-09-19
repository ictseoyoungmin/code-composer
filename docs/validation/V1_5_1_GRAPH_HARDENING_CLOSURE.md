# Code Composer v1.5.1 — Graph Hardening Closure

## Status

**CLOSED**

This patch is behavior-preserving relative to v1.5.

## Closed slices

| Slice | Result |
|---|---|
| G01 | In-process `pipeline.service`; agent/revision CLI subprocess recursion removed |
| G02 | Pytest-native suite: **25 / 25 PASS** |
| G03 | Automation regression restored with non-empty track/bus/master coverage |
| G04 | `core` upward imports removed; phrase resolution moved to composition; aggregate validation separated and tested |
| G05 | Stable `composition.profiles` contract; explicit compatibility APIs; root wildcard exports removed |
| G06 | Cumulative architecture and structure docs updated |

## Final graph verification

- Python modules: **81**
- Static import edges: **75**
- Module import failures: **0**
- Static import cycles: **0**
- `core` upward domain edges: **0**
- Root compatibility wildcard exports: **0**
- agent CLI recursion: **0**
- revision CLI recursion: **0**

## Test verification

```text
pytest -q
25 passed
```

The suite now includes:
- aggregate IR + mix validation semantics
- package-wide import-cycle detection
- compatibility-shim wildcard guard
- non-empty automation regression
- in-process pipeline delegation
- existing composition/render/timbre regressions

## Behavior preservation

Fixture: `tests/fixtures/topline_ir.json`

```text
v1.5 baseline SHA-256
f7163769b3f96bf0188918ad61c1586ae51b2dd07256c19817642a4918b749e5

v1.5.1 hardened SHA-256
f7163769b3f96bf0188918ad61c1586ae51b2dd07256c19817642a4918b749e5
```

- WAV byte-identical: **true**
- resolved IR identical: **true**
- section analysis identical: **true**
- CLI metrics identical: **true**

## Canonical execution graph

```text
app ──────────────→ agent
 │                   │
 └──────→ pipeline ←─┘
           ↑
       revision

pipeline → render + analysis
render   → composition + audio + mix + core
mix      → audio → core
composition → core
agent → composition.profiles
```

`app` is an adapter only. Engine workflows never call the CLI internally.
