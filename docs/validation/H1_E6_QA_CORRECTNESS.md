# v1.16 H1 — E6 QA Correctness

Status: CLOSED

## F01 fixed — orchestration masking occupancy

Old behavior summed overlap for every note pair. Polyphonic subordinate chords therefore multiplied occupied time.

New behavior:

```text
primary note events      -> merge intervals -> primary role occupancy
subordinate note events  -> merge intervals -> subordinate role occupancy
                                          ↓
                              interval intersection
                                          ↓
                         shared / primary occupancy
```

Audit B dogfood, after revision:

- old reported ratio: `0.7225`
- corrected union ratio: `0.240838`
- corrected `ORCHESTRATION_MASKING`: absent

The B WAV SHA remains unchanged:

`acbe34b6b811554df150bd4654d1195bce68f60835a1cc9ae95bf71d4ce03246`

## F02 fixed — global revision regression guard

`compare_expressive_qa()` now reports:

- `target_improved`
- `introduced_non_target`
- `introduced_high_medium`
- `regression_free`
- `improved`

Final semantics:

```text
improved = target_improved AND regression_free
```

A revision that resolves `TRANSITION_DISCONTINUITY` but introduces a new HIGH `REGISTER_COLLISION` is now rejected.

When no explicit target-code set is supplied, newly introduced HIGH/MEDIUM issues are also guarded.

## Verification

- pytest: **186 / 186 PASS**
- coverage: **87%**
- runtime modules: **113**
- import edges: **132**
- import cycles: **0**
- import failures: **0**
- compileall: PASS

## Backward compatibility

Legacy v1.15.6 path remains byte-identical:

- Composer Plan: `f7f16714e9d98666ae29d27b0c183d89fdd14aa82de9d4d4869cdb45ef2ee302`
- Music IR: `ef60c5f7388bddb0cd6eff857ee2dc937f3d819deb017a87a95d4146faa04b51`
- WAV: `589ac3efdc466a1a7c191caa0e614a63b1a28e4dea566b08164df3730f4490e0`

## Remaining audit blockers

H1 does not close the full v1.16 audit. Remaining sequence:

1. H2 — JSON Schema / Python validator contract parity
2. H3 — E2 call semantics + motif identity hard/soft policy
3. H4 — canonical revision surface cleanup
4. H5 — reference/package hygiene
5. Final integrated v1.16 closure dogfood
