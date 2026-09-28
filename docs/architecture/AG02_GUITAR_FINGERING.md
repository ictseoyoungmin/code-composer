# AG02 — String / Fret / Position Authority

Status: **R3-BASELINED IMPLEMENTATION CANDIDATE**

Target release: **v1.19.0**

Dependency: AG01 R3 CANONICAL CLOSED / per-note human listening PASS.

Canonical upstream:
- main: `99ec64269b608254fbbdae1617432789a558daf5`
- preset: `acoustic_guitar.steel_single_string@1.0.0`
- physical model: `ag01_modal_bridge_body_v2`
- string source: `triangular_pluck_bridge_force_v2`

## Authority

Standard-tuning string numbering is explicit: string 1 = high E, string 6 = low E.
Performance Score may author `instrument_performance.string`,
`instrument_performance.fret`, or both.

- both authored: exact position is validated and preserved;
- string only: fret is derived from authored pitch;
- fret only: the matching standard-tuning string is derived;
- neither: a deterministic playable resolver selects the lowest valid fret;
- impossible or contradictory mechanics are hard errors.

The resolver never changes MIDI, onset, duration, or velocity.

## AG01 R3 preservation

AG02 is a bounded mechanics layer over the accepted AG01 R3 sound.

Hard invariants:
- no authored AG02 mechanics -> AG01 R3 output sample-exact;
- deterministic canonical reference position -> AG01 R3 output sample-exact;
- alternate valid positions may alter only a small source-level physical delta;
- position identity does not change noise seed, coherent release phase,
  pick/string contact burst, pluck position, body modes, or bridge/body coupling.

The alternate-position delta is limited to:
- bridge-force modal rolloff;
- bounded stiffness/inharmonicity;
- decay;
- frequency-dependent damping;
- fret-contact loss.

## Provenance

Resolved mechanics are attached to `performance.guitar_realization` and summarized
in `guitar_performance_report`, including explicit upstream AG01 R3 model identity.

## Scope boundary

AG02 does not assign finger/nail/pick excitation, left-hand articulation, strum,
body percussion, or persistent six-string/body coupling. Those remain AG03–AG08.

## Closure gate

1. explicit string/fret authority preserved;
2. invalid/unplayable combinations fail loudly;
3. unspecified mechanics resolve deterministically;
4. E2/E3/E4 no-mechanics path is sample-exact with AG01 R3;
5. E2/E3/E4 reference-position path is sample-exact with AG01 R3;
6. same-MIDI alternate positions are distinct but tightly bounded (<0.12 delta/RMS regression);
7. provenance retained;
8. blocking CI passes;
9. actual-branch A/B/C evidence uses A=AG01 R3 canonical,
   B=AG02 reference, C=alternate position;
10. explicit human listening PASS is required before canonical close.

The old pre-R3 AG02 PR #58 and its listening evidence are superseded and cannot
serve as closure evidence.
