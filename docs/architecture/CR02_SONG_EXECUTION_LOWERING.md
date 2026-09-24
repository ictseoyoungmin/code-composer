# CR02 — Song → Execution Plan Lowering

Status: **CLOSED**

Issue: #22

## Purpose

CR02 lowers the canonical Composer-first Song into a deterministic runtime-aware
Execution Plan without using a legacy seed IR.

The lowerer may resolve **execution facts**. It may not invent **artistic facts**.

## Execution facts owned by CR02

- contiguous section timeline;
- exact material duration from authored rhythm;
- repeated part-instance positions;
- current-runtime tonal compatibility;
- engine/preset resolution;
- fully materialized deterministic patches;
- source Song fingerprint and execution-plan fingerprint.

## Artistic facts CR02 must not invent

- pitch anchor or actual note sequence;
- chord voicing;
- octave/register movement;
- chromatic transpose;
- dynamics or expression curves;
- melody variation;
- arrangement-role inference;
- style/mood → musical-content mapping.

This is why CR02 does not yet render audio.

## Instrument resolution

The default resolver is deliberately small and capability-first:

| Song identity | Canonical runtime preset |
|---|---|
| piano / no variant | `piano.concert_grand_natural` |
| piano / acoustic-grand | `piano.concert_grand_natural` |
| violin / no variant | `bowed.violin.modeled_continuous` |
| violin / solo-arco | `bowed.violin.modeled_continuous` |
| bass / no variant | `bass.electric_finger_modeled` |
| bass / electric-finger | `bass.electric_finger_modeled` |
| drums / no variant | `drums.acoustic_kit_modeled` |
| drums / acoustic-kit | `drums.acoustic_kit_modeled` |

There is **no generic fallback**. Unknown family/variant combinations require an
explicit preset lock.

An explicit preset lock wins. An engine-only lock can use a compatible canonical
family default, but an engine/preset mismatch is a hard failure.

## Temporal lowering

- motif duration = exact sum of authored motif rhythm;
- progression execution requires explicit authored rhythm;
- rhythm duration = `cycle_beats`;
- repeats expand sequentially with no hidden gate;
- every repeated instance must remain inside its section.

The historical hidden `0.82` note-duration behavior has no place in this layer.

## Tonal boundary

CR01 accepts arbitrary authored scale identifiers. CR02 checks current runtime
capability. Unsupported scales fail explicitly instead of being remapped.

Non-tonal Songs remain lowerable when they contain only non-pitched rhythm material.

## Output

`code-composer-execution-plan/v1` contains:

- source Song fingerprint;
- normalized transport/tonal state;
- section timeline;
- runtime-resolved instruments and patches;
- arbitrary tracks unchanged;
- symbolic materials with exact duration;
- expanded part instances.

CR03 may consume this plan to build the first piano+violin artistic realization and
render path.


## Closure

CR02 is **CLOSED**.

Authoritative evidence:
- Issue #22: closed / completed.
- PR #23: merged.
- validated candidate HEAD: `460ac57bcac0c75b3172b049121bd78cae105024`.
- CR02 merge on main: `34a35f17f5f5de237e67e5f172da8a8875668126`.
- pre-merge Actions #66 / run `35980019164`: checkout-hygiene + Python 3.10 + Python 3.12 SUCCESS.
- Python 3.10 / 3.12 blocking suite: 689 passed / 3 deselected on the validated candidate.
- post-merge Actions #67 / run `35980410984`: SUCCESS.
- skill self-check, canonical skill validation, plugin distribution, and Skill/Codex/Claude build surfaces PASS.
- source/package Execution Plan schemas are byte-identical.
- 15 CR02 focused regressions cover exact temporal preservation, no generic fallback, explicit scale failures, section overflow, deterministic fingerprinting, and legacy-vocabulary absence.
- no existing synthesis, mixer, renderer, legacy arranger, or Music IR implementation file was modified.

No perceptual music gate was required because CR02 resolves runtime planning only and does not yet realize or render note-level musical content.

Next: **CR03 — First Artistic Bottleneck: Piano + Violin**.
