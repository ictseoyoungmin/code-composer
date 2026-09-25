# CR04 — Listen / Critique / Revision

Status: **ENGINEERING / PERCEPTUAL CANDIDATE**

Issue: #28

## Purpose

CR04 makes revision a first-class Composer workflow rather than manual whole-JSON surgery.

```text
render
→ listen / evidence
→ Composer critique
→ explicit Revision Plan
→ deterministic targeted score revision
→ matched before/after render
→ compare
→ listening decision
```

Analysis remains evidence-only. It never chooses an operation.

## Canonical revision contract

`code-composer-revision-plan/v1` binds one exact source Performance Score fingerprint.

The first supported Composer-authored operations are:

- `scale_velocity` — taper or strengthen selected note attacks by beat range, optionally restricted to explicit event IDs;
- `thin_accompaniment` — remove explicitly named note events only;
- `set_track_mix_gain` — change one authored track gain;
- `shift_register` — move selected beat-range notes by explicit octaves.

These are instructions selected by the Composer from listening/user intent. They are not generated from analyzer issue codes.

## Provenance

Every successful application emits `code-composer-revision-record/v1` with:

- source score fingerprint;
- revision plan fingerprint;
- after score fingerprint;
- source Song fingerprint;
- ordered operation changes;
- changed event IDs;
- changed mix tracks;
- copied critique / preserve / acceptance statements.

A plan cannot apply to another score revision even if the title and Song are the same.

## Matched A/B

`compare-revision` renders before and after through the same Song and renderer path.

The comparison emits:
- before / after WAV hashes;
- before / after analysis metrics;
- metric deltas;
- score / plan provenance chain.

Metric deltas are evidence only. They do not decide whether a revision sounds better.

## First dogfood — Lantern Current coda

Critique:

> The final two-bar coda is a little too busy. Let the piano recede and leave more
> room around the violin without changing melody, harmony, meter, key, or form.

Revision:
- remove only `p-b11-u2` and `p-b12-u2`;
- scale only `p-b11-u1`, `p-b11-u3`, `p-b12-u1`, `p-b12-u3` to 78% velocity;
- piano track gain 0.50 → 0.46.

Hard-preserved dogfood scopes:
- exact violin track;
- exact piano bass events;
- exact sustain-pedal controls;
- Song identity;
- render sample rate / tail.

## Architectural guardrail

CR04 does **not** restore the removed v1.16 automatic revision architecture.

Forbidden as revision authorities:
- `propose_from_issue`
- `apply_proposal`
- `try_proposal`
- `PatchOp`
- `Proposal`
- analyzer-authored mutations

The Agent/Composer owns the revision choice; runtime only validates and executes the explicit plan.

## Closure

Engineering gate:
- strict plan/record contracts and source/package schema parity;
- wrong-source hard failure;
- preserved-scope regression checks;
- deterministic provenance chain;
- matched A/B artifact;
- Python 3.10/3.12, Skill/plugin/build, checkout-hygiene PASS.

Perceptual gate:
- listen to the matched A/B;
- confirm the coda becomes less crowded without harming violin line, harmonic identity, piano bass/pedal continuity, or ending flow.

CR04 cannot close from metric deltas alone.
