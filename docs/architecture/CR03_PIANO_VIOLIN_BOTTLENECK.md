# CR03 — First Artistic Bottleneck: Piano + Violin

Status: **ENGINEERING / PERCEPTUAL CANDIDATE**

Issue: #25

## Purpose

CR03 is the first slice where the Composer-first rebuild must prove itself as music.

Fresh-worker intent:

> 피아노와 바이올린으로 약 30초짜리 서정적인 곡을 만들어라.

The engineering system must support the artist's decisions. It must not replace them
with a schema-driven arranger.

## Authority chain

```text
Song v1
    authored identity / form / symbolic materials
        ↓
Execution Plan v1
    runtime facts only
        ↓
Performance Score v1
    exact notes / voicing / register / rhythm / rests
    velocity / articulation / expression / piano pedal / mix
        ↓
Render bridge
    validates ownership and provenance
        ↓
instrument mechanics
    violin fingering / bow realization only
        ↓
existing validated piano + bowed-waveguide renderer
        ↓
24 kHz WAV / resolved IR / analysis / evidence
```

## Performance Score principle

`code-composer-performance-score/v1` is an authored musical document.

It owns decisions that earlier deterministic arranger layers often made implicitly:
- exact MIDI pitch;
- chord voicing;
- register;
- note duration;
- phrase boundary/rest;
- velocity;
- articulation;
- instrument expression;
- piano sustain curves;
- piano hand-attack offset when explicitly authored;
- track balance / pan / room-send intent.

The runtime may reject impossible or unsupported states. It must not silently rewrite
those authored decisions.

## Physical realization

For violin, the score first fixes all notes. The existing violin performance planner
then adds:
- string/fingering choice;
- transition mechanics;
- bow direction/group;
- bow force/speed defaults when absent;
- physically supported technique metadata.

A CR03 invariant snapshots note `(start, duration, midi)` before/after physical
realization and fails if mechanics change the composition.

Piano sustain is represented by explicit `piano_control / sustain_pedal` curves.
CR03 does not use a hidden note-local pedal tail as the artistic authority.

## Dogfood — Quiet Thread

- original title: **Quiet Thread**
- 10 bars
- 84 BPM
- D minor
- acoustic piano + solo violin
- 24 kHz validation render
- opening: two piano-only bars
- theme: connected violin in D4–C5
- rise: one brief F5 apex, then immediate descent
- release: return to D4 and an explicit final breath
- modeled violin preset: `bowed.violin.modeled_admittance`
- piano preset: `piano.concert_grand_natural`

The dogfood deliberately avoids optimizing an energy score. Metrics are evidence only.

## Closure policy

### Engineering gate
- Performance Score schema / Python validator parity;
- exact Song fingerprint binding;
- score/plan/render provenance chain;
- no hidden 0.82 shortening;
- modeled bowed-waveguide violin;
- physical realization preserves authored notes;
- explicit piano sustain controls;
- no fixed-role / `register_shift` / seed-IR dependency in the new path;
- full Python 3.10 / 3.12 regression suite;
- skill/plugin/build/checkout-hygiene PASS;
- GitHub dogfood workflow emits a portable artifact with relative `SHA256SUMS.txt`.

### Perceptual gate
CR03 **cannot close from CI alone**.

The produced WAV must be listened to. Listening should answer:
- does the violin read as one musical line rather than syllabic note triggers?
- does the piano support rather than compete?
- does the brief apex feel earned and short?
- are there audible static/tail artifacts?
- does the harmonic flow feel intentional?
- does the ending breathe?

A test PASS is not a musical PASS.
