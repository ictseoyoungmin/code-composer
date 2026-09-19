# MIDI Export Workflow

Use MIDI when a collaborator needs note/timing/velocity interchange rather than Code Composer's full editable state.

- `code-composer-midi` exports a single Type 1 MIDI representation.
- `code-composer-collab` additionally includes reference WAV, resolved IR and a manifest.

MIDI does not carry Code Composer's synthesis/DSP faithfully. Never claim General MIDI patches reproduce the reference sound. Use the reference WAV as sound authority.
