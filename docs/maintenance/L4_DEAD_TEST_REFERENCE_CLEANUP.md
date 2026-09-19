# Legacy Cleanup L4 — Dead Test / Reference Cleanup

Status: **CLOSED**

v1.16.0 remains **CLOSED**. L4 removes only the files explicitly authorized by the closed L3 candidate boundary and cleans tests/navigation that assumed those files still existed. No runtime or schema behavior is changed.

## Scope

L3 authorized exactly **12 files / 37,197,041 bytes (~37.2 MB)** for deletion review. L4 did not expand that deletion boundary.

For each of the three final-closure dogfoods, L4 removed:

- the deterministic repeat WAV,
- the repeat analysis JSON,
- the repeat resolved JSON,
- the derived before/after comparison WAV.

The nine repeat artifacts were byte-identical to retained canonical evidence. Each comparison WAV was proven before deletion to be a deterministic transform of retained `before.wav` and `after.wav`: int16 re-quantized before audio, **30,869 zero frames (~0.7 s at 44.1 kHz)**, then int16 re-quantized after audio. It therefore carried no independent musical state.

## Retained evidence

L4 keeps all canonical closure evidence:

- `before.wav` / `after.wav`,
- before/after plans, performance IR, Music IR, resolved IR, and analysis,
- `agent_revision.json` and `revision_comparison.json`,
- `final_closure_manifest.json`,
- `v1.16_final_showcase_reel.wav`,
- v1.15 compatibility fixtures and package mirrors.

The final-closure manifest still records the original deterministic repeat hashes. Those fields are historical release evidence, not live file references.

## Dead test cleanup

`tests/test_legacy_cleanup_l3.py` previously asserted that L4 candidate files physically existed and that the L3 inventory matched the current repository byte-for-byte. Those assertions became invalid the moment authorized L4 deletion occurred. The test was retained but narrowed to the durable L3 invariants: exact authorization boundary, recorded duplicate hashes, retained-peer identity, package-mirror identity, and closed historical status.

`tests/test_legacy_cleanup_l4.py` now owns post-cleanup invariants: the 12 files stay absent, canonical closure evidence remains, no runtime/schema payload changed, current navigation reflects L4 closure, and the next slice is L5.

## Historical reference policy

The closed L3 inventory/report and the older legacy inventory are deliberately **not rewritten**. They remain historical snapshots and may name files that L4 subsequently removed. Current navigation (`README.md`, `STRUCTURE.md`, `docs/INDEX.md`, and example READMEs) now points to this L4 delta for post-cleanup state.

## Compatibility boundary

Canonical runtime flow remains unchanged:

```text
Analyzer → evidence
        ↓
Composer Agent
        ↓
explicit structured transition / revision
        ↓
deterministic engine
```

No file under `src/` or `schemas/` was intentionally modified by L4.

## Verification

Machine-readable evidence: `docs/maintenance/L4_DEAD_TEST_REFERENCE_CLEANUP.json`.

Closure run results:

- focused L3/L4 guards: **12 / 12 PASS**
- full regression: **247 / 247 PASS**
- coverage: **88%**
- `compileall`: **PASS**
- import sweep: **98 modules / 0 failures**
- static runtime graph: **99 modules / 121 edges / 0 cycles**
- `src/` + `schemas/`: **byte-identical to L3**
- v1.15 representative `demo_ir` WAV: `589ac3efdc466a1a7c191caa0e614a63b1a28e4dea566b08164df3730f4490e0` (byte-identical)
- v1.16 final dogfood A: `93aa85955b7aa8715b65721bc6388310be87006666cb9d7241889d66993116ba`
- v1.16 final dogfood B: `7d18321f4986c324b75e2ae45e88cc061e8409dcaa16ae0b051bf4998b368377`
- v1.16 final dogfood C: `db524b79b30fbd3d79fa97b157ddb83bb84c71d71cbf09d7c48c391aa3a3834f`
- all three rerenders: **byte-identical**, clipped frame ratio **0.0**

## Next

**L5 — Clean Install / Compatibility**
