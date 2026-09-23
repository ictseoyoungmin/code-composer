from dataclasses import dataclass
import random
from ..core.theory import quantize_to_scale, scale_degree_to_midi

@dataclass(frozen=True)
class PhraseConfig:
    bars: int = 8
    beats_per_bar: int = 4
    base_degree: int = 1
    octave: int = 4
    density: float = 0.75
    tension: float = 0.6
    cadence_strength: float = 0.85
    max_leap_semitones: int = 7

def _stable_rng(seed: int, namespace: str):
    x = seed & 0xFFFFFFFF
    for ch in namespace.encode("utf-8"):
        x = ((x * 1664525) + ch + 1013904223) & 0xFFFFFFFF
    return random.Random(x)

def _contour(intervals):
    out=[]
    for a,b in zip(intervals, intervals[1:]):
        out.append(1 if b>a else -1 if b<a else 0)
    return out

def motif_identity_score(base, candidate):
    if not base or not candidate:
        return 0.0
    n=min(len(base),len(candidate))
    base=base[:n]; candidate=candidate[:n]
    contour_a=_contour(base)
    contour_b=_contour(candidate)
    contour_match = (
        sum(1 for a,b in zip(contour_a, contour_b) if a==b) / max(1,len(contour_a))
    )
    normalized_a=[x-base[0] for x in base]
    normalized_b=[x-candidate[0] for x in candidate]
    interval_match=sum(1 for a,b in zip(normalized_a, normalized_b) if a==b)/n
    return 0.6*interval_match + 0.4*contour_match

