# Code Composer Architecture v1.16

> **PRE-REFACTOR HISTORICAL ARCHITECTURE.** CR00 starts a breaking Composer-first rebuild with no authoring compatibility/migration requirement. The v1.16.x validation rigor remains a design reference, but `CompositionBrief`, seed-first composition, fixed six-role authoring, and the current Music IR shape are not canonical constraints for CR01+. See [CR00 Composer Rebuild Boundary](CR00_COMPOSER_REBUILD_BOUNDARY.md).

## Canonical pipeline

```text
User prompt
  → Composer Agent (outside deterministic engine)
  → explicit CompositionBrief
  → Brief validation
  → deterministic Brief→ComposerPlan compiler
  → Music IR
  → pipeline.service
      → aggregate validation
      → render
          → arrangement / musical resolution
          → deterministic instruments / piano / percussion
          → mix graph + automation
      → analysis
  → expressive QA evidence
  → Composer Agent critique / structured revision
```

Code Composer does not infer musical intent from keyword dictionaries or style-name vocabularies.

## Layer boundaries

- **core**: IR primitives, theory and hard constraints. No upward imports.
- **composition**: phrase, form, harmony, orchestration, rhythm, transitions and the single canonical resolver.
- **audio**: deterministic DSP, pitched instruments, piano and percussion.
- **mix**: buses, routing, sends and automation.
- **render**: execution orchestrator and WAV writer.
- **analysis**: audio/musical/structural measurement.
- **pipeline**: aggregate validation and in-process render/analyze service.
- **analysis** emits evidence only; the Composer Agent authors any structured revision before recompilation.
- **agent**: explicit `CompositionBrief` schema/validation and deterministic Brief→Plan compiler. It is not a natural-language parser.
- **app**: user-facing adapters.

## Validation boundaries

1. `CompositionBrief` validation before compile.
2. aggregate Music IR validation before execution.
3. final render-boundary validation.

R1 additionally enforces hard forbidden roles at final event-graph execution.

## Resolver policy

`composition.resolve.resolve_ir` is the only resolver implementation.

`code_composer.resolve.resolve_ir` is an explicit compatibility shim. The former orphan
`core.resolve` implementation was removed in R3.

## CLI surfaces

- `code-composer`: render an existing Music IR.
- `code-composer-compose`: compile an Agent-authored Composition Brief into Music IR.

Neither CLI performs natural-language interpretation.

## Testing contract

`pytest -q` is canonical. Graph tests enforce no import cycles, no core upward imports, no CLI
recursion, absence of the removed vocabulary parser, and a single resolver implementation.


## Revision ownership

The deterministic engine does not own creative revision.

```text
analysis
  → evidence
  → Composer Agent
  → explicit structured revision
  → validation
  → deterministic execution
```

The legacy automatic `revision.propose_from_issue()` / `apply_proposal()` subsystem was removed in v1.16 H4. `pipeline.service` remains the single in-process render/analyze service.
