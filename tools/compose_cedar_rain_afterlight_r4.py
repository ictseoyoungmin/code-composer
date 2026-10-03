#!/usr/bin/env python3
"""Cedar Rain, Afterlight R4 — music-first solo acoustic guitar rewrite.

R4 replaces R3's per-melody micro-roll rule with phrase-led guitar writing.
The rhythmic grammar is informed by public-domain Mauro Giuliani guitar practice:
strong-beat bass+melody pinches, alternating bass under a sustained top voice,
selective p-i-m-a-m-i arpeggiation, and density reduction at cadences.
No melody, bar, harmony sequence, or passage is copied from the references.
"""
from __future__ import annotations

from copy import deepcopy
import math

import compose_cedar_rain_afterlight as base

BPM = 73
METER_BEATS = 3
PRESET = base.PRESET
OPEN = base.OPEN
VOICINGS = base.VOICINGS
INSPIRATION = {
    "primary_score": "Mauro Giuliani — Studio per la Chitarra, Op.1 (1812), public-domain score",
    "secondary_score": "Mauro Giuliani — 12 Divertimenti per chitarra, Op.40 (1813), IMSLP CC0 2026 typeset",
    "usage": "rhythmic/idiomatic analysis only: metrical anchoring, bass+melody coordination, alternating bass, cadential density, right-hand patterns",
    "originality": "no melody, bar, harmony sequence, voicing sequence, or arrangement passage copied",
}

SECTIONS = [
    ("prelude", 8),
    ("theme", 16),
    ("development", 16),
    ("bridge", 8),
    ("percussive", 12),
    ("recap", 8),
    ("coda", 4),
]
START = {}
_cursor = 0
for _name, _bars in SECTIONS:
    START[_name] = _cursor
    _cursor += _bars
TOTAL_BARS = _cursor
assert TOTAL_BARS == 72

HARMONY = (
    ["Em9","Cmaj7","G6","B7", "Em9","C/G","D/F#","B7"] +
    ["Em9","Cmaj7","G6","B7", "Em/G","Am7","Cmaj7","B7",
     "Em9","C/G","D/F#","G6", "Cmaj7","Am7","B7","Em9"] +
    ["G6","D/F#","Em9","B7", "Cmaj7","Am7","Dsus2","B7",
     "Em/G","Fmaj7#11","Cmaj7","B7", "Am7","C/G","B7sus4","B7"] +
    ["Em9","G6","D/F#","B7", "Cmaj7","Am7","B7","Em9"] +
    ["Em9","Cmaj7","G6","B7", "Em/G","Am7","Cmaj7","B7",
     "Fmaj7#11","C/G","B7sus4","B7"] +
    ["Em9","Cmaj7","G6","B7", "Em/G","Am7","B7","Em9"] +
    ["Cmaj7","B7sus4","B7","Em9"]
)
assert len(HARMONY) == TOTAL_BARS

# Comfortable singing register for steel-string solo guitar.  Candidates are
# chord tones; desired contour is used only to choose smooth voice-leading.
TOP_CANDIDATES = {
    "Em9": [59,64,66,67,71],
    "Cmaj7": [59,60,64,67,71],
    "G6": [59,62,64,67],
    "D/F#": [62,66,69],
    "Em/G": [59,64,67,71],
    "Am7": [60,64,67,69],
    "C/G": [60,64,67],
    "Dsus2": [62,64,69],
    "Fmaj7#11": [59,64,65,69],
    "B7": [59,63,66,69,71],
    "B7sus4": [59,64,66,69,71],
}
PHRASE_CONTOURS = [
    [64,66,67,63], [64,62,64,63], [64,67,66,67], [64,62,63,64],
    [67,66,64,63], [64,67,69,63], [64,65,64,63], [60,62,64,63],
    [64,67,66,63], [64,62,64,63], [64,67,69,67], [64,62,63,64],
    [64,66,67,63], [64,62,64,63], [64,65,64,63], [64,62,63,64],
    [64,63,63,64], [64,64,63,64],
]
assert len(PHRASE_CONTOURS) == TOTAL_BARS // 4


