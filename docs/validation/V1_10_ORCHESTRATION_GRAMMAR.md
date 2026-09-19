# v1.10 Orchestration / Foreground Role Grammar

## Problem

Previous genre examples inherited `lead + topline_guide` from a Sunlit Static template.
That made unrelated styles share the same recorder/whistle-like foreground language.

## Solution

The arranger now resolves a section-level foreground mode:

- `none`
- `lead`
- `topline`
- `both`
- `sparse`
- `legacy`

Inactive foreground roles do not generate note events.

`legacy` behavior remains unchanged when the grammar is absent or disabled.

## Validation

- pytest: 35 / 35 PASS
- explicit none / lead / topline / sparse tests
- legacy behavior preservation test
- six-style dogfood regenerated with distinct orchestration policies
