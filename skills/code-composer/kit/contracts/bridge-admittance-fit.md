# Bridge Admittance Fit Contract

## Quantity

Input is a real discrete impulse response representing mechanical bridge admittance: bridge velocity divided by applied force. Recorded acoustic audio is not interchangeable with this quantity.

## Profile

Format: `code-composer-bridge-admittance-era/v1`.

Required runtime fields are reference sample rate, stable discrete poles, matching residues, direct term, and output scale. Runtime sample-rate adaptation preserves identified modal frequency and decay through pole remapping.

## ERA fitting

The fitter constructs shifted Hankel matrices from the impulse-response Markov parameters, performs an SVD truncation to the requested/numerically supported order, derives a state realization, diagonalizes it, and emits a pole/residue representation for O(M) runtime evaluation. Unstable fitted poles may be conservatively clamped below the unit circle and the count is recorded.

## Separation of mechanical and acoustic response

A fitted bridge-admittance profile may drive the weak feedback path in `bowed_waveguide`. It MUST NOT be treated as a microphone/radiation impulse response. Body radiation remains a separate output stage.

## Provenance

`source` metadata should identify the measurement or local asset sufficiently for reproducibility. Code Composer does not infer instrument identity from the response. Factory distribution of a measured profile requires explicit source and redistribution provenance.
