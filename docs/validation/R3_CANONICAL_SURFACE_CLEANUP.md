# R3 — Canonical Surface Cleanup

Status: CLOSED

## Canonical architecture

`User prompt -> external Composer Agent -> CompositionBrief -> deterministic compiler -> Music IR`

Code Composer no longer contains a keyword/alias natural-language intent parser in runtime source.

## Removed runtime chain

- `agent.agent_surface`
- `agent.agent_runner`
- `agent.agent_evaluation`
- `app.agent_cli`
- their root compatibility shims
- orphan `core.resolve`

These files formed the superseded vocabulary-driven edit path and had no dependency from the current
Composition Brief compiler.

## Resolver closure

There is now one `resolve_ir` implementation:

`composition.resolve.resolve_ir`

`code_composer.resolve.resolve_ir` remains only as an explicit compatibility shim.

## Canonical CLI surfaces

- `code-composer`: render Music IR
- `code-composer-compose`: compile Agent-authored Composition Brief to Music IR

A local wheel build verified both console entry points.

## Regression

- pytest: 96 / 96 PASS
- runtime Python source files: 102
- import edges: 106
- import cycles: 0
- import failures: 0
- removed vocabulary-parser runtime token hits: 0
- resolver implementations: 1

## Behavior preservation

A representative valid R2 Brief was compiled and rendered independently under R2 and R3.

- Plan SHA-256: `3ccb63001a88e7a98d4d8e74d32750291255ece2a76522dfc4050cf400538a25`
- Music IR SHA-256: `cc254fa49320783f5a374d8e8cbec5d06b09eabd99041b45a5b89974dfb2f5d8`
- arranged graph SHA-256: `4160cc8f4a4d3edd6a029b9dfaa0de47d9ad4fc0138407f1bfcf420234f250cf`
- WAV SHA-256: `b2b0b712fa0249f0246f73725b3e9cdef1dbfb12248dbd76988ace84bdf7aa49`

All four are byte-identical.

## Scope note

R3 establishes one canonical execution philosophy. Example/schema/reference-document hygiene that is
not needed to define the runtime boundary remains the next R4 slice.
