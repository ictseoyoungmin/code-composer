# R2 — Validation Closure

Status: CLOSED

## Contract

`validation PASS -> compile / arrange / render has no known schema/parameter crash`

R2 moves parameter failures to validation boundaries instead of allowing late `ValueError`,
fallback metadata corruption, or piano-design execution errors.

## Closed failures

- invalid `piano_design` category: aggregate IR validation now rejects it
- non-numeric transition values: Brief compile rejects them
- non-numeric development scales: Brief compile rejects them
- invalid harmony section colors: Brief compile rejects them
- development family members referencing absent sections: rejected
- rhythm section profiles referencing absent Brief sections: rejected
- runtime `arrangement.profiles.*.entry_gain/entry_soften_beats`: validated before arrangement
- runtime harmonic/development/orchestration/rhythm extension values: validated at aggregate and render boundaries

## Shared contract surface

`src/code_composer/validation_contracts.py` is used by:

1. Composition Brief validation
2. aggregate pipeline IR validation
3. final render boundary

This avoids a Brief-only fix that could be bypassed by direct Music IR.

## Legacy compatibility

Legacy runtime IR may retain dormant semantic rhythm profiles such as `intro/build/main/break/final`
while the current form uses only a subset. These dormant profiles are allowed, but every stored value
is still validated.

Agent-authored Briefs are stricter: a section profile must refer to a section that actually exists in
the authored form.

## Regression

- pytest: 94 / 94 PASS
- Python modules: 111
- import failures: 0
- import cycles: 0

## Output preservation

Valid R1 and R2 Composer Plan + Music IR + arranged graph are byte-identical.

SHA-256:

`0dedde89715e600200db9ed383815dcd069eb766bf7c460d33fdebc7ae50a082`

Representative valid render is also byte-identical:

`b2b0b712fa0249f0246f73725b3e9cdef1dbfb12248dbd76988ace84bdf7aa49`
