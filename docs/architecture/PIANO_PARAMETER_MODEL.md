# Piano Parameter Model — v1.15

Piano authoring has two deliberately separate surfaces.

## 1. Categories — discrete structural choices

Categories describe **which physical configuration** is being modeled. They are not mood words and are not continuous knobs.

```json
{
  "categories": {
    "body": "concert_grand",
    "hammer": "medium_felt",
    "stringing": "concert",
    "soundboard": "open_board",
    "perspective": "player"
  }
}
```

Current categorical fields:

- `body`: `concert_grand | studio_grand | upright`
- `hammer`: `soft_felt | medium_felt | dense_felt`
- `stringing`: `concert | compact | aged`
- `soundboard`: `open_board | balanced_board | dry_board`
- `perspective`: `player | audience | close`

Subjective vocabulary is intentionally invalid here. `body: "warm"` is rejected.

## 2. Controls — direct numeric parameters

Controls are explicit absolute values with physical/DSP meaning.

```json
{
  "controls": {
    "stereo_width": 0.34,
    "base_decay_s": 2.35,
    "hammer_noise_gain": 0.095,
    "detune_cents": 0.8
  }
}
```

No control called `warmth`, `grandness`, or `acousticness` exists.

## Resolution order

```text
category baseline
      ↓
resolved physical graph
      ↓
absolute numeric controls override matching values
      ↓
validated piano_graph
      ↓
Piano Performance Engine
```

The merge rule is deterministic and fixed. Numeric controls always win over category baselines for the exact parameter they address.

## Example

```json
{
  "kind": "piano",
  "piano_design": {
    "categories": {
      "body": "concert_grand",
      "hammer": "medium_felt",
      "stringing": "concert",
      "soundboard": "open_board",
      "perspective": "player"
    },
    "controls": {
      "stereo_width": 0.31,
      "base_decay_s": 2.75
    }
  }
}
```

`concert_grand` establishes a wide/long-decay baseline, but the authored `stereo_width=0.31` and `base_decay_s=2.75` become the final values.

Legacy `piano_graph` patches remain readable. A single patch may not contain both `piano_design` and `piano_graph`, because that would create two competing authoring surfaces.
