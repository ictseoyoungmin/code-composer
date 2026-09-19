# v1.17 M2 — Code Composer Exchange Package Closure

Status: **CLOSED**  
Release line: **v1.17.0**  
Prior slices: **M1 CLOSED; v1.16.0 and Legacy Cleanup L0–L5 remain CLOSED**

## Scope

M2 adds a lossless Code Composer-to-Code Composer collaboration checkpoint. It does not add MIDI import, automatic musical merge, new composition heuristics, or new DSP.

Canonical path:

```text
Code Composer user A
  → canonical Music IR
  → code-composer-exchange export
  → .ccx checkpoint
  → code-composer-exchange import
  → Code Composer user B
  → explicit Music IR revision
  → next .ccx checkpoint
```

The M1 MIDI/reference bundle remains the external interchange/delivery surface. `.ccx` is the internal editable collaboration authority.

## Implemented

- strict ZIP-based `code-composer-exchange/v1` container (`.ccx`)
- required canonical Music IR + exact resolved IR + exact reference WAV
- optional Composer plan and Composition Brief preservation
- SHA-256 coverage of every package payload member
- content-addressed single-parent revision IDs
- revision history with author, parent, timestamp, message, and state hashes
- structured handoff status / requested changes / notes
- scope locks for transport, tonal, form, mix, arrangement, performance IR, track, instrument, and section scopes
- lock enforcement against the imported parent baseline at child checkpoint
- clean fast-forward import only
- dirty-workspace refusal
- sibling/divergence refusal (`DIVERGED HANDOFF`)
- idempotent same-revision re-import
- strict archive member/path validation and tamper detection
- deterministic archive bytes when provenance timestamp/content are fixed
- `code-composer-exchange export|import|inspect` CLI

Automatic merge is deliberately absent. A divergent branch is surfaced to the humans/agents instead of silently reconciling musical intent.

## Two-person clean-wheel dogfood

The final wheel was installed into a target outside the repository. Code Composer itself was loaded only from that installed wheel target; the environment supplied the already-provisioned NumPy/SciPy runtime dependencies.

Dogfood sequence:

1. Producer A exported root `r1.ccx`.
2. A and B independently imported r1 into separate workspaces.
3. B edited canonical `composition/music_ir.json`.
4. B exported/checkpointed child `r2.ccx` with `status=review`.
5. A, still at r1, imported r2 as a legal fast-forward.
6. `inspect` validated the received package and revision chain.

Evidence:

```text
r1 revision
5796838a1aafa2e6c442f79842b56e2113161ff20f0c294eff2e4a5cca8b4374

r2 parent
5796838a1aafa2e6c442f79842b56e2113161ff20f0c294eff2e4a5cca8b4374

r2 revision
9597d2a25d864356baed99eab82855369e4a64eca503b17d4bf1a3c067af1670
```

Package SHA-256:

```text
r1.ccx  7b63e5a47c487ce9341fa4d6b191bc40a68cf747f8e1e98e10eef7d5a48e0043
r2.ccx  ae1626ddfcc01daba8516d0454d24fba23985d0bf0cfc967265515d62886714d
```

## Validation

```text
Focused M2                       15 / 15 PASS
Full regression                 283 / 283 PASS
Total coverage                  88.774885% (89% displayed)
exchange/package.py coverage    85.399449%
app/exchange_cli.py coverage    97.368421%
compileall                      PASS

Import modules                  105
Import failures                   0
Static modules                  106
Static import edges             138
Cycles                            0
```

Package build/install:

```text
wheel             code_composer-1.17.0-py3-none-any.whl
wheel SHA-256     5d816da55180c2da3cc577a33386f3604eee0a8604aff904588b6106605802dc
metadata version  1.17.0
entry points      5 / 5 present
exchange CLI      executed from clean installed target
```

Existing M1 runtime preservation:

```text
existing M1 src .py files changed   0
existing M1 src .py files missing   0
new runtime files                   3
  app/exchange_cli.py
  exchange/__init__.py
  exchange/package.py
```

The only active packaging-surface addition is the `code-composer-exchange` console entry point.

## Audio compatibility

The clean-installed wheel rerendered all three v1.16 final dogfood cases from their retained Music IR. All outputs are byte-identical to the existing closure baseline:

```text
A  93aa85955b7aa8715b65721bc6388310be87006666cb9d7241889d66993116ba
B  7d18321f4986c324b75e2ae45e88cc061e8409dcaa16ae0b051bf4998b368377
C  db524b79b30fbd3d79fa97b157ddb83bb84c71d71cbf09d7c48c391aa3a3834f
```

The v1.15 representative legacy render also remains byte-identical:

```text
589ac3efdc466a1a7c191caa0e614a63b1a28e4dea566b08164df3730f4490e0
```

## Closure decision

M2 is **CLOSED**.

Internal collaboration now has a lossless editable exchange boundary. M3 can focus on external professional delivery (per-track MIDI, stems, richer delivery manifest/metadata) without overloading `.ccx` or turning MIDI into the internal authority.
