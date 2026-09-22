# S27-L — Full-Song Authenticated Drum Chain / Production Closure

Status: **ENGINEERING CANDIDATE / PERCEPTUAL GATE OPEN**  
Date: 2026-09-20

## Why this slice exists

S27-B R1 removed the production-listening felt/fabric artifact from the two-cymbal hi-hat and S27-K R2 closed the authored foot-chick/splash path. The roadmap principle after these engine fixes is not to preselect another synthesis feature. The complete accepted drum chain must first survive a real multi-role song, and the next bottleneck must come from listening evidence.

## Boundary

No new synthesis model is introduced. The slice locks and dogfoods:

- S19 kick;
- S27-A2 ride/crash;
- S27-B R1 two-plate modal-contact hi-hat;
- S27-C center/ghost/rimshot/cross-stick snare;
- S27-D high/mid/floor tom family;
- S27-F four-limb evidence;
- S27-G shared kit/room integration;
- S27-H/I/J persistent/continuous pedal state;
- S27-K R2 authored chick/splash consequences.

Piano, modeled electric-finger bass and articulated modeled violin provide a real production context rather than a drum-only loop. The runtime does not infer genre-specific hi-hat grammar; every pedal control and drum event remains authored.

## Production dogfood — Cobalt Meridian

- 24 kHz
- 112 BPM
- 12-bar compressed full form: **Intro → Verse → Pre → Chorus → Outro**
- symbolic duration: `25.7143 s`
- rendered duration with tails: `27.8339 s`
- tracks: acoustic piano / modeled bass / articulated violin / authenticated drums
- event counts: piano `109`, bass `46`, violin `42`, drums `175`
- master RMS: `0.1536883`
- master peak: `0.7935846`
- clipped sample ratio: `0`

The pre/chorus transition deliberately exercises closed → half-open → open hi-hat, explicit pedal close/reopen, crash replacement, ride timekeeping, left-foot chicks, rimshots and a high→mid→floor tom fill inside the full mix.

## Drummer evidence

- events: `175`
- hands: `118`
- right foot: `46`
- left foot: `11`
- `playable=true`
- `strained=false`
- HIGH/MEDIUM/LOW issues = `0/0/0`

An initial full-form draft exposed a real final-bar travel/rate strain where a floor-tom move followed a backbeat too closely. The arrangement was corrected by yielding that final backbeat to the fill rather than weakening the validator.

## Reproducibility

`tools/s27l_full_song_drum_chain.py` owns the complete authored production score and renders stems separately at 24 kHz before deterministic summing/limiting. This avoids environment command-duration limits without changing the audio contract.

Primary listening files:

1. `01_COBALT_MERIDIAN_FULL_PRODUCTION.wav`
2. `04_PRE_TO_CHORUS_PRODUCTION_GATE.wav`
3. `02_DRUM_STEM.wav`
4. `03_NO_DRUMS_STEM.wav`

## Closure gate

Do not mark S27-L CLOSED from metrics alone. User listening must decide whether:

1. the drum kit reads as one coherent production instrument rather than independent synthesized lanes;
2. the new metal hi-hat stays free of the former felt/fabric texture over a longer song;
3. pedal chick/splash remains natural inside the mix and does not become a special-effect layer;
4. snare, toms, ride/crash and kick retain identity without fighting piano/bass/violin;
5. section development feels musical rather than a no-op loop;
6. the next audible bottleneck, if any, is identified from this production rather than guessed in advance.

## Current canonical interpretation

The status above records the state **at the S27-L checkpoint** and is intentionally not rewritten as a retroactive perceptual PASS.

S27-L is no longer an active gate. The authenticated drum chain continued into S27-M R2 full-song production integration, where the user completed production listening and marked the ensemble/full-song gate **PASS / CLOSED** on 2026-09-22. Later S29-S31 full-song closures retain that accepted drum baseline.

Current role: **historical production checkpoint / active gate superseded by later closed full-song evidence**.
