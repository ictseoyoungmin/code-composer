from collections import Counter
from ..core.theory import scale_degree_to_midi, voice_leading_cost

COLOR_DEGREE_OFFSETS = {
    "triad": [0,2,4],
    "seventh": [0,2,4,6],
    "add9": [0,2,4,6,8],
    "sus2": [0,1,4,6],
    "sus4": [0,3,4,6],
}

def color_chord(root, scale, degree, octave, color):
    offsets=COLOR_DEGREE_OFFSETS.get(color,COLOR_DEGREE_OFFSETS["seventh"])
    return [scale_degree_to_midi(root,scale,degree+off,octave) for off in offsets]

def _inversions(chord):
    base=sorted(chord)
    out=[]
    for inv in range(len(base)):
        notes=base[inv:]+[n+12 for n in base[:inv]]
        for shift in (-24,-12,0,12,24):
            out.append([n+shift for n in notes])
    return out

def voice_color_chord(chord, previous, center, motion_weight=1.0, center_weight=0.22):
    candidates=_inversions(chord)
    def score(notes):
        center_cost=abs(sum(notes)/len(notes)-center)
        movement=voice_leading_cost(previous,notes) if previous else center_cost
        span=max(notes)-min(notes) if notes else 0
        return motion_weight*movement + center_weight*center_cost + 0.025*max(0,span-19)
    return min(candidates,key=score)

def section_harmonic_profile(ir, section_id):
    grammar=ir.get("harmonic_grammar",{})
    default=grammar.get("default",{})
    specific=grammar.get("sections",{}).get(section_id,{})
    out=dict(default); out.update(specific)
    return out

def color_for_slot(profile, slot_index, slot_count):
    colors=profile.get("colors",["seventh"])
    if not colors: colors=["seventh"]
    if slot_index==slot_count-1 and profile.get("cadence_color"):
        return profile["cadence_color"]
    return colors[slot_index % len(colors)]

def passing_spec(profile, slot_index, slot_count):
    if slot_index != slot_count-1: return None
    if not profile.get("passing_enabled",False): return None
    return {
        "degree_offset": int(profile.get("passing_degree_offset",1)),
        "beats": float(profile.get("passing_beats",0.5)),
        "color": profile.get("passing_color","sus4"),
        "velocity_scale": float(profile.get("passing_velocity",0.62)),
    }
