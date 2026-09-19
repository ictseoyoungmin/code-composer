# S8 — Bridge Admittance & Body Feedback Hardening — CLOSED

Date: 2026-09-17
Engine version: 1.17.0

## Scope

S8 closes one narrow bowed-string sound bottleneck: S7's body stage radiated bridge motion but did not mechanically load the string again. S8 adds a weak causal bridge-admittance/body-feedback loop while preserving every older factory preset.

New factory preset:

- `bowed.violin.modeled_admittance@1.0.0`

Preserved presets:

- `bowed.violin.synthetic_warm@1.0.0`
- `bowed.violin.modeled_open@1.0.0`
- `bowed.violin.modeled_continuous@1.0.0`
- `bowed.violin.modeled_coupled@1.0.0`

## Research basis

The implementation follows the established decomposition of bowed-string dynamics + bridge driving-point admittance + body/radiation transfer used in empirical digital-waveguide violin work. S8 does not reproduce a measured named violin; it uses a compact deterministic modal approximation suitable for the existing Code Composer engine.

References:

- Sterling & Bocko, *Empirical physical modeling for bowed string instruments*, ICASSP 2010, DOI 10.1109/ICASSP.2010.5495754.
- Maestre, Scavone & Smith, *Joint Modeling of Bridge Admittance and Body Radiativity for Efficient Synthesis of String Instrument Sound by Digital Waveguides*, IEEE/ACM TASLP 2017, DOI 10.1109/TASLP.2017.2689241.
- Faust Physical Modeling Library, bowed-string/violin components: https://faustlibraries.grame.fr/libs/physmodels/

## Architecture

For the S8 preset only:

```text
G/D/A/E waveguide state bank
        ↓ summed bridge motion
causal violin-family modal body state
        ├─ radiation tap → audio
        └─ admittance tap
               ↓ weak gain + hard velocity bound
          one-sample delay
               ↓
string bridge reflection on next sample
```

The radiation and bridge-admittance taps share the same modal state but use independent gains. This makes the body a causal load on the strings rather than only a downstream EQ/filter.

### Stability boundary

Factory values are deliberately conservative:

- `feedback_gain = 0.006`
- `max_feedback_velocity = 0.012`
- authoring validator caps `feedback_gain <= 0.03`

A 44.1 kHz gain sweep was used to avoid the stronger closed-loop phase changes observed above the weak-coupling region. The factory value is not a realism score; it is a stable starting point.

## Causal-control evidence

The S8 audition phrase realizes `G → D → A → E → E`.

- S7 `modeled_coupled` WAV SHA-256: `55a43efd22104fb636910419c62cb88c1cf3513f932748a923418a8c7d57da9c`
- S8 `modeled_admittance` WAV SHA-256: `8fe48c1608d20b40f91b67d85fe978dbe0a284a77486caca4afdd304780b9cd3`
- S8 identical body model with `feedback_gain=0` SHA-256: `a7ac7bb88f35f4ddad8c8663bdb7b6149908336a23e564793a034555422821f1`
- feedback-on vs feedback-zero correlation: `0.9617785710`
- feedback-on vs feedback-zero difference RMS: `0.0113643921`

The radiation coefficients remain unchanged in the on/off control; only the body-to-string feedback gain changes. Therefore this difference is evidence that the closed loop affects string evolution, not merely catalog metadata.

These metrics are structural evidence only. They are not a perceptual claim that S8 is a perfect acoustic violin.

## Backward compatibility

S7 `bowed.violin.modeled_coupled` rendered from S8 code remains byte-identical to the original S7 closure WAV:

`55a43efd22104fb636910419c62cb88c1cf3513f932748a923418a8c7d57da9c`

Historical v1.16 final dogfood also remains byte-identical:

- A: `93aa85955b7aa8715b65721bc6388310be87006666cb9d7241889d66993116ba`
- B: `7d18321f4986c324b75e2ae45e88cc061e8409dcaa16ae0b051bf4998b368377`
- C: `db524b79b30fbd3d79fa97b157ddb83bb84c71d71cbf09d7c48c391aa3a3834f`

## Validation

- S8 focused: **17 / 17 PASS**
- bowed/violin group: **48 / 48 PASS**
- remaining source regression: **317 / 317 PASS**
- source total: **365 / 365 PASS**
- clean-installed bowed/violin: **48 / 48 PASS**
- clean-installed remainder: **317 / 317 PASS**
- clean-installed total: **365 / 365 PASS**
- bowed-waveguide focused coverage: **93.4540%**
- standalone self-check: **PASS**
- isolated Skill validation: **PASS**
- compileall: **PASS**
- import sweep: **124 modules including package root / 0 failures**
- static graph: **124 modules / 180 internal edges / 0 cycles**
- clean wheel SHA-256: `98531d67bfd65e04606857565b4ad5b89a105077666e0c4e30ddbb4c79422643`
- clean-installed S8 audition equals source audition: **YES**

The complete suite is split into bowed/violin and remainder groups for closure execution because a single chained pytest process can exceed the execution harness time limit even though the two groups complete normally when run independently.

## Packaging

- standalone Skill: **191 files**
- Codex plugin: **193 files**
- Claude plugin: **193 files**
- forbidden build/cache/audio/MIDI artifacts inside installed Skill: **0**
- Codex Skill subtree: **191 / 191 byte-exact**
- Claude Skill subtree: **191 / 191 byte-exact**

Artifact hashes:

- standalone Skill: `348824ba2ec7d088a02479c25c3206393c7205ffca88591e9cbf3d9c411413e6`
- Codex plugin: `9b8c478bf9e3b9247a52c7ef7f9b3d06ce7f9410f9c178285920f235a4e00aa5`
- Claude plugin: `dcbdf96c751e6c78cb0ddae893d0a37e34dbc1ae6f7f61ffd507bca3a9b27ea3`

## Non-goals / still open

S8 does not claim:

- measured fitting to a specific physical violin,
- continuous physical double-stop coupling,
- harmonics or pizzicato,
- ricochet/spiccato bounce mechanics,
- MusicXML/engraving,
- finite-element bridge/soundbox simulation,
- perceptual equivalence to a professional sampled violin.

S8 is CLOSED at the intended bridge-admittance/body-feedback boundary.
