# AG02 — String / Fret / Position Authority

Status: **R1 REJECTED · R2 IMPLEMENTATION CANDIDATE**

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

## R1 listening failure and R2 correction

R1 was rejected because both comparison sides had already been retuned away from
the AG01 human-listening-approved tone. Broad per-string/fret profiles changed
rolloff, stiffness, decay, damping, noise, coupling, spectral loss, contact loss,
click transient and random seed identity.

R2 removes that redesign. Resolved mechanics are still recorded as
`performance.guitar_realization` and `guitar_performance_report`, but the
canonical lowest-fret reference position is acoustically inert relative to AG01.
Only alternate valid positions receive a small bounded delta in string rolloff,
inharmonicity, decay, damping and fret-contact loss. Position identity does not
change noise seed, oscillator phase identity or bridge coupling.

No authored mechanics and the reference position must both render sample-exactly
with the canonical AG01 tone.

## Scope boundary

AG02 does not assign finger/nail/pick excitation, left-hand articulation, strum,
body percussion, or persistent six-string coupling. Those remain AG03–AG08.

## Closure gate

1. authored string/fret authority is preserved;
2. invalid combinations fail loudly;
3. unspecified mechanics resolve deterministically;
4. no authored mechanics preserves the AG01 canonical output sample-exactly;
5. the AG02 reference position preserves the AG01 canonical output sample-exactly;
6. an alternate valid position is measurably distinct but remains within a bounded timbral delta;
7. resolved mechanics provenance is retained;
8. blocking regression passes;
9. human A/B/C listening uses A=AG01 canonical, B=AG02 reference position, C=alternate position before AG02 is canonical CLOSED.
