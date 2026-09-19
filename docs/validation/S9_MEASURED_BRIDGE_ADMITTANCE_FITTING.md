# S9 — Measured Bridge-Admittance ERA Fitting — CLOSED

Date: 2026-09-18  
Engine: Code Composer 1.17.0

## Goal

Replace further hand-added body modes with a reproducible path from an **explicit measured mechanical bridge-admittance impulse response** to a compact deterministic runtime model. S9 does not pretend ordinary microphone audio is bridge admittance and does not ship a named measured-violin preset without verified measurement provenance.

## Architecture

```text
measured force -> bridge velocity IR
          |
          v
ERA fit (Hankel + SVD + reduced realization)
          |
          v
code-composer-bridge-admittance-era/v1
  stable poles + residues + direct term + provenance
          |
          v
EraAdmittanceState (O(M), sample-rate adapted)
          |
          v
bowed_waveguide mechanical bridge feedback

body/radiation output remains a separate path
```

New public command:

```bash
code-composer-admittance-fit INPUT_IR.wav OUTPUT_PROFILE.json --order 24 --source-id ...
```

The fitter expects the input WAV to already represent force-normalized bridge velocity. Measurement-specific repeat averaging, force normalization, minimum-phase conversion and noise-tail cropping are deliberately upstream/provenance-visible rather than silently inferred.

## Research basis

- DAFx 2026, *Eigensystem Realization of Violin Bridge Admittances*: ERA is used to derive compact reduced-order state-space models directly from measured bridge-admittance impulse responses.
- Acta Acustica 2026, *Violin “playing-in”*: bridge input admittance was measured with laser Doppler vibrometry and an instrumented impact hammer; the associated acoustics dataset is declared available on Zenodo and processing/access code is public on GitHub.
- The public `hugo-paugesteros/CNSM-dataset` repository confirms an admittance data-access surface, but the exact raw measurement asset and redistribution provenance were not independently imported during S9. Therefore no factory preset is labeled as a measured named violin.

## Validation

- Focused fitter / CLI / integration / Skill surface: **22/22 PASS**
- Source regression: **374/374 PASS** (`57` bowed/violin/fitter + `317` remainder)
- Clean-installed regression: **374/374 PASS**
- Focused new fitter+CLI coverage: **91% combined**
  - `bridge_admittance_fit.py`: **92%**
  - `admittance_fit_cli.py`: **86%**
- Import sweep: **126 modules / 0 failures**
- Static graph: **126 modules / 182 edges / 0 cycles**
- Standalone self-check / isolated Skill validation / compileall: **PASS**
- Public console entrypoints: **9**

Synthetic protocol recovery deliberately contains no musical content. A known six-pole response was recovered with time-domain NMSE **5.56e-25** before WAV quantization. The validation-only closed-loop A/B also proves that attaching the fitted profile changes actual bridge feedback rather than only metadata.

## Backward compatibility

The S8 `bowed.violin.modeled_admittance` path without `fitted_response` was rendered independently under the original S8 source and S9 source. Both raw float buffers have SHA-256:

`c871b3fea30327e73d901c40bba7286fa9486df1bcefe612671acf35002b8f37`

Therefore S9 is opt-in and does not silently alter the S8 modeled preset. Legacy A/B/C closure guards also continue to pass.

## Packaging

- Standalone Skill: **197 files**
- Codex plugin: **199 files**
- Claude plugin: **199 files**
- Forbidden build/cache/audio/MIDI inside Skill: **0**
- Codex embedded Skill: **197/197 byte-exact**
- Claude embedded Skill: **197/197 byte-exact**

## Closure boundary

S9 closes **measurement ingestion + ERA identification + mechanical-feedback runtime integration**. It does **not** close measured-instrument sonic realism because no exact raw public measurement was imported and audited in this slice. The next evidence-based step is to import one redistributable measured bridge-admittance asset with verified provenance, fit it, and audition it as a separately versioned measurement-derived resource.
