# Composer Agent Piano Selection Contract — v1.15.5

The deterministic engine does **not** interpret descriptive words into piano presets.

The Composer Agent first decides what sound-producing system the piece actually needs, then authors
the structured design.

## Decision order

1. Decide the sound source family.
   - `acoustic`: hammer → strings → bridge → soundboard/body
   - `electric`: tine/reed/FM excitation → pickup → amp → modulation
2. Choose structural categories within that family.
3. Set exact numeric controls only where the musical purpose needs precision.
4. Render and critique the actual audio.
5. Revise the structured design, not the user's words.

## Acoustic questions

- Does the part need a large or compact physical body?
- How exposed should the hammer/mechanics be?
- How many/stringing character and detune are appropriate?
- Should the shared soundboard be open, balanced, or dry?
- What keyboard perspective fits the mix?

## Electric questions

- Which excitation mechanism best serves the part: tine, reed, or digital FM?
- Should the pickup emphasize or soften upper harmonics?
- Is a direct signal or amp/cabinet coloration appropriate?
- Does modulation serve the musical role, and if so tremolo or chorus?
- How wide should the stage image be?

These are reasoning prompts for the Agent, not a keyword table.

## Invalid shortcut

Do not implement rules such as:

```text
"warm" -> warm_combo
"nostalgic" -> tine
"cinematic" -> concert_grand
```

The same descriptive word may imply different designs depending on harmony, arrangement, register,
tempo, density and the user's reference context.

## Authoring examples

Acoustic:

```json
{
  "family": "acoustic",
  "categories": {
    "body": "concert_grand",
    "hammer": "medium_felt",
    "stringing": "concert",
    "soundboard": "open_board",
    "perspective": "player"
  },
  "controls": {
    "bridge_coupling": 0.43,
    "modal_gain": 0.076,
    "stereo_width": 0.86
  }
}
```

Electric:

```json
{
  "family": "electric",
  "categories": {
    "mechanism": "tine",
    "pickup": "mellow",
    "amp": "clean_combo",
    "modulation": "tremolo",
    "perspective": "wide"
  },
  "controls": {
    "bell_gain": 0.32,
    "tremolo_rate_hz": 4.3,
    "tremolo_depth": 0.15
  }
}
```
