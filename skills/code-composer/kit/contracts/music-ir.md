# Music IR Contract

Canonical Music IR is the editable authority. Core surfaces include metadata/seed, transport, tonal context, form, materials, instruments, tracks and mix. Track events and higher-level sources must validate before rendering.

Do not treat resolved IR as a replacement for editable canonical intent when continuing composition work. Preserve deterministic seeds/provenance where reproducibility matters.

## Track gain semantics

`track.gain` is a mixer-level linear amplitude fader. It must not be used as note velocity, strike/bow excitation, brightness, articulation, or any other performance/timbre control. Performance dynamics belong in event velocity / Performance IR / instrument-expression surfaces.

- Legacy/non-graph rendering applies `track.gain` after instrument rendering, engine track post-processing, and legacy per-track insert FX.
- Graph-mode projects keep gain in the mix graph route, also after instrument rendering.
- Therefore changing only track gain should scale the rendered track linearly while leaving the normalized waveform/timbre unchanged, except for later shared nonlinear bus/master processing.


## Track pan semantics

`track.pan` is a mixer-level stereo balance control. It must not be used as an instrument/event pan fallback that collapses an intrinsic stereo source before track processing.

- Legacy/non-graph rendering leaves the instrument's intrinsic stereo image intact through instrument rendering, engine track post-processing and legacy per-track insert FX, then applies `track.pan` once with the shared stereo-balance operator.
- Graph-mode projects continue to apply route pan in the mix graph with the same stereo-balance operator.
- `track.pan == 0` preserves the unpanned stereo image exactly.
- Explicit event `pan`, when authored, remains event-local and is not replaced by track pan.
- Changing only track pan must not force a stereo instrument into a perfectly correlated mono image except at source content that is already mono or at an intentionally extreme downstream routing condition.
