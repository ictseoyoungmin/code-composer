# v1.16 Implementation Slices

Status: E0–E6 CLOSED / FINAL v1.16 INTEGRATED CLOSURE CLOSED

## E0 — Contract Foundation — CLOSED

### Implement
- `expressive_score_plan.py`
- `performance_ir.py`
- JSON/Python validation parity
- section/role/reference integrity
- curve monotonic-position validation
- range invariants
- motif statement lineage integrity

### CLOSED when
- schemas validate checked-in example
- Python validator rejects all cross-reference violations
- no musical output changes when expressive plan is absent
- v1.15.6 regression suite remains byte-compatible where applicable

---

## E1 — Phrase Expression — CLOSED

### Implement
- phrase membership over note/event groups
- normalized phrase position per note
- dynamic-curve interpolation
- timing-curve interpolation
- gate/note-length curve
- articulation realization
- accent realization
- explicit breath/gap realization
- bounded deterministic micro-variation

### Critical rule
Random variation may decorate an authored phrase but may never create the phrase envelope.

### CLOSED when
One identical motif rendered with three different phrase plans produces:
- same pitch identity,
- measurably different velocity contour,
- measurably different microtiming contour,
- measurably different note-length contour,
- deterministic identical output for identical plan+seed.

Dogfood: solo piano only. No mix/reverb used to hide performance defects.

---

## E2 — Motif Development — CLOSED / H3 SEMANTICS HARDENED

### Implement
- motif statement lineage
- `exact`
- `fragment`
- `sequence`
- `transpose`
- `register_shift`
- `rhythm_scale`
- `rhythm_rewrite`
- `inversion`
- `retrograde`
- `cadence_rewrite`
- `ornament`
- call/response relation

### Identity measurement
Compare transformed statement against source using:
- interval contour retention
- rhythmic landmark retention
- pitch-class/scale-degree anchors
- phrase landmark retention

No single metric is the creative decision; the Agent supplies `identity_floor` as a QA target. An optional lower `identity_hard_min` is the only identity-based compile barrier.

### CLOSED when
A five-section piece uses one source motif and produces at least four recognizably related but non-identical statements with explicit lineage.

---

## E3 — Register & Voicing — CLOSED

### Implement
- hard range enforcement
- preferred-range optimization
- role center / span
- intervoice spacing
- smooth voice allocation
- simultaneous role/register occupancy analysis
- register collision score

### CLOSED when
- no generated note violates hard range
- preferred range can be exceeded only with traceable reason
- collision analyzer catches synthetic overlap fixtures
- piano-led dogfood removes pad/arp masking without EQ-only fixes.

---

## E4 — Orchestration Budget — CLOSED

### Implement
- primary / secondary / decorative roles
- max simultaneous role budget
- silence roles
- phrase-gap-only decorative roles
- overlap allowlist
- event gating after all material/transition generation

### Critical rule
Development is not defined as adding layers.

### CLOSED when
A section marked piano-only stays piano-only even after transition/fill generation, and decorative arp is emitted only in primary-phrase gaps.

---

## E5 — Musical Transitions — CLOSED

### Implement
- harmonic anticipation
- pickup material
- bass approaches
- cadence extension
- role subtraction
- explicit silence
- register preparation
- rhythm fill as one optional transition component

### CLOSED when
At least three transition types are audible and structurally different:
1. subtraction + silence,
2. anticipation + pickup,
3. cadence extension + register preparation.

No transition may require a volume fade to be recognizable.

---

## E6 — Expressive QA + Revision Loop — CLOSED

### Implement analyzers
- `MECHANICAL_TIMING`
- `FLAT_DYNAMICS`
- `MOTIF_IDENTITY_LOSS`
- `REGISTER_COLLISION`
- `ORCHESTRATION_MASKING`
- `TRANSITION_DISCONTINUITY`
- `PHRASE_NO_BREATH`

### Revision discipline
Analyzer reports evidence. It does not rewrite music automatically.

```text
render
→ analyzer evidence
→ Composer Agent critique
→ structured plan revision
→ recompile
```

### CLOSED when
Three distinct dogfoods each undergo at least one Agent-authored structured revision and improve the targeted metrics without introducing hard-constraint regressions.

---

# Final v1.16 closure

Required final dogfoods:

## A. Lyrical piano
Tests phrase, motif, voicing, breathing and acoustic performance.

## B. Rhythm-centered track
Tests timing hierarchy, articulation, transition fills and role budgets.

## C. Sparse chamber/electronic track
Tests silence, orchestration masking, register separation and non-layer-based development.

All final outputs:
- 44.1 kHz minimum,
- no sample clipping,
- reproducible from checked-in structured plans,
- explicit before/after revision artifacts,
- no natural-language keyword parser,
- no style→fixed-material mapping.


## Final closure result — CLOSED

Three integrated four-section compositions passed the final gate.

Each final:
- executes E1–E6 with concrete resolved provenance,
- has three authored transitions and at least two transitions with realized effects,
- has zero final Expressive QA issues,
- has zero final HIGH/MEDIUM legacy analyzer issues,
- improves its before-state with no introduced HIGH/MEDIUM expressive regression,
- renders at 44.1 kHz with zero clipped samples,
- rerenders byte-identically.

See `docs/validation/V116_FINAL_CLOSURE.md`.
