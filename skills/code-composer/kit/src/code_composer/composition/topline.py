from dataclasses import dataclass
from .phrase import PhraseConfig, compose_phrase
from .topline_grammar import apply_topline_grammar

@dataclass(frozen=True)
class ToplineConfig:
    density: float = 0.48
    octave: int = 5
    phrase_bars: int = 4
    tension: float = 0.52
    cadence_strength: float = 0.72
    max_leap_semitones: int = 5

def resolve_topline(ir, section, role, profile, seed):
    """
    Resolve a sparse, phrase-aware guide/topline lane.

    This is not vocal synthesis. It creates symbolic note events that reserve
    melodic/rhythmic space for a future singer/topline and may optionally be
    rendered with a guide instrument.
    """
    if not profile.get("topline_active", False):
        return []

    beats_per_bar = ir["transport"]["beats_per_bar"]
    motif_id = role.get("motif", ir["arrangement"]["motif"])

    cfg = PhraseConfig(
        bars=int(section["bars"]),
        beats_per_bar=int(beats_per_bar),
        base_degree=int(role.get("base_degree", 1)),
        octave=int(profile.get("topline_octave", role.get("octave", 5))),
        density=float(profile.get("topline_density", 0.48)),
        tension=float(profile.get("topline_tension", role.get("tension", 0.52))),
        cadence_strength=float(role.get("cadence_strength", 0.72)),
        max_leap_semitones=int(role.get("max_leap_semitones", 5)),
        gate=float(role.get("gate", 1.0)),
    )

    phrase = compose_phrase(
        ir["materials"], ir["tonal"], seed, motif_id, cfg,
        namespace=f"topline:{section['id']}"
    )

    start_beat = section["start_bar"] * beats_per_bar
    total_beats = section["bars"] * beats_per_bar
    rest_bias = float(profile.get("topline_rest_bias", 0.28))
    phrase_gap = float(profile.get("topline_phrase_gap_beats", 0.5))

    out = []
    last_end = -999.0
    for i, ev in enumerate(phrase["events"]):
        local = float(ev["start_beat"])
        if local >= total_beats:
            continue

        # Preserve phrase breathing room: avoid filling every candidate onset.
        # Deterministic index pattern; no renderer-side invention.
        if i % 5 == 3 and rest_bias >= 0.2:
            continue
        if local < last_end + phrase_gap and i % 3 != 0:
            continue

        x = dict(ev)
        x["start_beat"] = round(start_beat + local, 6)
        x["velocity"] = float(x.get("velocity", 0.6)) * float(profile.get("topline_velocity", 0.82))
        x["section_id"] = section["id"]
        x["arrangement_role"] = "topline"
        x["topline_phrase"] = True
        out.append(x)
        last_end = local + float(x["duration_beats"])

    return apply_topline_grammar(
        out,
        section,
        ir["tonal"],
        beats_per_bar,
        ir.get("topline_grammar", {}),
    )
