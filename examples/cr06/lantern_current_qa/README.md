# CR06 Dogfood — Lantern Current Evidence-first QA

Subject: the **accepted CR04 revised Lantern Current**. CR06 does not rewrite the music.

Hard integrity gate:
- finite audio;
- explicit clipping policy;
- exact source-score binding;
- Song/Score/Execution Plan/realized-IR provenance coherence;
- exact authored-note authority after physical realization;
- mechanically realized violin state.

Musical evidence is descriptive only:
- dynamics;
- spectrum;
- register exposure;
- phrase continuity;
- repetition;
- voice motion;
- section tension/release proxies;
- cross-track close-register masking.

There is deliberately no aggregate quality score, no aesthetic pass/fail, and no
automatic revision.

The dogfood also performs controlled probes:
1. corrupt provenance → hard gate must FAIL;
2. inject clipped sample → hard gate must FAIL;
3. change only `high_register_midi` from 76 to 72 on the same music/render →
   QA comparison must record `target_mutation=true` and must not claim improvement.
