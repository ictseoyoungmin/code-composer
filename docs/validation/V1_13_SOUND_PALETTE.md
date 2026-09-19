# Code Composer v1.13 — Sound Palette Dogfood

## Contract

The Composer Agent writes the actual DSP patch graph. Character strings are metadata only.
The compiler does not map adjectives or genres to timbre presets.

## Dreamy Night Road

Agent-authored roles: pad / lead / bass / drums.
Analyzer issues: 0.
Dreamy pad centroid after final palette QA: 2443.3 Hz.
Stereo width: 0.931.
The drum palette reduces snare high-band ratio from 0.245 to 0.120.

## Dark Broken Rhythm

Agent-authored roles: pad / bass / drums. Lead and topline remain forbidden.
Analyzer issues: 0.
The hat onset click score changes from 9.25 to 11.42, reflecting the intentionally harder metallic kit.

## Bright Syncopated Pop

Agent-authored roles: pad / lead / bass / drums.
Analyzer issues: 0 after the Agent reduced verse arrangement density rather than dulling the brighter palette.
Lead waveform correlation vs seed patch: 0.279.

## Regression

- pytest: 50 / 50 PASS
- all 3 dogfoods: analyzer issue count 0
- representative repeated render: byte-identical
- SHA-256: `cf3ca62d3641f73da1f2e92fd54880b618c86370df523c729229481f593ddb5b`