def _voice_led_melody():
    result = []
    prev = 64
    for phrase in range(TOTAL_BARS // 4):
        for slot in range(4):
            bar = phrase * 4 + slot
            chord = HARMONY[bar]
            target = PHRASE_CONTOURS[phrase][slot]
            cand = TOP_CANDIDATES[chord]
            # Phrase-end B7 deliberately favors D#4 for a clean leading-tone
            # resolution into E4 when the next phrase begins on Em.
            if chord == "B7" and slot == 3:
                pitch = 63
            elif chord == "Em9" and bar > 0 and HARMONY[bar-1] in {"B7","B7sus4"}:
                pitch = 64
            else:
                pitch = min(cand, key=lambda p: abs(p-target)*1.0 + abs(p-prev)*0.55)
            result.append(pitch)
            prev = pitch
    return result

MELODY = _voice_led_melody()


def check_position(p):
    midi, string, fret = p
    if int(midi) != OPEN[int(string)] + int(fret):
        raise ValueError(f"midi/string/fret mismatch: {p}")
    if not 0 <= int(fret) <= 20:
        raise ValueError(f"fret outside playable range: {p}")


def top_position(midi: int, *, prefer_string2=False, avoid=None):
    avoid = set(avoid or ())
    opts = []
    for string in (2,1,3):
        fret = int(midi) - OPEN[string]
        if 0 <= fret <= 12 and string not in avoid:
            opts.append((int(midi), string, fret))
    if not opts:
        raise ValueError(f"unplayable melody note: {midi}")
    if prefer_string2:
        opts.sort(key=lambda p: (0 if p[1] == 2 else 1, p[2]))
    else:
        opts.sort(key=lambda p: (0 if p[1] in {2,3} else 1, p[2]))
    return opts[0]


def _by_string(chord):
    return {int(p[1]): tuple(p) for p in VOICINGS[chord]}


def note(event_id, start, duration, position, velocity, method, *, pluck=None, angle=None, left=None, arpeggio=None):
    check_position(position)
    midi, string, fret = position
    if pluck is None:
        pluck = .18 if method == "thumb" else (.145 if method == "nail" else .165)
    if angle is None:
        angle = 31.0 if method == "thumb" else (43.0 if method == "nail" else 37.0)
    perf = {
        "string": int(string), "fret": int(fret),
        "right_hand": {
            "method": method,
            "pluck_position": float(pluck),
            "attack_angle_deg": float(angle),
            "strength": float(max(.25, min(.90, .42 + .38 * velocity))),
        },
    }
    if left:
        perf["left_hand"] = deepcopy(left)
    if arpeggio:
        perf["arpeggio"] = deepcopy(arpeggio)
    return {
        "id": event_id, "type": "note", "start_beat": float(start),
        "duration_beats": float(duration), "midi": int(midi),
        "velocity": float(max(.16, min(.94, velocity))),
        "instrument_performance": perf,
    }


def action(event_id, kind, start, strength, location=None):
    params = {"strength": float(strength)}
    if location:
        params["location"] = location
    return {
        "id": event_id, "type": "instrument_action", "start_beat": float(start),
        "duration_beats": .08, "action": kind, "parameters": params,
    }


def _bass_positions(chord, bar_index):
    bys = _by_string(chord)
    low = [bys[s] for s in (6,5,4) if s in bys]
    if not low:
        raise ValueError(chord)
    root = low[0]
    alt = low[1] if len(low) > 1 else root
    if bar_index % 2:
        root, alt = alt, root
    return root, alt


def _inner_positions(chord, melody_string):
    bys = _by_string(chord)
    options = [bys[s] for s in (4,3,2,1) if s in bys and s != melody_string]
    if len(options) < 2:
        options = [tuple(p) for p in VOICINGS[chord] if int(p[1]) != melody_string]
    # Prefer two different physical strings closest to the treble register.
    a = options[0]
    b = next(p for p in options[1:] if p[1] != a[1])
    return a, b


def _method_for_string(string):
    if string >= 5:
        return "thumb"
    if string == 4:
        return "thumb"
    if string == 3:
        return "finger"
    if string == 2:
        return "finger"
    return "finger"


def _secondary_melody(bar_index, primary):
    chord = HARMONY[bar_index]
    cand = TOP_CANDIDATES[chord]
    # Choose a close chord tone, usually below the primary, for a response.
    others = [p for p in cand if p != primary]
    return min(others, key=lambda p: (abs(p-primary), 0 if p < primary else 1))


def phrase_energy(section, local):
    bases = {
        "prelude": .45, "theme": .62, "development": .70,
        "bridge": .75, "percussive": .73, "recap": .66, "coda": .48,
    }
    arc = (.88, .98, 1.06, .90)[local % 4]
    return bases[section] * arc


def _pinch(out, bar, eid, onset, bass, melody_pos, energy, melody_dur=1.05):
    # Thumb + melody finger together on the metrical anchor.  This is the key
    # R4 change: melody is not preceded by a compulsory micro-roll.
    out.append(note(f"{eid}-p", bar*METER_BEATS+onset, .62, bass, energy-.03, "thumb"))
    m_method = "nail" if (bar % 17 == 0 and melody_pos[1] <= 2) else "finger"
    out.append(note(f"{eid}-m", bar*METER_BEATS+onset, melody_dur, melody_pos, energy+.07, m_method))


def _pinch_flow_bar(bar, local, section):
    chord = HARMONY[bar]
    energy = phrase_energy(section, local)
    primary = MELODY[bar]
    melody_pos = top_position(primary, prefer_string2=(bar % 3 != 0))
    bass1, bass2 = _bass_positions(chord, bar)
    inner1, inner2 = _inner_positions(chord, melody_pos[1])
    out = []
    _pinch(out, bar, f"r4-b{bar+1:02d}-a", 0.0, bass1, melody_pos, energy, 1.12)
    out.append(note(f"r4-b{bar+1:02d}-i1", bar*3+.52, .48, inner1, energy-.09, _method_for_string(inner1[1])))
    out.append(note(f"r4-b{bar+1:02d}-b2", bar*3+1.02, .50, bass2, energy-.07, "thumb"))
    out.append(note(f"r4-b{bar+1:02d}-i2", bar*3+1.52, .46, inner2, energy-.08, _method_for_string(inner2[1])))
    response = _secondary_melody(bar, primary)
    response_pos = top_position(response, prefer_string2=(melody_pos[1] == 1), avoid={melody_pos[1]} if response == primary else set())
    out.append(note(f"r4-b{bar+1:02d}-r", bar*3+2.02, .62, response_pos, energy+.01, "finger"))
    # Leave the final half-beat partly open so the bar breathes.
    if local % 4 not in {3}:
        out.append(note(f"r4-b{bar+1:02d}-tail", bar*3+2.56, .32, inner1, energy-.13, _method_for_string(inner1[1])))
    return out


def _alberti_melody_bar(bar, local, section):
    chord = HARMONY[bar]
    energy = phrase_energy(section, local)
    primary = MELODY[bar]
    melody_pos = top_position(primary, prefer_string2=True)
    bass1, bass2 = _bass_positions(chord, bar)
    inner1, inner2 = _inner_positions(chord, melody_pos[1])
    out = []
    # Giuliani-informed concept: a sustained melody is articulated with the
    # bass at the start, while p/i motion maintains pulse underneath.
    _pinch(out, bar, f"r4-b{bar+1:02d}-al", 0.0, bass1, melody_pos, energy, 1.55)
    for idx, (off, pos, vel) in enumerate([
        (.50, inner1, -.10), (1.00, bass2, -.07), (1.50, inner1, -.10),
        (2.00, bass1, -.08), (2.50, inner2, -.11),
    ]):
        method = "thumb" if pos[1] >= 4 else "finger"
        out.append(note(f"r4-b{bar+1:02d}-al{idx}", bar*3+off, .39, pos, energy+vel, method))
    return out


def _roll6_bar(bar, local, section):
    chord = HARMONY[bar]
    energy = phrase_energy(section, local)
    primary = MELODY[bar]
    melody_pos = top_position(primary, prefer_string2=False)
    bass1, _bass2 = _bass_positions(chord, bar)
    inner1, inner2 = _inner_positions(chord, melody_pos[1])
    # A true p-i-m-a-m-i-style six-contact gesture.  It occupies the bar
    # instead of being repeated before every melody note.
    positions = [bass1, inner1, inner2, melody_pos, inner2, inner1]
    players = []
    for p in positions:
        if p[1] >= 4: players.append(("thumb", "bass" if p[1] >= 5 else "inner", "thumb"))
        elif p[1] == 3: players.append(("index", "inner", "finger"))
        elif p[1] == 2: players.append(("middle", "treble", "finger"))
        else: players.append(("ring", "treble", "finger"))
    gid = f"r4-b{bar+1:02d}-roll"
    out = []
    for seq, (off, pos) in enumerate(zip((0,.5,1.,1.5,2.,2.5), positions)):
        player, voice, method = players[seq]
        out.append(note(
            f"{gid}-{seq}", bar*3+off, .39 if seq != 3 else .72,
            pos, energy + (.06 if seq == 3 else -.07 + .015*(seq%2)), method,
            arpeggio={"gesture_id":gid,"player":player,"voice":voice,"sequence_index":seq},
        ))
    return out


def _cadence_bar(bar, local, section):
    chord = HARMONY[bar]
    energy = phrase_energy(section, local) * .92
    primary = MELODY[bar]
    melody_pos = top_position(primary, prefer_string2=True)
    bass1, bass2 = _bass_positions(chord, bar)
    inner1, inner2 = _inner_positions(chord, melody_pos[1])
    out = []
    _pinch(out, bar, f"r4-b{bar+1:02d}-cad", 0.0, bass1, melody_pos, energy, 1.30)
    out.append(note(f"r4-b{bar+1:02d}-cad-i", bar*3+.78, .50, inner1, energy-.11, _method_for_string(inner1[1])))
    out.append(note(f"r4-b{bar+1:02d}-cad-b", bar*3+1.52, .58, bass2, energy-.08, "thumb"))
    # The last beat is intentionally sparse: one inner response and decay.
    out.append(note(f"r4-b{bar+1:02d}-cad-u", bar*3+2.05, .78, inner2, energy-.07, _method_for_string(inner2[1])))
    return out


def _development_sync_bar(bar, local):
    chord = HARMONY[bar]
    energy = phrase_energy("development", local)
    primary = MELODY[bar]
    melody_pos = top_position(primary, prefer_string2=(bar%2==0))
    bass1, bass2 = _bass_positions(chord, bar)
    inner1, inner2 = _inner_positions(chord, melody_pos[1])
    out=[]
    _pinch(out, bar, f"r4-b{bar+1:02d}-dev", 0.0, bass1, melody_pos, energy, 1.05)
    # One controlled displaced response; strong beat remains anchored.
    out.append(note(f"r4-b{bar+1:02d}-dev-i1", bar*3+.66, .38, inner1, energy-.10, _method_for_string(inner1[1])))
    out.append(note(f"r4-b{bar+1:02d}-dev-b", bar*3+1.18, .44, bass2, energy-.07, "thumb"))
    out.append(note(f"r4-b{bar+1:02d}-dev-i2", bar*3+1.72, .40, inner2, energy-.09, _method_for_string(inner2[1])))
    response=_secondary_melody(bar,primary)
    rp=top_position(response,prefer_string2=True)
    out.append(note(f"r4-b{bar+1:02d}-dev-r", bar*3+2.18, .64, rp, energy+.01, "finger"))
    return out


def _strum_config(stroke_id, direction, idx, energy, muted=False):
    down = direction == "down"
    return {
        "stroke_id": stroke_id, "direction": direction,
        "traversal_ms": 36.0 if down else 26.0,
        "entry_strength": min(.90, energy + (.07 if idx == 0 else -.04)),
        "acceleration": .12 if down else -.07,
        "pick_depth": .58 if down else .45,
        "attack_angle_deg": 40.0 if down else 34.0,
        "follow_through": .74 if down else .58,
        "accent_position": .58 if down else .42,
        "accent_amount": .28 if idx == 0 else .07,
        "from_string": 6 if down else 1, "to_string": 1 if down else 6,
        "state": "muted" if muted else "sounding",
    }


def _strum_bar(bar, local):
    chord=HARMONY[bar]
    energy=phrase_energy("bridge",local)
    # Waltz-like guitar groove: clear beat 1, lighter answer, optional choke.
    patterns=[
        [(0.,"down",False),(1.02,"down",False),(1.68,"up",False),(2.42,"up",False)],
        [(0.,"down",False),(.82,"up",False),(1.52,"down",False),(2.28,"up",True)],
        [(0.,"down",False),(1.18,"down",False),(1.82,"up",False),(2.48,"down",False)],
        [(0.,"down",False),(.92,"up",False),(1.64,"down",True),(2.34,"up",False)],
    ]
    out=[]
    for idx,(off,direction,muted) in enumerate(patterns[local%4]):
        sid=f"r4-b{bar+1:02d}-s{idx}"
        cfg=_strum_config(sid,direction,idx,energy,muted)
        for n,(m,s,f) in enumerate(VOICINGS[chord]):
            perf={
                "string":s,"fret":f,
                "right_hand":{"method":"pick","pluck_position":.12 if direction=="down" else .14,"attack_angle_deg":cfg["attack_angle_deg"],"strength":cfg["entry_strength"]},
                "strum":deepcopy(cfg),
            }
            if muted: perf["left_hand"]={"technique":"dead_note"}
            out.append({"id":f"{sid}-{n}","type":"note","start_beat":bar*3+off,"duration_beats":.18 if muted else .48,"midi":m,"velocity":min(.93,energy+(.07 if idx==0 else -.05)),"instrument_performance":perf})
    return out


def _percussive_bar(bar, local):
    # Keep the same musical grammar as fingerstyle; percussion is punctuation,
    # never a replacement for pulse or melody.
    out = _pinch_flow_bar(bar, local, "percussive") if local % 3 != 1 else _alberti_melody_bar(bar, local, "percussive")
    if local % 4 in {1,3}:
        out.append(action(f"r4-b{bar+1:02d}-tap","body_tap",bar*3+1.48,.38,"lower_bout"))
    if local % 4 == 2:
        out.append(action(f"r4-b{bar+1:02d}-slap","top_slap",bar*3+2.46,.41,"soundboard"))
    return out


def _prelude_bar(bar, local):
    # Sparse statement: strong-beat pinch + one inner answer, with natural space.
    chord=HARMONY[bar]
    energy=phrase_energy("prelude",local)
    primary=MELODY[bar]
    mp=top_position(primary,prefer_string2=True)
    bass1,_=_bass_positions(chord,bar)
    inner1,_=_inner_positions(chord,mp[1])
    out=[]
    _pinch(out,bar,f"r4-b{bar+1:02d}-pre",0.,bass1,mp,energy,1.45)
    out.append(note(f"r4-b{bar+1:02d}-pre-i",bar*3+1.48,.70,inner1,energy-.10,_method_for_string(inner1[1])))
    if local%4!=3:
        out.append(note(f"r4-b{bar+1:02d}-pre-b",bar*3+2.28,.48,bass1,energy-.12,"thumb"))
    return out


def _coda_bar(bar, local, final=False):
    chord=HARMONY[bar]
    energy=phrase_energy("coda",local)
    primary=MELODY[bar]
    mp=top_position(primary,prefer_string2=True)
    bass1,_=_bass_positions(chord,bar)
    out=[]
    _pinch(out,bar,f"r4-b{bar+1:02d}-co",0.,bass1,mp,energy,1.65)
    if not final:
        bys=_by_string(chord)
        ip=next(bys[s] for s in (3,2,4) if s in bys and s!=mp[1])
        out.append(note(f"r4-b{bar+1:02d}-co-i",bar*3+1.60,.72,ip,energy-.10,_method_for_string(ip[1])))
    else:
        # Final Em9 is a quiet, slightly spread chord after the melodic arrival.
        gid=f"r4-final-rake"
        for idx,(m,s,f) in enumerate(VOICINGS["Em9"]):
            method="thumb" if s>=4 else "finger"
            out.append(note(f"{gid}-{idx}",bar*3+1.72+.045*idx,1.05,(m,s,f),energy-.02+.012*idx,method))
    return out


def build_events():
    ev=[]
    for local in range(8):
        bar=START["prelude"]+local
        ev += _prelude_bar(bar,local)
    for local in range(16):
        bar=START["theme"]+local
        mode=local%4
        ev += (_pinch_flow_bar(bar,local,"theme") if mode==0 else
               _alberti_melody_bar(bar,local,"theme") if mode==1 else
               _roll6_bar(bar,local,"theme") if mode==2 else
               _cadence_bar(bar,local,"theme"))
    for local in range(16):
        bar=START["development"]+local
        mode=local%4
        ev += (_alberti_melody_bar(bar,local,"development") if mode==0 else
               _development_sync_bar(bar,local) if mode==1 else
               _roll6_bar(bar,local,"development") if mode==2 else
               _cadence_bar(bar,local,"development"))
    for local in range(8):
        bar=START["bridge"]+local
        ev += _strum_bar(bar,local)
    for local in range(12):
        bar=START["percussive"]+local
        ev += _percussive_bar(bar,local)
        if local%4==3:
            # phrase-ending bar is cadence-shaped rather than percussion-dense
            pass
    for local in range(8):
        bar=START["recap"]+local
        mode=local%4
        ev += (_pinch_flow_bar(bar,local,"recap") if mode==0 else
               _alberti_melody_bar(bar,local,"recap") if mode==1 else
               _roll6_bar(bar,local,"recap") if mode==2 else
               _cadence_bar(bar,local,"recap"))
    for local in range(4):
        bar=START["coda"]+local
        ev += _coda_bar(bar,local,final=(local==3))
    return sorted(ev,key=lambda e:(float(e["start_beat"]),0 if e["type"]=="note" else 1,e["id"]))


def build_song():
    return {
        "format":"code-composer-song/v1",
        "meta":{"title":"Cedar Rain, Afterlight","global_seed":1919072,"revision":"SOLO-ACOUSTIC-PROD-R4"},
        "transport":{"bpm":BPM,"meter":{"beats_per_bar":3,"beat_unit":4}},
        "tonal":{"root":"E","scale":"natural_minor"},
        "sections":[{"id":s,"bars":n,"name":s.title()} for s,n in SECTIONS],
        "instruments":[{"id":"guitar","family":"acoustic_guitar","variant":"steel-string","render_lock":{"preset":PRESET,"preset_version":"1.0.0"}}],
        "tracks":[{"id":"guitar","function":"solo-acoustic-guitar","instrument":"guitar"}],
        "materials":[{"id":"through-composed","kind":"motif","intervals":[0],"rhythm":[1]}],
        "parts":[{"id":f"{s}-part","section":s,"track":"guitar","material":"through-composed"} for s,_ in SECTIONS],
    }


def bar_signatures(events=None):
    events=build_events() if events is None else events
    sigs=[]
    for b in range(TOTAL_BARS):
        row=[]
        for e in events:
            st=float(e["start_beat"])
            if b*3 <= st < (b+1)*3:
                if e["type"]=="note":
                    p=e["instrument_performance"]
                    row.append(("n",round(st-b*3,3),int(e["midi"]),round(float(e["duration_beats"]),3),round(float(e["velocity"]),3),int(p["string"]),p["right_hand"]["method"],(p.get("strum") or {}).get("direction"),(p.get("arpeggio") or {}).get("player")))
                else:
                    row.append(("a",round(st-b*3,3),e["action"],round(float(e["parameters"]["strength"]),3)))
        sigs.append(tuple(row))
    return sigs


def validate_musical_grammar(events=None):
    events=build_events() if events is None else events
    notes=[e for e in events if e["type"]=="note"]
    # Strong-beat guitar anchoring: in fingerstyle sections, most bars must have
    # at least two simultaneous notes (bass+melody) on beat 1.
    finger_bars=list(range(START["prelude"],START["bridge"])) + list(range(START["percussive"],START["bridge"]+8+12)) + list(range(START["recap"],TOTAL_BARS))
    anchored=0
    for b in finger_bars:
        onset=[e for e in notes if abs(float(e["start_beat"])-b*3.0)<1e-9]
        strings={int(e["instrument_performance"]["string"]) for e in onset}
        if len(onset)>=2 and any(s>=4 for s in strings) and any(s<=3 for s in strings):
            anchored+=1
    anchor_ratio=anchored/max(1,len(finger_bars))
    if anchor_ratio < .78:
        raise ValueError(f"metrical bass+melody anchoring too weak: {anchor_ratio:.3f}")

    # Phrase endings must be less dense than the preceding bar to create breath.
    cadence_checks=[]
    for b in list(range(START["theme"]+3,START["theme"]+16,4)) + list(range(START["development"]+3,START["development"]+16,4)) + list(range(START["recap"]+3,START["recap"]+8,4)):
        cur=sum(1 for e in notes if b*3 <= float(e["start_beat"]) < (b+1)*3)
        prev=sum(1 for e in notes if (b-1)*3 <= float(e["start_beat"]) < b*3)
        cadence_checks.append((b+1,prev,cur))
        if cur >= prev:
            raise ValueError(f"cadence bar {b+1} does not reduce density: {prev}->{cur}")

    # No long exposed treble chain: consecutive note onsets on strings 1-2 with
    # no intervening bass/inner contact are capped at two.
    run=best=0
    for e in sorted(notes,key=lambda x:(float(x["start_beat"]),x["id"])):
        s=int(e["instrument_performance"]["string"])
        if s<=2:
            run+=1; best=max(best,run)
        else:
            run=0
    if best>2:
        raise ValueError(f"exposed treble run too long: {best}")

    # The music must use more than one rhythmic texture and avoid copy-paste.
    sigs=bar_signatures(events)
    unique=len(set(sigs))
    windows=[tuple(sigs[i:i+4]) for i in range(TOTAL_BARS-3)]
    if unique < 60:
        raise ValueError(f"bar diversity too low: {unique}/{TOTAL_BARS}")
    if len(windows) != len(set(windows)):
        raise ValueError("identical 4-bar phrase window detected")

    # Keep the lyrical line out of a permanently shrill register.
    melody_values=MELODY
    if max(melody_values)>71 or sum(1 for p in melody_values if p>=69)/len(melody_values)>.18:
        raise ValueError("melody register too persistently high")

    return {
        "meter":"3/4",
        "bpm":BPM,
        "bass_melody_downbeat_anchor_ratio":anchor_ratio,
        "cadence_density_checks":cadence_checks,
        "max_exposed_treble_run":best,
        "unique_bar_signatures":unique,
        "identical_four_bar_windows":0,
        "melody_min":min(melody_values),
        "melody_max":max(melody_values),
        "high_melody_ratio":sum(1 for p in melody_values if p>=69)/len(melody_values),
        "music_first_grammar":True,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(validate_musical_grammar(),indent=2))
