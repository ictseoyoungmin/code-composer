from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass


class ViolinPerformanceError(ValueError):
    pass


# Standard violin tuning. The planner intentionally models a conventional
# four-string violin only; scordatura is a future capability.
STRINGS = (
    ("G", 55, 24),
    ("D", 62, 24),
    ("A", 69, 24),
    ("E", 76, 29),
)

# Nominal first-finger locations for successive violin positions expressed as
# semitones above the open string. Chromatic low/high-finger alterations are
# represented separately instead of pretending every hand frame is fixed.
POSITION_FIRST_FINGER = (2, 4, 5, 7, 9, 10, 12, 14, 16, 17, 19, 21, 23, 24)
FINGER_NOMINAL_OFFSETS = (0, 2, 4, 5)

DEFAULT_VIOLIN_CONFIG = {
    "range_midi": [55, 105],
    "max_bow_duration_s": 5.0,
    "legato_gap_beats": 0.10,
    "comfortable_transition_score": 6.0,
    "challenging_transition_score": 10.0,
    "strict_comfort": True,
    "default_contact_point": None,
    "double_stop_max_position_gap": 1,
    "double_stop_max_stretch_semitones": 7,
    # S12 opt-in: separated bow groups may reuse the previous direction after
    # a physical retake. Defaults stay false to preserve S3-S11 realization.
    "enable_bow_retakes": False,
    "bow_retake_gap_beats": 0.18,
}


@dataclass(frozen=True)
class Fingering:
    string_index: int
    string: str
    open_midi: int
    position: int
    finger: int
    alteration_semitones: int
    stopped_semitones: int

    def as_dict(self) -> dict:
        return {
            "string": self.string,
            "string_index": self.string_index,
            "open_midi": self.open_midi,
            "position": self.position,
            "finger": self.finger,
            "alteration_semitones": self.alteration_semitones,
            "stopped_semitones": self.stopped_semitones,
        }


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


def _merge_config(config: dict | None) -> dict:
    out = deepcopy(DEFAULT_VIOLIN_CONFIG)
    if config:
        if not isinstance(config, dict):
            raise ViolinPerformanceError("violin config must be an object")
        unknown = set(config) - set(out)
        if unknown:
            raise ViolinPerformanceError(f"unknown violin config field(s): {sorted(unknown)}")
        out.update(deepcopy(config))
    rng = out["range_midi"]
    if not isinstance(rng, (list, tuple)) or len(rng) != 2:
        raise ViolinPerformanceError("range_midi must contain [low, high]")
    out["range_midi"] = [int(rng[0]), int(rng[1])]
    if out["range_midi"][0] < 55 or out["range_midi"][1] > 105 or out["range_midi"][0] > out["range_midi"][1]:
        raise ViolinPerformanceError("range_midi must stay within conventional violin range 55..105")
    out["max_bow_duration_s"] = float(out["max_bow_duration_s"])
    if not 0.5 <= out["max_bow_duration_s"] <= 12.0:
        raise ViolinPerformanceError("max_bow_duration_s must be within 0.5..12")
    out["legato_gap_beats"] = float(out["legato_gap_beats"])
    if not 0.0 <= out["legato_gap_beats"] <= 1.0:
        raise ViolinPerformanceError("legato_gap_beats must be within 0..1")
    for key in ("comfortable_transition_score", "challenging_transition_score"):
        out[key] = float(out[key])
    if out["comfortable_transition_score"] >= out["challenging_transition_score"]:
        raise ViolinPerformanceError("comfortable transition score must be below challenging score")
    if not isinstance(out["strict_comfort"], bool):
        raise ViolinPerformanceError("strict_comfort must be boolean")
    if out["default_contact_point"] is not None:
        out["default_contact_point"] = _clamp(out["default_contact_point"], .02, .49)
    out["double_stop_max_position_gap"] = int(out["double_stop_max_position_gap"])
    if not 0 <= out["double_stop_max_position_gap"] <= 2:
        raise ViolinPerformanceError("double_stop_max_position_gap must be within 0..2")
    out["double_stop_max_stretch_semitones"] = int(out["double_stop_max_stretch_semitones"])
    if not 0 <= out["double_stop_max_stretch_semitones"] <= 9:
        raise ViolinPerformanceError("double_stop_max_stretch_semitones must be within 0..9")
    if not isinstance(out["enable_bow_retakes"], bool):
        raise ViolinPerformanceError("enable_bow_retakes must be boolean")
    out["bow_retake_gap_beats"] = float(out["bow_retake_gap_beats"])
    if not 0.0 <= out["bow_retake_gap_beats"] <= 4.0:
        raise ViolinPerformanceError("bow_retake_gap_beats must be within 0..4")
    return out


def fingering_candidates(midi: int) -> list[dict]:
    """Return deterministic physically plausible candidates for one violin pitch."""
    midi = int(midi)
    if midi < 55 or midi > 105:
        return []
    out: list[Fingering] = []
    for sidx, (name, open_midi, max_offset) in enumerate(STRINGS):
        delta = midi - open_midi
        if delta < 0 or delta > max_offset:
            continue
        if delta == 0:
            out.append(Fingering(sidx, name, open_midi, 0, 0, 0, 0))
            continue
        for pos, base in enumerate(POSITION_FIRST_FINGER, 1):
            for finger, nominal in enumerate(FINGER_NOMINAL_OFFSETS, 1):
                alteration = delta - (base + nominal)
                if alteration in (-1, 0, 1):
                    out.append(Fingering(sidx, name, open_midi, pos, finger, alteration, delta))
    out.sort(key=lambda f: (
        f.position == 0,
        f.position if f.position else 0,
        abs(f.alteration_semitones),
        -f.string_index,
        f.finger,
    ))
    return [x.as_dict() for x in out]


def _candidate_local_cost(c: dict) -> float:
    if c["finger"] == 0:
        return 0.0
    pos = int(c["position"])
    cost = pos * 0.055 + abs(int(c["alteration_semitones"])) * 0.16
    if pos > 7:
        cost += (pos - 7) * 0.20
    return cost


def _transition_cost(a: dict, b: dict, delta_s: float) -> tuple[float, dict]:
    crossing = abs(int(b["string_index"]) - int(a["string_index"]))
    apos = int(a["position"])
    bpos = int(b["position"])
    shift = 0 if apos == 0 or bpos == 0 else abs(bpos - apos)
    time_factor = 1.0 / max(.12, float(delta_s))
    score = crossing * .30 * time_factor + shift * .43 * time_factor
    if crossing > 1:
        score += .75 * (crossing - 1)
    if bpos > 7:
        score += .12 * (bpos - 7)
    if a.get("finger") == b.get("finger") and shift >= 3:
        score += .35
    return score, {
        "string_crossing": crossing,
        "position_shift": shift,
        "transition_seconds": round(float(delta_s), 6),
        "score": round(score, 6),
    }


__all__ = [
    "ViolinPerformanceError",
    "STRINGS",
    "DEFAULT_VIOLIN_CONFIG",
    "fingering_candidates",
]
