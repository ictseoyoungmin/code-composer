## Scope

Describe the slice and its owned delta.

## Closed-slice preservation

- Upstream canonical CLOSED slice(s) touched:
- Frozen invariant(s):
- Preservation regression:
- New behavior owned by this slice:
- Evidence protocol:
- Upstream slice REOPEN required: yes / no

> A downstream slice must not retune or replace accepted upstream behavior to make
> its feature easier to demonstrate. If a frozen invariant must change, REOPEN the
> owning slice and rerun its closure barrier before merge.

## Validation

- [ ] blocking regression PASS
- [ ] build / distribution checks PASS
- [ ] each perceptual bottleneck tested independently
- [ ] previous canonical reference included in listening evidence when perception is involved
- [ ] human listening PASS obtained when required
