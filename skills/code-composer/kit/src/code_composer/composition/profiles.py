"""Stable arrangement profile contract shared by composition and agent layers."""

DEFAULT_PROFILES = {
    "intro": {
        "energy": 0.32,
        "lead_density": 0.42,
        "lead_octave": 4,
        "lead_fragment": 0.50,
        "pad_gain": 0.75,
        "bass": False,
        "arp": False,
        "register_shift": -12,
    },
    "build": {
        "energy": 0.58,
        "lead_density": 0.68,
        "lead_octave": 4,
        "lead_fragment": 0.78,
        "pad_gain": 0.95,
        "bass": True,
        "arp": True,
        "register_shift": 0,
    },
    "main": {
        "energy": 0.88,
        "lead_density": 0.88,
        "lead_octave": 4,
        "lead_fragment": 1.00,
        "pad_gain": 1.0,
        "bass": True,
        "arp": True,
        "register_shift": 0,
    },
    "break": {
        "energy": 0.42,
        "lead_density": 0.46,
        "lead_octave": 5,
        "lead_fragment": 0.50,
        "pad_gain": 0.62,
        "bass": False,
        "arp": False,
        "register_shift": 12,
    },
    "final": {
        "energy": 1.0,
        "lead_density": 0.95,
        "lead_octave": 5,
        "lead_fragment": 1.00,
        "pad_gain": 1.12,
        "bass": True,
        "arp": True,
        "register_shift": 12,
    },
}

def profile_for(ir: dict, section_id: str) -> dict:
    custom = ir.get("arrangement", {}).get("profiles", {}).get(section_id, {})
    base = dict(DEFAULT_PROFILES.get(section_id, DEFAULT_PROFILES["main"]))
    base.update(custom)
    return base

__all__ = ["DEFAULT_PROFILES", "profile_for"]
