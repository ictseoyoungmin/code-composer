NOTE_TO_PC = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11
}

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "natural_minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
}

def midi_to_hz(midi: float) -> float:
    return 440.0 * (2.0 ** ((midi - 69.0) / 12.0))

def scale_pitch_classes(root: str, scale: str) -> set[int]:
    base = NOTE_TO_PC[root]
    return {(base + x) % 12 for x in SCALES[scale]}

def quantize_to_scale(midi: int, root: str, scale: str) -> int:
    pcs = scale_pitch_classes(root, scale)
    candidates = [m for m in range(midi - 6, midi + 7) if m % 12 in pcs]
    return min(candidates, key=lambda m: (abs(m - midi), m))

def scale_degree_to_midi(root: str, scale: str, degree: int, octave: int = 4) -> int:
    # degree is 1-based and can exceed one octave
    intervals = SCALES[scale]
    root_pc = NOTE_TO_PC[root]
    idx = degree - 1
    octave_add, scale_idx = divmod(idx, len(intervals))
    return 12 * (octave + 1 + octave_add) + root_pc + intervals[scale_idx]

def triad_from_degree(root: str, scale: str, degree: int, octave: int = 4, seventh: bool = False):
    notes = [
        scale_degree_to_midi(root, scale, degree, octave),
        scale_degree_to_midi(root, scale, degree + 2, octave),
        scale_degree_to_midi(root, scale, degree + 4, octave),
    ]
    if seventh:
        notes.append(scale_degree_to_midi(root, scale, degree + 6, octave))
    return notes

def nearest_inversion(chord: list[int], center: int) -> list[int]:
    candidates = []
    base = sorted(chord)
    for inv in range(len(base)):
        notes = base[inv:] + [x + 12 for x in base[:inv]]
        for shift in (-24, -12, 0, 12, 24):
            shifted = [n + shift for n in notes]
            score = abs(sum(shifted) / len(shifted) - center)
            candidates.append((score, shifted))
    return min(candidates, key=lambda x: x[0])[1]

def voice_leading_cost(a: list[int], b: list[int]) -> float:
    aa = sorted(a)
    bb = sorted(b)
    n = min(len(aa), len(bb))
    if n == 0:
        return 0.0
    return sum(abs(aa[i] - bb[i]) for i in range(n)) / n
