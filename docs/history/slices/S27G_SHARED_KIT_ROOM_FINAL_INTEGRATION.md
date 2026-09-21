# S27-G — Shared Kit / Room Final Integration

Status: **ENGINEERING CANDIDATE / PERCEPTUAL GATE OPEN**

## Goal

Close the drum-authenticity chain at the kit level without reopening any approved dry source. S27-G must make S19 kick + S27-A2 cymbals + S27-B hi-hat + S27-C snare + S27-D toms sound like one drummer recorded in one compact studio space, while preserving the attack authority that was lost in the earlier S20-S24 direction.

S27-F four-limb validation remains evidence-only and is used to qualify the flagship performance before rendering.

## Locked source boundary

S27-G does **not** change `audio/percussion.py` or any S27-D dry-source block. The new preset copies the entire S27-D `drum_graph` exactly except for `kit_integration`.

New factory preset:

`drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated@1.0.0`

The direct rendered bytes of kick, ride/crash, six hi-hat states, four snare articulations and high/mid/floor tom articulations therefore remain identical to S27-D before track integration.

## Problem found in S26 room integration

S26 was built before the authenticated articulation vocabulary existed. Its room-send logic understood only legacy `kick/snare/hat/ride/crash`; later events fell through broad prefix/default weights.

That meant:

- ghost and rimshot excited the room almost like ordinary snare hits;
- tight/open/pedal hi-hat states did not carry their actual contact-state difference into the shared room;
- high/mid/floor toms were all generic fallback events;
- the overhead direct branch started at zero delay, effectively reinforcing the close signal at the same instant instead of representing microphone propagation.

The problem was no longer weak source synthesis. It was an outdated kit-integration model consuming the corrected source.

## S27-G integration model

### 1. Articulation-aware room excitation

`kit_integration.articulation_room_weights` may explicitly weight already-authored drum articulations. It never creates or rewrites events.

Current acoustic hierarchy:

- rimshot > center > ghost/cross-stick room drive;
- open > half-open > closed > tight-closed hi-hat room drive;
- foot splash > pedal chick;
- floor > mid > high tom body excitation;
- crash remains a strong room accent; ride remains restrained timekeeping.

Old presets without this map retain the pre-S27-G room-weight fallback byte-exactly.

### 2. Propagated overhead

S27-G adds `overhead_predelay_ms=2.9` only in the new preset. The dry close branch stays zero-delay and remains the attack anchor. The overhead image arrives a few milliseconds later, then feeds deterministic early reflections.

This is a compact propagation cue, not a claim about a measured microphone distance or named studio.

### 3. Early-reflection-first room

Compared with S26:

- room RT60 is shortened;
- late-field mix is reduced and darkened;
- early reflection share is increased;
- constant room-send floor is reduced;
- authored velocity/articulation controls the remaining room excitation more strongly.

The room is intended to support a good dry kit, not manufacture realism with a long tail.

### 4. Lighter bus/body glue

The first S27-G tuning still raised sustained RMS enough that RMS-matched kick attack fell too far behind the dry source. That candidate was rejected internally.

The accepted engineering candidate reduces overhead/room/body-parallel level and parallel-bus mix while keeping the propagation and articulation-aware logic. The whole 16-bar integrated render now has nearly the same raw RMS as the dry source, so perceived integration is not bought by hidden loudness or heavy compression.

## Flagship performance gate

24 kHz / 118 BPM / 16 bars / 269 explicit drum events.

The authored performance contains:

- closed/tight hi-hat pocket;
- center + ghost snare;
- cross-stick verse with half/open hi-hat;
- ride section with left-foot hi-hat chicks;
- rimshot power chorus;
- crash section accents that replace the timekeeping cymbal at the downbeat;
- high -> mid -> floor tom fills;
- final tom fill + kick/crash punctuation.

S27-F result before rendering:

- `playable=true`
- `strained=false`
- HIGH/MEDIUM/LOW = `0/0/0`
- 189 hand events / 65 right-foot events / 15 left-foot events.

## Integration evidence

Same authenticated dry source, RMS-matched where noted:

- whole-render raw RMS: dry `0.15587`, S26 `0.15365`, S27-G `0.15593`;
- final crash first 30 ms: S26 `0.4422` -> S27-G `0.4933` (dry `0.5146`);
- final floor-tom body 20-180 ms: S26 `0.2939` -> S27-G `0.3214` (dry `0.3376`);
- final crash 300-900 ms: S26 `0.0905` -> S27-G `0.0867` (dry `0.0839`).

So the candidate recovers impact/body while keeping shared decay close to the dry-source tail instead of returning to a long tonal room/cymbal smear.

Old S26 integration behavior was also re-rendered from the S27-F and S27-G worktrees with an identical fixed input/config; SHA-256 remained identical (`eae4dd1be89db6d4de346ab5db3ac362b8a7cc6b606c7d2c28808bdf6d12faa2`).

## Closure gate

S27-G is not CLOSED until listening confirms:

1. the dry-authenticated kit still leads every hit;
2. the room makes the kit feel physically shared rather than simply wetter;
3. rimshots/crashes feel powerful without zero-time doubling or long wash;
4. open hi-hat and floor tom naturally excite more space than tight-hat/ghost notes;
5. fills move through the kit without sounding like unrelated isolated instruments;
6. the S26 -> S27-G RMS-matched comparison is an audible improvement in realism/power, not merely a level or stereo-width change.
## Perceptual closure replay — 2026-09-20

Repository-hygiene clean candidate was used to reconstruct the documented 16-bar flagship contract as a reproducible tool rather than relying on missing generated WAVs.

- 24 kHz / 118 BPM / 16 bars / 269 events.
- S27-F replay: 189 hands / 65 right foot / 15 left foot; `playable=true`, `strained=false`, HIGH/MEDIUM/LOW=`0/0/0`.
- whole-render raw RMS: dry `0.14153`, S26 `0.14142`, S27-G `0.14336`; A/B files RMS-match both integrated candidates to dry.
- final crash first 30 ms, RMS-matched: dry `0.5457`, S26 `0.4727`, S27-G `0.5112`.
- final floor-tom body 20–180 ms: dry `0.3998`, S26 `0.3516`, S27-G `0.3928`.
- final crash 300–900 ms: dry `0.0561`, S26 `0.0667`, S27-G `0.0562`.
- rimshot first 30 ms remains intentionally flagged for listening: S26's zero-delay room reinforcement is stronger numerically, while S27-G returns the onset closer to the authenticated dry hit and removes same-time doubling. No retune is accepted without perceptual evidence.

The RMS-matched flagship was accepted by user listening on 2026-09-20. **S27-G is CLOSED** and becomes the shared-kit/room baseline for later drum-state work.

## User perceptual closure

- PASS: 2026-09-20.
- The S26 → S27-G RMS-matched 16-bar flagship passed the listening gate.
- The previously flagged rimshot onset did not require a reopen after listening.
- Next active slice: S27-H stateful hi-hat closure/choke.
