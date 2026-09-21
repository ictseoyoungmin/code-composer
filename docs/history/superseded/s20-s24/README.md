# Superseded S20-S24 drum runtime lineage

These files are retained as historical implementation and regression evidence from the GitHub source-first baseline.

They are **not** part of the current active runtime/test surface.

## Why archived

The later ZIP-first drum lineage deliberately re-anchored on the user-selected **S19 core** before S20 and then rebuilt cymbal, kit-room, articulation, hi-hat state, snare/tom authenticity, and drummer-performance behavior through S25-S27.

The S25 preservation contract explicitly states that the S19 core is the canonical pre-S20 drum checkpoint and that later S20 non-cymbal coupled-head/cavity hardening is not imported into that path.

Keeping the old S20-S24 tests active would therefore force two incompatible runtime contracts onto the same preset IDs and renderer API. The files are archived here instead of silently discarded.

## Preserved material

- S20-S24 regression test modules
- S21-S24 opt-in preset JSONs
- S23/S24 historical dogfood render tools

The corresponding reports/checksums remain in the normal `docs/history/` hierarchy.

## Current authority

Current active drum authority is the S19-core-derived S25-S27 lineage present under the canonical `skills/code-composer/`, `tests/`, and `tools/` surfaces.
