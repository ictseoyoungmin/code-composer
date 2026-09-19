# v1.9 Harmonic Color Grammar

## Goal

Add harmonic color without changing the progression identity or low-end functional harmony.
Only pad voicing is transformed; bass, drums, lead, topline and arp remain identical to v1.8.

## Grammar

- seventh
- add9
- sus2
- sus4
- inversion / voice-center search
- section-specific color sequences
- short passing-tension chord before selected section boundaries
- note-count loudness compensation for extended chords

## Harmonic QA

- authored chords: 40 -> 43
- unique colors: 1 -> 4
- passing chords: 0 -> 3
- mean voice-leading cost: 0.865 -> 1.126 semitones
- maximum voice-leading cost: 1.250 -> 2.250
- mean chord span: 8.250 -> 9.186 semitones

Color distribution:

```text
{
  "sus2": 8,
  "add9": 15,
  "seventh": 12,
  "sus4": 8
}
```

## Isolation

Unchanged resolved tracks relative to v1.8:
- bass
- drums
- lead
- topline
- arp

Only pad harmony changes.

## Whole-song QA

- analyzer issues: 0 -> 0
- energy correlation: 0.9886 -> 0.9888
- RMS: 0.115510 -> 0.115556
- peak: 0.499390 -> 0.498610

## Determinism

SHA-256: `a60d10705b921b4e42faea760f2358bbf902a054ca537b375287a5f6f164b3c3`

Repeated full-song render is byte-identical.
