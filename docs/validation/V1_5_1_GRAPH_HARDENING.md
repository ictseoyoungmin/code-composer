# v1.5.1 Graph Hardening

Closed items:

- G01: in-process `pipeline.service`; agent/revision CLI subprocess recursion removed.
- G02: pytest discovery; all script tests now expose pytest tests.
- G03: automation regression restored with non-empty track/bus/master lanes.
- G04: `core` upward imports removed; phrase resolution moved to composition layer; aggregate validation split from core.
- G05: shared `composition.profiles` contract; revision/package APIs explicit; compatibility shims contain no behavior.
- G06: cumulative architecture and structure docs updated.

The hardening release is intended to be behavior-preserving for existing musical output.
