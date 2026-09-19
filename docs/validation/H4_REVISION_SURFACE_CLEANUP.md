# v1.16 H4 — Canonical Revision Surface Cleanup

Status: CLOSED

## Problem

The v1.16 architecture says:

```text
Analyzer → evidence → Composer Agent → structured revision
```

but the package still shipped a second mutation model:

```text
issue → propose_from_issue() → PatchOp / Proposal → apply_proposal() → try_proposal()
```

That deterministic issue→patch path could author changes without the Composer Agent.

## Resolution

Removed from runtime and wheel:

- `code_composer.revision`
- `code_composer.revision_runner`
- `revision/revision.py`
- `revision/revision_runner.py`
- `propose_from_issue`
- `apply_proposal`
- `try_proposal`
- `PatchOp`
- `Proposal`

`pipeline.service.render_state()` remains the single in-process render/analyze service.

The only canonical revision loop is now:

```text
render
→ analysis / expressive QA
→ evidence
→ Composer Agent critique
→ Agent-authored Expressive Score Plan / Music IR revision
→ validate / recompile / rerender
```

`compare_expressive_qa()` is evidence comparison only; it does not author or apply patches.

## Verification

- focused H4 tests: 21 PASS
- full regression: 212 / 212 PASS
- coverage: 88%
- compileall: PASS
- import failures: 0
- static import graph: 109 source modules / 128 edges / 0 cycles
- legacy flat/direct path H3 → H4: byte-identical
- H3 call/response dogfood IR rendered under H3 and H4: byte-identical

Representative legacy hashes:

- Composer Plan: `f7f16714e9d98666ae29d27b0c183d89fdd14aa82de9d4d4869cdb45ef2ee302`
- Music IR: `ef60c5f7388bddb0cd6eff857ee2dc937f3d819deb017a87a95d4146faa04b51`
- WAV: `589ac3efdc466a1a7c191caa0e614a63b1a28e4dea566b08164df3730f4490e0`

H3 call/response dogfood WAV under both engines:

`0023687bde334c2b4bc44b4b89eb83c8fb9c38b298fdf12e94c4adc7a07bf960`

## Compatibility note

This intentionally removes the legacy automatic-revision Python API. It is an architectural cleanup, not a transparent compatibility shim.

Audio rendering, Composition Brief compilation, Music IR execution, expressive QA, and all E0–E6 execution paths remain unchanged.

## Next

H5 — Reference / Package Hygiene:
- synchronize version surfaces
- update current architecture/reference headers
- inspect/remove true orphan runtime surfaces
- package/build reproducibility documentation
