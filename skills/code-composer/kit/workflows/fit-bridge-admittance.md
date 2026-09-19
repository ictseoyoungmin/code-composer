# Fit Measured Bridge Admittance

Use this workflow only when an explicit bridge mechanical response is available. Do not use ordinary violin audio as if it were bridge admittance.

1. Confirm the source quantity: force input at/near the bridge and bridge velocity response, with sample rate and measurement provenance known.
2. Keep measurement preprocessing explicit. If the acquisition protocol calls for repeated-impact averaging, force normalization, minimum-phase conversion, or tail cropping, perform/record those steps before fitting.
3. Run `code-composer-admittance-fit INPUT.wav PROFILE.json --order N --source-id ...`. Start with a compact order and increase only when fit evidence supports it.
4. Inspect `fit_metrics.nmse_time`, pole stability, source provenance, and order. Do not equate a low time-domain NMSE with perceptual violin realism.
5. Attach the profile only to `bowed_waveguide_graph.body.bridge_feedback.fitted_response`. Keep `feedback_gain` weak and bounded.
6. Compare feedback-off vs feedback-on render evidence and verify finite/deterministic output.
7. Do not publish a named factory preset unless the underlying measurement identity and redistribution rights are verified.

This workflow fits mechanical bridge admittance. It does not fit radiation transfer, microphone position, room acoustics, or a player's performance.
