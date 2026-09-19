# Piano Family Architecture — v1.15.5

## Goal

The Composer Agent must be able to choose an acoustic or electric piano for the musical purpose
without the deterministic engine pretending to understand descriptive vocabulary.

```text
User intent
   ↓
Composer Agent judgment
   ↓
piano_design
├─ family      # acoustic | electric
├─ categories  # structural discrete choices
└─ controls    # direct numeric values
   ↓
family-specific resolver / renderer
```

## Acoustic family

Categories:
- body: concert_grand / studio_grand / upright
- hammer: soft_felt / medium_felt / dense_felt
- stringing: concert / compact / aged
- soundboard: open_board / balanced_board / dry_board
- perspective: player / audience / close

Signal structure:

```text
hammer excitation
→ coupled stretched strings
→ bridge transfer
→ register/velocity body filter
→ shared modal soundboard
→ key/damper mechanics
→ stereo radiation
```

The old authored `piano_graph` remains readable and retains its historical behavior. The additional
bridge/modal/mechanical stages activate through the current `piano_design` resolver.

## Electric family

Categories:
- mechanism: tine / reed / digital_fm
- pickup: mellow / neutral / bright
- amp: direct / clean_combo / warm_combo
- modulation: none / tremolo / chorus
- perspective: centered / wide / close

Signal structure:

```text
tine / reed / FM excitation
→ velocity-dependent bell/bark
→ pickup transfer + saturation
→ amplifier transfer
→ tremolo / chorus
→ stereo image
→ key mechanics
```

This is a different rendering engine from the acoustic path; it is not an acoustic preset with
different EQ.

## Category vs numeric controls

A category changes topology or a physically meaningful baseline. A numeric control directly sets a
parameter. Numeric controls are absolute and win over category baselines.

Subjective axes such as `warmth=0.8` are intentionally unsupported.

## Backward compatibility

A `piano_design` without `family` is interpreted as `acoustic`, preserving v1.15.4 authoring.
Legacy resolved `piano_graph` remains supported.
