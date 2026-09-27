# CR06 — Evidence-first QA

Status: **ENGINEERING / EVIDENCE-USABILITY CANDIDATE**

Issue: #33

## Purpose

CR06 separates objective integrity enforcement from descriptive musical evidence.

```text
Song + Performance Score + Execution Plan + Render
    ↓
Hard Integrity Gate
    ↓
Musical Evidence Report
    ↓
Composer interpretation
    ↓
optional explicit CR04 Revision Plan
```

QA may protect correctness. QA may not decide whether music is good.

## Hard Integrity Gate

Binary PASS/FAIL is restricted to objective integrity/correctness:

- finite rendered audio;
- explicit clipping policy;
- exact Performance Score binding;
- coherent Song → Score → Execution Plan → realized-IR provenance;
- authored note pitch/timing/duration authority preserved through physical realization;
- required mechanical realization present and not impossible.

Malformed contracts and invalid references fail before a QA report is emitted. Renderer
failure remains a render failure rather than an aesthetic result.

## Musical Evidence

Evidence is descriptive and keyed by requested focus:

- dynamics / windowed RMS motion;
- spectral centroid and broad-band energy fractions;
- register exposure / high-register duration;
- phrase gaps / overlaps;
- interval-pattern repetition;
- voice motion;
- section-level motion / tension-release proxies;
- close-register cross-track occupancy / masking evidence.

There is deliberately no weighted aggregate, no "good music" score, no quality score,
and no automatic musical PASS/FAIL.

## Anti-self-certification

`code-composer-qa-request/v1` fingerprints both the exact source score and the QA
target/policy.

Comparing QA reports records a `target_mutation` when hard-policy or evidence-focus
parameters differ. A changed target cannot be represented as musical improvement.

`code-composer-qa-comparison/v1` explicitly exposes:

- target mutation fields;
- hard-integrity transition;
- whether descriptive evidence changed;
- `improvement_verdict: false`;
- `aesthetic_ranking: false`.

Analysis cannot author or apply CR04 revision operations.

## Public command

```bash
code-composer-song qa SONG.json PERFORMANCE_SCORE.json QA_REQUEST.json OUTPUT_DIR/
```

Outputs include:

- final 24 kHz QA WAV;
- Execution Plan;
- realized/resolved IR;
- audio analysis;
- QA request;
- QA report with full source provenance.

## First dogfood — accepted Lantern Current

Subject: the accepted CR04 revised **Lantern Current**.

The dogfood proves:

1. valid candidate hard integrity → PASS;
2. injected clipping → hard FAIL;
3. corrupted Execution Plan provenance → hard FAIL;
4. authored-note divergence after realization → hard FAIL;
5. changing only `high_register_midi: 76 → 72` on the same score/render is recorded
   as `target_mutation=true`;
6. target mutation never produces an improvement verdict.

## Closure

Engineering gate:
- strict request/report/comparison schemas and packaged parity;
- accepted subject hard integrity PASS;
- controlled objective corruptions fail the expected hard checks;
- target mutation is explicit;
- no aesthetic score / automatic acceptance / automatic revision authority;
- Python 3.10/3.12, checkout, Skill/plugin/build PASS;
- dogfood artifact hashes PASS.

Evidence-usability gate:
- a human Composer can inspect the report and distinguish objective blockers from
  descriptive observations without the QA system pretending to make the artistic
  decision.

Metrics are evidence, not musical authority.
