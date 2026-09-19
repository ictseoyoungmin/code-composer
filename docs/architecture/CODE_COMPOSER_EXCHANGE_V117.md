# Code Composer v1.17 M2 — Code Composer Exchange Package

## Purpose

M2 adds a lossless collaboration boundary for **Code Composer user ↔ Code Composer user** work.
It is distinct from the M1 MIDI collaboration bundle, which is a delivery/interchange representation for external DAWs and collaborators.

```text
Person A / Code Composer
  ↓ checkpoint
song-r1.ccx
  ↓ import
Person B / Code Composer
  ↓ edit canonical Music IR
  ↓ checkpoint
song-r2.ccx
  ↓ fast-forward import
Person A / Code Composer
```

The canonical editable authority remains `composition/music_ir.json`. MIDI is not used as the internal exchange authority.

## `.ccx` container

`.ccx` is a ZIP-based, validated container with a strict v1 member set:

```text
manifest.json
composition/
  music_ir.json
  resolved_ir.json
  plan.json          # optional
  brief.json         # optional
provenance/
  revisions.json
handoff/
  handoff.json
audio/
  reference_mix.wav
```

Every payload member is SHA-256 covered by `manifest.json`. The importer rejects unknown members, unsafe paths, missing required members, malformed JSON, broken revision chains, and hash mismatches.

## Checkpoint semantics

Exporting from an imported exchange workspace creates a new revision and checkpoints that workspace to the exported state. The workspace keeps hidden local exchange metadata under `.code-composer/` so that the next handoff can verify its parent and the exact baseline used for scope-lock comparisons.

A revision records:

- `revision_id`
- `parent_revision_id`
- `author`
- `created_at`
- `message`
- state hashes for canonical Music IR, resolved IR, reference mix, and handoff
- optional plan/brief hashes

`revision_id` is content-addressed from durable provenance and state hashes. Wall-clock `created_at` is not part of the revision identity.

## Fast-forward only

M2 deliberately does **not** implement automatic musical merge.

Incoming import is accepted when:

1. the destination is an empty new exchange workspace, or
2. the incoming revision is already the current clean head (idempotent re-import), or
3. the incoming `parent_revision_id` equals the current clean workspace head (fast-forward).

If both collaborators checkpoint children from the same parent, importing one branch into the other raises `DIVERGED HANDOFF` instead of overwriting musical work.

If the local workspace has uncheckpointed changes, incoming import is rejected until those changes are checkpointed.

## Handoff intent and scope locks

Each revision carries structured handoff intent:

```json
{
  "format": "code-composer-handoff/v1",
  "status": "working",
  "requested_changes": ["tighten the pre-hook transition"],
  "locked_scopes": ["track:bass", "section:intro"],
  "notes": ["keep the current low-end identity"]
}
```

Supported lock scopes:

- `transport`
- `tonal`
- `form`
- `mix`
- `arrangement`
- `performance_ir`
- `track:<track_id>`
- `instrument:<instrument_id>`
- `section:<section_id>`

When a collaborator checkpoints a child revision, M2 compares each locked scope against the imported parent baseline. A changed locked scope raises `ScopeLockViolation`.

Locks are collaboration constraints, not new composition-engine heuristics. The deterministic runtime still executes explicit structured Music IR only.

## CLI

Create a root exchange package:

```bash
code-composer-exchange export song.json song-r1.ccx \
  --author "Producer A" \
  --message "first internal handoff" \
  --request "review pre-hook" \
  --lock track:bass
```

Receive it:

```bash
code-composer-exchange import song-r1.ccx work/song
```

After editing `work/song/composition/music_ir.json`, checkpoint a child revision:

```bash
code-composer-exchange export work/song song-r2.ccx \
  --author "Producer B" \
  --message "reworked pre-hook" \
  --status review
```

Inspect/validate without importing:

```bash
code-composer-exchange inspect song-r2.ccx
```

For a standalone child file that is not an imported workspace, an explicit parent package can be provided with `--parent parent.ccx`.

## Boundary with external delivery

```text
Internal collaboration authority
  .ccx
  canonical Music IR + provenance + handoff + exact reference render

External delivery authority
  M1/M3 delivery surface
  MIDI + reference audio (+ future stems) + delivery manifest
```

M2 does not import arbitrary MIDI back into Music IR and does not merge divergent musical branches automatically.
