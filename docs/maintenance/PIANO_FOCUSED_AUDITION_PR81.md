# PR81 third audition: foreground piano, not another treble cut

Status: **listening acceptance OPEN**, no main merge or release. The user heard an
improvement in round 2 but still found the synthesized tail distracting.

## Scope and preserved authority

The previous round (`b9a3e1c`) used a passive coupled-string model. Its default
fixed inter-string excitation phases (0, 0.53, 1.06 radians before common offsets)
also seed differential-mode energy at the instant of the hammer strike. The new
`unison_hammer_phase_alignment` acoustic control reduces this initial spacing,
continuously over MIDI 60–84, while keeping its mean and independently authored
per-strike phase jitter. It does not change pitch, detuning, string lifetimes,
note timing, velocity, pedal events, or the coupled solver's passivity.

This is a reduced excitation model, not measured reconstruction of a real hammer.
The control is explicit, finite and bounded to [0,1]. Absent/zero takes the exact
round-2 path. An initial global experiment changed an existing S28G comparison;
it was rejected, not accommodated by weakening that test. All existing factory
preset definitions are retained.

`piano.concert_grand_focused` is a separate audition preset using alignment 1,
0.25-cent detuning (not zero), revised spectral/decay balance and restrained
reinforcement. Its output gain reserves peak headroom instead of relying on
per-note peak normalization. These are explicit authored sound parameters, not
an analyzer rewriting music or a hidden role/style mapper. Runtime remains
sample-free. This is a candidate voice, not a claim of sampled-grand fidelity.

The strict portable/package design schemas lacked 14 controls already implemented
in the runtime (strike identity, unison decoherence and explicit damper controls).
Both now match `ACOUSTIC_CONTROL_SPECS`, including the new control; unknown fields
remain rejected. The catalogue gains exactly one preset (38 to 39). Preview epoch
4 rejects earlier cache generations.

## Actual listening path

`tools/render_piano_focus_audition.py` loads and materializes native factory presets,
resolves the native piano design, renders explicit sustain-pedal track controls,
then applies the shared soundboard. No replacement acoustic implementation or
mock resolver is used for the delivered WAVs. The short original phrase, touch
probe and sustained-note probe are developer evidence outside the installed Skill.
No existing showcase/test composition was used as musical material.

Both versions use identical events/seeds. They are delivered at measured **-22.0
LUFS**, using one fixed gain per whole clip, never per-note gain or compression.
FFmpeg remeasures the PCM16 files after matching. There is no master EQ, room
reverb, extra synthesizer, SoundFont or recorded audio in these outputs.

The A/B is **round-2 engine + Natural factory preset** versus **Focused preset**.
It is not the old four-note diagnostic patch from the first two conversations.
Raw float WAVs, resolved patches, event hashes and gain records are retained in
the evidence bundle. An alignment-off focused ablation is measured separately.

## Descriptive measurements, not an aesthetic score

48 kHz, velocity .75, seed 2820, 2.5-second held notes, note-local sustain pedal,
native factory graphs and shared soundboard. Every interval is relative to that
note's first 50 ms. Values below are Focused minus previous Natural, in dB.

| MIDI | 50–300 ms | 300–800 ms | 1.5–2.5 s |
| --- | ---: | ---: | ---: |
| 72 | +0.44 | +2.36 | -10.77 |
| 76 | +0.71 | +3.22 | -11.07 |
| 84 | +1.51 | -0.71 | -18.59 |
| 88 | +1.87 | -3.54 | -18.07 |

The middle treble body is retained better while late energy decreases. The very
high E6 body still decreases: this tradeoff must not be hidden by an attack-only
metric. These are full-band measurements; no claim is made that they isolate
only unpleasant noise. They also include explicit preset changes, not just the
phase-control effect. With the Focused parameters held fixed, alignment alone
reduces late attack-relative RMS by about 2.75/6.34/7.70/6.61 dB respectively.

## Verification

- Exact source was obtained from the connected repository's pinned CI artifact;
  round-2 piano.py matched the previous evidence source byte-for-byte.
- Native factory resolution exactly matched the graphs reconstructed during
  initial offline probes; delivered audio was then regenerated through the real
  installed-source package path.
- Local full suite: **1075 passed in 108.85 s**, including the existing S28G
  modulation/attack tests unchanged. The first local invocation omitted
  PYTHONPATH for subprocess CLIs; it was stopped and rerun with the CI environment.
- New tests cover schema/runtime parity, bounds, phase mean/energy, zero-default
  sample compatibility, single/two-string preservation, unchanged frequencies,
  dynamics/headroom, deterministic pedal release and shared-soundboard rendering.
- 32 old-source/new-source paired renders of Natural/Subtle at 24/48 kHz, with
  pedal and explicit-control variants, were exactly sample-identical.
- Skill, plugin, version and release builds passed locally. Remote CI status is
  reported on the PR rather than asserted in advance here.

No human listening approval is claimed. The user's original composition was not
provided. A local sample-based General MIDI piano was used only as an exploratory
reference (TimGM6mb via FluidSynth, reverb/chorus disabled), not as a calibrated
recording of a grand piano. Neither its samples nor derived waveform/envelope
assets are embedded in the new engine or the deliverable. The intended external
Salamander recordings could not be downloaded in this execution environment;
therefore this work does not claim an original-recording A/B or physical fidelity.

General acoustic context, not source code copied into the implementation:
- Aalto, Analysis and Synthesis of the Piano Sound:
  https://www.aalto.fi/en/department-of-signal-processing-and-acoustics/analysis-and-synthesis-of-the-piano-sound
- D. Russell, Hammer nonlinearity, dynamics and the piano sound:
  https://www.acs.psu.edu/drussell/Piano/Dynamics.html
