# AG02 — String / Fret / Position Authority

Status: **IMPLEMENTATION CANDIDATE**

Target release: **v1.19.0**

Dependency: AG01 canonical CLOSED / human listening PASS.

## Authority

Standard-tuning string numbering is explicit: string 1 = high E, string 6 = low E.
Performance Score may author `instrument_performance.string`,
`instrument_performance.fret`, or both on the accepted AG01 physical preset.

- both authored: exact position is validated and preserved;
- string only: fret is derived from authored pitch;
- fret only: the matching standard-tuning string is derived;
- neither: a deterministic playable resolver selects the lowest valid fret;
- impossible or contradictory mechanics are hard errors.

The resolver never changes MIDI, onset, or duration.

## Physical realization

Resolved mechanics are recorded as `performance.guitar_realization` and in
`guitar_performance_report`. The steel-string source consumes string identity and
fret/effective-length state to vary bounded stiffness, partial balance, damping,
contact loss, transient identity, and bridge coupling.

The AG01 direct path remains unchanged when no guitar realization is supplied.

## Scope boundary

AG02 does not assign finger/nail/pick excitation, left-hand articulation, strum,
body percussion, or persistent six-string coupling. Those remain AG03–AG08.

## Closure gate

1. authored string/fret authority is preserved;
2. invalid combinations fail loudly;
3. unspecified mechanics resolve deterministically;
4. same MIDI at two valid positions is measurably and audibly distinct;
5. resolved mechanics provenance is retained;
6. blocking regression passes;
7. human matched A/B listening passes before AG02 is canonical CLOSED.
