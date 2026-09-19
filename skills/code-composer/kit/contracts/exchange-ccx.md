# `.ccx` Exchange Contract

`.ccx` is a lossless Code Composer checkpoint for internal collaboration. It preserves canonical Music IR, resolved/reference state, revision identity/parentage, contributor metadata, handoff request/status and scope locks.

Imports are fast-forward only. Dirty local state or sibling revisions must block silent overwrite. Revision identity and payload hashes are validated on import.
