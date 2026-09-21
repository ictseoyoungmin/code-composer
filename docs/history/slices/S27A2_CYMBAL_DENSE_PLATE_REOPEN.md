# S27-A2 — Cymbal Dense Plate Reopen

Status: ENGINEERING CANDIDATE / perceptual gate OPEN

## Why S27-A was reopened

S27-A restored a real stick-force onset, but its sparse coherent modal bank produced an audible `bell/gong` (`댕`) pitch instead of a cymbal-like `clang/crash` (`챙`) field. The failure was not contact strength; it was modal dimensionality and strike-zone radiation.

## A2 correction

- preserve the S27-A short velocity-dependent stick-force pulse;
- replace sparse physical_v1 partials with physical_v2 dense inharmonic plate modes;
- preserve one impact time origin while allowing localized mode-shape sign differences and rapid de-phasing;
- suppress low-order radiation for ride-bow and crash-edge/shoulder strikes;
- preserve R2/R3 short-tail limits and S19 kick/snare/closed-hat byte identity;
- do not use external samples, room IRs, measured modal tables, or copied third-party source.

## Listening gate

A2 is not CLOSED until the isolated ride/crash and real 125 BPM groove are heard as stick-on-cymbal rather than bell/gong.

## Verification

- full 76-file partitioned suite: 494/494 PASS
- focused S27-A/A2 + S26/S25/factory/closure regression included
- standalone skill validation / compileall / plugin build: PASS
