# CR04 — Listen / Critique / Revision

Status: **CLOSED**

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


## Closure

CR04 is **CLOSED**.

Authoritative evidence:
- Issue #28: closed / completed.
- PR #29: merged after explicit matched A/B perceptual listening PASS.
- validated candidate HEAD: `0674ed5611fa20b660891ed3249ed986cdfc54e0`.
- implementation merge on main: `06e344bfe87c87b57c8a6f174d223b04b0fc3f55`.
- pre-merge CI #92 / run `36005868417`: checkout-hygiene + Python 3.10 + Python 3.12 SUCCESS.
- blocking suite: 721 passed / 3 deselected on Python 3.10 and 3.12.
- CR04 Revision Dogfood #2 / run `36005868352`: SUCCESS.
- matched A/B artifact ID: `10809229987`.
- source score fingerprint: `fa8bba9f5bf0ec1b1447a77bf017a09cd8512da5fce155ade2745d18de4a0ddd`.
- revision plan fingerprint: `af5896aef1008653efed6c8f8ebdc51fa4c28b31addeb54333d1a06b16ca875f`.
- after score fingerprint: `b8352a010cf099cc2052865b9f0f1b387d3d156e5223cf5c5a6d78990118f7f9`.
- post-merge main CI #93 / run `36135363088`: checkout-hygiene + Python 3.10 + Python 3.12 SUCCESS.
- preserved scopes: violin exact, piano bass exact, sustain controls exact.
- targeted changes: six coda upper-piano events + piano-foundation mix gain only.
- before/after clipping: 0.0.
- perceptual listening verdict: PASS.

The CR04 revision authority remains Composer-authored intent. Analysis and metric deltas are evidence only and do not author changes or decide acceptance.

Next: **CR05 — Fast Preview / Incremental Render**.
