from .development import develop_rhythm_profile
from dataclasses import dataclass
import random

@dataclass(frozen=True)
class GrooveConfig:
    steps_per_bar: int = 16
    swing: float = 0.08
    humanize_beats: float = 0.008
    velocity_jitter: float = 0.035
    fill_probability: float = 0.65
    bass_coupling: float = 0.75

def _stable_rng(seed: int, namespace: str):
    x = seed & 0xFFFFFFFF
    for ch in namespace.encode("utf-8"):
        x = ((x * 1664525) + ch + 1013904223) & 0xFFFFFFFF
    return random.Random(x)

def _section_profile(section_id: str):
    return {
        "intro": {"density": 0.15, "kick": 0.35, "snare": 0.0,  "hat": 0.25, "fill": 0.0},
        "build": {"density": 0.55, "kick": 0.75, "snare": 0.70, "hat": 0.65, "fill": 0.45},
        "main":  {"density": 0.90, "kick": 1.00, "snare": 1.00, "hat": 0.92, "fill": 0.65},
        "break": {"density": 0.25, "kick": 0.25, "snare": 0.35, "hat": 0.38, "fill": 0.25},
        "final": {"density": 1.00, "kick": 1.05, "snare": 1.05, "hat": 1.00, "fill": 0.90},
    }.get(section_id, {"density":0.75,"kick":0.8,"snare":0.8,"hat":0.75,"fill":0.4})

def _step_to_beat(step: int, steps_per_bar: int, beats_per_bar: int, swing: float):
    step_beats = beats_per_bar / steps_per_bar
    beat = step * step_beats
    # Delay every second 8th-note subdivision in a 16-step grid.
    if steps_per_bar % (beats_per_bar * 4) == 0:
        sixteenth = step
        if sixteenth % 4 == 2:
            beat += step_beats * swing
    return beat

def _weighted_keep(rng, base_probability, density):
    p = max(0.0, min(1.0, base_probability * density))
    return rng.random() <= p

def generate_rhythm_events(ir: dict, config: GrooveConfig):
    beats_per_bar = ir["transport"]["beats_per_bar"]
    seed = ir["meta"]["global_seed"]
    materials = ir["materials"]["rhythms"]
    rhythm_cfg = ir.get("rhythm_engine", {})
    groove_id = rhythm_cfg.get("groove", "default")
    groove = materials[groove_id]

    steps = int(groove.get("steps_per_bar", config.steps_per_bar))
    role_cells = groove["roles"]
    fills = groove.get("fills", {})

    events = []
    bar_meta = []

    for sec in ir["form"]:
        sec_id = sec["id"]
        profile = dict(_section_profile(sec_id))
        profile.update(rhythm_cfg.get("section_profiles", {}).get(sec_id, {}))
        profile = develop_rhythm_profile(ir, sec_id, profile)

        for local_bar in range(sec["bars"]):
            global_bar = sec["start_bar"] + local_bar
            rng = _stable_rng(seed, f"rhythm:{sec_id}:{global_bar}")
            is_last_bar = local_bar == sec["bars"] - 1

            bar_events = []
            for role in ("kick", "snare", "hat"):
                cell = role_cells.get(role, [])
                role_gain = float(profile.get(role, 1.0))
                for step, weight in enumerate(cell):
                    weight = float(weight)
                    if weight <= 0:
                        continue

                    # Primary anchors survive density thinning.
                    anchor = weight >= 0.95
                    climax = profile["density"] >= 0.98
                    if not climax:
                        if not anchor and not _weighted_keep(rng, weight, profile["density"]):
                            continue
                        if anchor and profile["density"] < 0.2 and role != "hat":
                            continue

                    beat = global_bar * beats_per_bar + _step_to_beat(
                        step, steps, beats_per_bar, config.swing
                    )
                    jitter = (rng.random() - 0.5) * 2 * config.humanize_beats
                    velocity = weight * role_gain * (0.94 + (rng.random()-0.5)*2*config.velocity_jitter)
                    velocity = max(0.03, min(1.0, velocity))

                    bar_events.append({
                        "event_type": "drum",
                        "drum": role,
                        "start_beat": round(max(0.0, beat + jitter), 6),
                        "duration_beats": 0.12 if role != "hat" else 0.05,
                        "velocity": round(velocity, 4),
                        "section_id": sec_id,
                        "arrangement_role": "drums",
                        "rhythm_origin": "groove",
                    })

            # Fill only on section transitions / final bar.
            fill_added = False
            if is_last_bar and profile.get("fill",0) > 0 and fills:
                force_fill = profile.get("fill",0) >= 0.90
                if force_fill or rng.random() < min(1.0, profile["fill"] * config.fill_probability):
                    fill = fills.get(sec_id) or fills.get("default")
                    if fill:
                        for step, role, weight in fill:
                            beat = global_bar * beats_per_bar + _step_to_beat(
                                int(step), steps, beats_per_bar, config.swing
                            )
                            bar_events.append({
                                "event_type": "drum",
                                "drum": role,
                                "start_beat": round(beat, 6),
                                "duration_beats": 0.09 if role != "hat" else 0.04,
                                "velocity": round(min(1.0, float(weight)*profile["density"]),4),
                                "section_id": sec_id,
                                "arrangement_role": "drums",
                                "rhythm_origin": "fill",
                            })
                        fill_added = True

            events.extend(bar_events)
            bar_meta.append({
                "section_id": sec_id,
                "bar": global_bar,
                "event_count": len(bar_events),
                "fill_added": fill_added,
                "density": profile["density"],
            })

    return {
        "events": sorted(events, key=lambda e:(e["start_beat"], e["drum"])),
        "bar_meta": bar_meta,
        "config": {
            "steps_per_bar": config.steps_per_bar,
            "swing": config.swing,
            "humanize_beats": config.humanize_beats,
            "velocity_jitter": config.velocity_jitter,
            "fill_probability": config.fill_probability,
            "bass_coupling": config.bass_coupling,
        }
    }

def coupled_bass_pattern(rhythm_events, section_id, beats_per_bar, coupling=0.75):
    """
    Derive bass onset offsets from kick events while keeping a stable musical pulse.
    Returns local offsets within each bar.
    """
    kicks = [e for e in rhythm_events
             if e.get("drum")=="kick" and e.get("section_id")==section_id]

    by_bar = {}
    for e in kicks:
        bar = int(e["start_beat"] // beats_per_bar)
        local = e["start_beat"] - bar * beats_per_bar
        by_bar.setdefault(bar, []).append(local)

    result = {}
    for bar, offsets in by_bar.items():
        offsets = sorted(offsets)
        selected = [0.0]
        for off in offsets:
            if off < 0.05:
                continue
            # Keep strongest structural points: roughly half/whole-beat locations first.
            structural = abs((off*2) - round(off*2)) < 0.08
            if structural or len(selected) < 2:
                selected.append(round(off,4))
        # Cap density based on coupling.
        max_notes = 2 if coupling < 0.5 else 3 if coupling < 0.85 else 4
        result[bar] = sorted(set(selected))[:max_notes]
    return result