def _transform(intervals, kind, amount=1):
    seq=list(intervals)
    if kind=="identity":
        return seq
    if kind=="sequence_up":
        return [x+amount for x in seq]
    if kind=="sequence_down":
        return [x-amount for x in seq]
    if kind=="reverse":
        return list(reversed(seq))
    if kind=="invert":
        return [-x for x in seq]
    if kind=="fragment":
        keep=max(3, len(seq)//2)
        return seq[:keep]
    if kind=="expand":
        return [x*2 for x in seq]
    return seq

def _clip_degree(degree):
    return max(1, min(14, degree))

def _nearest_scale_midi(root, scale, degree, octave):
    return scale_degree_to_midi(root, scale, _clip_degree(degree), octave)

def _smooth_pitch(prev_midi, target_midi, max_leap):
    if prev_midi is None:
        return target_midi
    while target_midi - prev_midi > max_leap:
        target_midi -= 12
    while prev_midi - target_midi > max_leap:
        target_midi += 12
    return target_midi

def compose_phrase(materials, tonal, seed, motif_id, config: PhraseConfig, namespace="phrase"):
    motif = materials["motifs"][motif_id]
    base_intervals = list(motif["intervals"])
    base_rhythm = list(motif["rhythm"])
    rng = _stable_rng(seed, namespace)

    total_beats = config.bars * config.beats_per_bar
    phrase = []
    cursor = 0.0
    phrase_index = 0
    prev_midi = None
    transform_log=[]

    grammar = [
        ("identity", 1),
        ("sequence_up", 1),
        ("fragment", 1),
        ("sequence_down", 1),
        ("identity", 1),
        ("invert", 1),
        ("sequence_up", 2),
        ("identity", 1),
    ]

    while cursor < total_beats - 1e-9:
        progress = cursor / max(total_beats, 1e-9)

        if progress < 0.25:
            phase="opening"
            kind="identity" if phrase_index==0 else "sequence_up"
            amount=1
        elif progress < 0.60:
            phase="development"
            choices=[("sequence_up",1),("sequence_down",1),("fragment",1),("reverse",1)]
            kind,amount=choices[phrase_index % len(choices)]
        elif progress < 0.85:
            phase="tension"
            choices=[("sequence_up",2),("invert",1),("expand",1)]
            kind,amount=choices[phrase_index % len(choices)]
        else:
            phase="cadence"
            kind="identity"
            amount=1

        transformed=_transform(base_intervals,kind,amount)

        # identity guard: if transform destroys motif too much, fallback to sequence.
        score=motif_identity_score(base_intervals, transformed)
        if kind not in ("fragment",) and score < 0.42:
            kind="sequence_up" if progress < 0.75 else "identity"
            amount=1
            transformed=_transform(base_intervals,kind,amount)
            score=motif_identity_score(base_intervals, transformed)

        transform_log.append({
            "phrase_index": phrase_index,
            "phase": phase,
            "transform": kind,
            "identity_score": round(score, 4)
        })

        local=cursor
        for i,interval in enumerate(transformed):
            if local >= total_beats - 1e-9:
                break
            dur=base_rhythm[i % len(base_rhythm)]
            # sparse opening, denser tension
            density=config.density
            if phase=="opening":
                density*=0.78
            elif phase=="tension":
                density=min(1.0,density*1.18)
            if rng.random() > density and i not in (0, len(transformed)-1):
                local += dur
                continue

            degree=config.base_degree + interval

            # tension lifts register/degree; cadence resolves toward tonic.
            if phase=="tension":
                degree += 1 if (i+phrase_index)%3==0 else 0
            elif phase=="cadence":
                if i >= len(transformed)-2:
                    degree = 2 if i == len(transformed)-2 else 1

            midi=_nearest_scale_midi(
                tonal["root"], tonal["scale"], degree, config.octave
            )
            midi=_smooth_pitch(prev_midi,midi,config.max_leap_semitones)

            velocity=0.58
            if phase=="opening": velocity=0.52
            elif phase=="development": velocity=0.60
            elif phase=="tension": velocity=0.66 + 0.08*config.tension
            elif phase=="cadence": velocity=0.56

            event={
                "start_beat": round(local,6),
                "duration_beats": round(dur,6),
                "midi": int(midi),
                "velocity": round(min(1.0,velocity),4),
                "phrase_phase": phase,
                "motif_id": motif_id,
                "transform": kind,
            }
            phrase.append(event)
            prev_midi=midi
            local += dur

        # phrase unit advances by original motif duration for stable form.
        cursor += sum(base_rhythm)
        phrase_index += 1

    # Strong cadence: guarantee penultimate supertonic -> tonic if room exists.
    if phrase:
        end_beat=total_beats
        cadence_len=min(1.0, config.beats_per_bar/2)
        penultimate=scale_degree_to_midi(tonal["root"], tonal["scale"], 2, config.octave)
        tonic=scale_degree_to_midi(tonal["root"], tonal["scale"], 1, config.octave)
        phrase=[e for e in phrase if e["start_beat"] < end_beat-cadence_len]
        phrase.append({
            "start_beat": round(end_beat-cadence_len,6),
            "duration_beats": round(cadence_len*0.45,6),
            "midi": int(penultimate),
            "velocity": 0.54,
            "phrase_phase": "cadence",
            "motif_id": motif_id,
            "transform": "cadential_2"
        })
        phrase.append({
            "start_beat": round(end_beat-cadence_len*0.5,6),
            "duration_beats": round(cadence_len*0.48,6),
            "midi": int(tonic),
            "velocity": round(0.56+0.1*config.cadence_strength,4),
            "phrase_phase": "cadence",
            "motif_id": motif_id,
            "transform": "cadential_1"
        })

    return {
        "events": sorted(phrase,key=lambda e:(e["start_beat"],e["midi"])),
        "transform_log": transform_log,
        "config": {
            "bars": config.bars,
            "beats_per_bar": config.beats_per_bar,
            "base_degree": config.base_degree,
            "octave": config.octave,
            "density": config.density,
            "tension": config.tension,
            "cadence_strength": config.cadence_strength,
            "max_leap_semitones": config.max_leap_semitones,
        }
    }
