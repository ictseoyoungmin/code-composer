# Example and Fixture Policy

**Examples teach operation, never taste.**

## Allowed inside the installed skill

- command invocation examples;
- workflow diagrams;
- schemas and empty templates;
- tiny synthetic fixtures used to prove protocol behavior;
- placeholder names and non-musical metadata.

## Forbidden inside the installed skill

- completed songs or polished excerpts;
- showcase WAV/MP3/FLAC audio;
- polished MIDI or memorable hooks;
- dogfood compositions;
- stylistically meaningful chord progressions, bass grooves, drum patterns or arrangements presented as exemplars;
- instructions that say a bundled musical choice is a preferred/default creative choice.

## Fixture constraints

A protocol fixture must be declared synthetic and non-reference, stay minimal, and contain only enough events to test serialization/rendering. Its musical content must not be used as a compositional prior.

When an agent encounters any fixture, treat all note/rhythm/instrument values as arbitrary test data.


## Factory presets

Factory presets are not examples. They may contain sonic engine parameters but must contain no notes, events, motifs, rhythms, chords, progressions, form, or arrangement content. Agent-facing preset catalogs describe capabilities and limitations rather than exposing a completed musical phrase.
