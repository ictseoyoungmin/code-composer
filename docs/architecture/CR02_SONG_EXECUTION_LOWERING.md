# CR02 — Song → Execution Plan Lowering

Status: **ENGINEERING CANDIDATE**

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
