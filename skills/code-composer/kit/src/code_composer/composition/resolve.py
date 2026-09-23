from copy import deepcopy
import random

from ..core.ir import validate_ir
from .phrase import PhraseConfig, compose_phrase
from ..core.theory import (
    scale_degree_to_midi,
    triad_from_degree,
    nearest_inversion,
    quantize_to_scale,
)

def _stable_rng(seed: int, namespace: str):
    # Deterministic string mixing independent of Python hash randomization.
    x = seed & 0xFFFFFFFF
    for ch in namespace.encode("utf-8"):
        x = ((x * 1664525) + ch + 1013904223) & 0xFFFFFFFF
    return random.Random(x)

def _section_lookup(ir):
    beats_per_bar = ir["transport"]["beats_per_bar"]
    sections = []
    for sec in ir["form"]:
        start = sec["start_bar"] * beats_per_bar
        end = (sec["start_bar"] + sec["bars"]) * beats_per_bar
        sections.append((start, end, sec))
    return sections

def _section_at(beat, sections):
    for start, end, sec in sections:
        if start <= beat < end:
            return sec
    return sections[-1][2] if sections else {"energy": 1.0}

def resolve_ir(ir: dict) -> dict:
    validate_ir(ir)
    out = deepcopy(ir)
    root = ir["tonal"]["root"]
    scale = ir["tonal"]["scale"]
    seed = ir["meta"]["global_seed"]
    beats_per_bar = ir["transport"]["beats_per_bar"]
    sections = _section_lookup(ir)
    total_bars = max(sec["start_bar"] + sec["bars"] for sec in ir["form"])
    total_beats = total_bars * beats_per_bar

    for track in out["tracks"]:
        source = track["source"]
        stype = source["type"]
        if stype == "resolved":
            continue

        events = []
        rng = _stable_rng(seed, track["id"])

        if stype == "phrase":
            cfg = PhraseConfig(
                bars=int(source.get("bars", 8)),
                beats_per_bar=int(beats_per_bar),
                base_degree=int(source.get("base_degree", 1)),
                octave=int(source.get("octave", 4)),
                density=float(source.get("density", 0.75)),
                tension=float(source.get("tension", 0.6)),
                cadence_strength=float(source.get("cadence_strength", 0.85)),
                max_leap_semitones=int(source.get("max_leap_semitones", 7)),
                gate=float(source.get("gate", 1.0)),
            )
            phrase = compose_phrase(
                ir["materials"], ir["tonal"], seed,
                source["motif"], cfg,
                namespace=f"phrase:{track['id']}"
            )
            events = phrase["events"]
            track["phrase_meta"] = {
                "transform_log": phrase["transform_log"],
                "config": phrase["config"],
            }

        elif stype == "motif":
            motif = ir["materials"]["motifs"][source["motif"]]
            base_degree = source.get("base_degree", 1)
            base_octave = source.get("octave", 4)
            phrase_beats = sum(motif["rhythm"])
            cursor = float(source.get("start_beat", 0))
            repeat_until = float(source.get("until_beat", total_beats))
            phrase_idx = 0

            while cursor < repeat_until - 1e-9:
                sec = _section_at(cursor, sections)
                energy = float(sec.get("energy", 1.0))
                transform_cycle = source.get("transform_cycle", ["identity"])
                transform = transform_cycle[phrase_idx % len(transform_cycle)]
                intervals = list(motif["intervals"])

                if transform == "reverse":
                    intervals = list(reversed(intervals))
                elif transform == "invert":
                    intervals = [-x for x in intervals]
                elif transform == "octave_up":
                    intervals = [x + 7 for x in intervals]

                local = cursor
                for i, (interval, dur) in enumerate(zip(intervals, motif["rhythm"])):
                    degree = base_degree + interval
                    midi = scale_degree_to_midi(root, scale, max(1, degree), base_octave)

                    if source.get("humanize_pitch", False):
                        midi = quantize_to_scale(midi, root, scale)

                    timing_jitter = (rng.random() - 0.5) * float(source.get("timing_jitter_beats", 0))
                    vel_jitter = (rng.random() - 0.5) * float(source.get("velocity_jitter", 0))
                    velocity = max(0.05, min(1.0,
                        float(source.get("velocity", 0.65)) * energy + vel_jitter
                    ))

                    events.append({
                        "start_beat": max(0.0, local + timing_jitter),
                        "duration_beats": float(dur) * float(source.get("gate", 0.85)),
                        "midi": int(midi),
                        "velocity": velocity,
                    })
                    local += dur

                cursor += phrase_beats
                phrase_idx += 1

        elif stype == "chords":
            prog = ir["materials"]["progressions"][source["progression"]]
            chord_beats = float(source.get("chord_beats", beats_per_bar))
            octave = int(source.get("octave", 3))
            center = int(source.get("voice_center", 60))
            seventh = bool(source.get("seventh", True))
            cursor = 0.0
            idx = 0
            previous = None

            while cursor < total_beats - 1e-9:
                degree = prog["degrees"][idx % len(prog["degrees"])]
                chord = triad_from_degree(root, scale, degree, octave, seventh=seventh)
                voiced = nearest_inversion(chord, center)
                if previous is not None:
                    # Try nearby octave shifts and choose smallest movement.
                    candidates = [
                        [n - 12 for n in voiced], voiced, [n + 12 for n in voiced]
                    ]
                    voiced = min(
                        candidates,
                        key=lambda c: sum(abs(a-b) for a,b in zip(sorted(previous), sorted(c)))
                    )
                sec = _section_at(cursor, sections)
                energy = float(sec.get("energy", 1.0))
                for note in voiced:
                    events.append({
                        "start_beat": cursor,
                        "duration_beats": chord_beats * float(source.get("gate", 0.92)),
                        "midi": int(note),
                        "velocity": float(source.get("velocity", 0.55)) * energy,
                    })
                previous = voiced
                cursor += chord_beats
                idx += 1

        elif stype == "bass":
            prog = ir["materials"]["progressions"][source["progression"]]
            pattern = source.get("pattern", [0.0, 2.0])
            octave = int(source.get("octave", 2))
            for bar in range(total_bars):
                degree = prog["degrees"][bar % len(prog["degrees"])]
                midi = scale_degree_to_midi(root, scale, degree, octave)
                sec = _section_at(bar * beats_per_bar, sections)
                energy = float(sec.get("energy", 1.0))
                for off in pattern:
                    events.append({
                        "start_beat": bar * beats_per_bar + float(off),
                        "duration_beats": float(source.get("duration_beats", 0.7)),
                        "midi": int(midi),
                        "velocity": float(source.get("velocity", 0.72)) * energy,
                    })

        track["events"] = sorted(events, key=lambda e: (e["start_beat"], e["midi"]))
        track["source"] = {"type": "resolved", "derived_from": source}

    return out
