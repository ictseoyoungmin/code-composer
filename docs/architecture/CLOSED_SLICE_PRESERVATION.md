# Closed Slice Preservation Contract

A slice marked **CANONICAL CLOSED** establishes frozen invariants for downstream
work. Later slices may extend capability, but they must not silently retune,
replace, or reinterpret accepted upstream behavior merely to make the new feature
easier to demonstrate.

## Required downstream behavior

1. New behavior must be layered as a bounded delta over the previous canonical state.
2. With new mechanics absent, the previous canonical output must remain identical
   where deterministic rendering permits sample-exact comparison.
3. Reference/default states introduced only to name or resolve mechanics should be
   behaviorally inert unless their slice explicitly owns changing that behavior.
4. Listening evidence must include the immediately preceding canonical CLOSED result
   as the first reference. Comparing only two variants from the new slice is not a
   valid regression check.
5. If an accepted upstream invariant must change, the owning slice must be explicitly
   **REOPENED**, its closure evidence rerun, and its human listening gate repeated
   before the downstream change can merge.
6. CI regression is authoritative for machine-checkable invariants. Notion and docs
   describe the contract but do not replace executable gates.

## Perceptual closure

When a closure criterion applies across multiple pitches/registers/techniques,
human listening must test each required bottleneck independently. A montage or
full-song impression cannot substitute for a failing individual bottleneck.

## Pull-request evidence

Every feature PR following a canonical closure should state:

- upstream CLOSED slice(s) potentially touched;
- frozen invariant(s);
- executable preservation test(s);
- new delta owned by the current slice;
- A/B or A/B/C evidence protocol;
- whether an upstream slice was REOPENED.
