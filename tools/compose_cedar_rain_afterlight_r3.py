#!/usr/bin/env python3
"""Cedar Rain, Afterlight R3 — guitar-native fingerstyle texture revision.

R2 exposed the upper melody as isolated single-string plucks over an independent
low accompaniment layer. R3 removes that piano-like separation. Every authored
upper melody onset in the fingerstyle sections now belongs to a 3- or 4-contact
multi-string arpeggio gesture with explicit p/i/m/a-style player authority.

The composition, harmony, section form, strumming bridge, percussion actions,
and coda remain derived from the R2 source. Only the fingerstyle realization is
re-authored here.
"""
from __future__ import annotations

from copy import deepcopy
import math

import compose_cedar_rain_afterlight as base

# Re-export the canonical composition constants/functions expected by the
# production section renderer.
BPM = base.BPM
PRESET = base.PRESET
OPEN = base.OPEN
INSPIRATION = base.INSPIRATION
VOICINGS = base.VOICINGS
LOW = base.LOW
SECTIONS = base.SECTIONS
START = base.START
TOTAL_BARS = base.TOTAL_BARS
HARMONY = base.HARMONY
ENERGY = base.ENERGY
bar_sigs = base.bar_sigs


def _role_for_string(string_number: int) -> tuple[str, str, str]:
    """Return (player, voice, right-hand method) for one physical string."""
    if string_number >= 4:
        return ("thumb", "bass" if string_number >= 5 else "inner", "thumb")
    if string_number == 3:
        return ("index", "inner", "finger")
    if string_number == 2:
        return ("middle", "treble", "finger")
    return ("ring", "treble", "finger")


def _arp_note(
    event_id: str,
    start: float,
    duration: float,
    position: tuple[int, int, int],
    velocity: float,
    gesture_id: str,
    sequence_index: int,
    *,
    melody_peak: bool = False,
    use_nail: bool = False,
):
    midi, string_number, _fret = position
    player, voice, method = _role_for_string(string_number)
    if use_nail and string_number <= 2:
        method = "nail"
    ev = base.note(
        event_id,
        start,
        duration,
        position,
        velocity,
        method,
        pluck=.145 if method == "nail" else (.18 if string_number >= 4 else .165),
        angle=31. if method == "thumb" else (43. if method == "nail" else 37.),
    )
    ev["instrument_performance"]["arpeggio"] = {
        "gesture_id": gesture_id,
        "player": player,
        "voice": voice,
        "sequence_index": int(sequence_index),
    }
    ev["r3_texture_role"] = "melody_peak" if melody_peak else "arpeggio_support"
    return ev


def _voicing_by_string(chord: str) -> dict[int, tuple[int, int, int]]:
    return {int(p[1]): p for p in VOICINGS[chord]}


def _support_positions(chord: str, melody_string: int, gesture_index: int, local: int):
    """Choose physically separated chord tones around the melody string.

    The patterns deliberately rotate bass/inner strings so the hand does not
    repeat one identical keyboard-like cell across the whole piece.
    """
    bys = _voicing_by_string(chord)
    bass_candidates = [bys[s] for s in (6, 5, 4) if s in bys and s != melody_string]
    inner_candidates = [bys[s] for s in (4, 3, 2, 1) if s in bys and s != melody_string]
    if not bass_candidates:
        bass_candidates = inner_candidates[:1]
    if len(inner_candidates) < 2:
        inner_candidates = [p for p in VOICINGS[chord] if p[1] != melody_string]

    bass = bass_candidates[(local + gesture_index) % len(bass_candidates)]
    # Prefer strings 3/2 around a string-1 melody, and 4/3 around string-2 melody.
    if melody_string == 1:
        preferred = [bys[s] for s in (3, 2, 4) if s in bys]
    else:
        preferred = [bys[s] for s in (4, 3, 1) if s in bys]
    preferred = [p for p in preferred if p[1] != melody_string]
    if len(preferred) < 2:
        preferred = inner_candidates

    a = preferred[(local + gesture_index) % len(preferred)]
    b = preferred[(local + gesture_index + 1) % len(preferred)]
    if b[1] == a[1]:
        b = next(p for p in inner_candidates if p[1] != a[1])
    return bass, a, b


def finger_bar(bar0: int, local: int, section: str, percussive: bool = False):
    """Author guitar-native arpeggio gestures around every melody peak.

    R2 used two independent layers: seven low notes plus four exposed treble
    notes. R3 instead makes each melody peak the destination of a physical
    multi-string roll. Even-numbered peaks use p-i-m/a four-contact gestures;
    odd peaks use three-contact inner-to-treble gestures. This preserves a
    singing top line without making it sound like one-finger piano melody.
    """
    chord = HARMONY[bar0]
    energy = ENERGY[section] + .022 * math.sin((local + 1) * .67)
    out = []

    melodic = base.melody(bar0, local, section)
    for j, (melody_off, melody_midi, melody_dur) in enumerate(melodic):
        melody_pos = base.top_pos(
            melody_midi,
            alt=((local + j) % 5 == 0 and section in {"development", "recap", "percussive"}),
        )
        melody_string = int(melody_pos[1])
        bass, inner_a, inner_b = _support_positions(chord, melody_string, j, local)
        gesture_id = f"r3-b{bar0 + 1:02d}-g{j}"

        # Keep the published melodic onset intact. Supporting contacts happen
        # just before it as a real rolled fingerstyle gesture, not a block chord.
        if j % 2 == 0:
            contacts = [
                (-.24, bass, .82, -.055),
                (-.145, inner_a, .66, -.025),
                (-.070, inner_b, .58, -.010),
                (0.0, melody_pos, melody_dur, .060),
            ]
        else:
            contacts = [
                (-.155, inner_a, .62, -.030),
                (-.072, inner_b, .55, -.010),
                (0.0, melody_pos, melody_dur, .055),
            ]

        # The earliest R3 melody onset can be 0.20 beat; clamp only the first
        # supporting contact, while preserving strict sequence ordering.
        starts = [max(bar0 * 4.0 + .006 * seq, bar0 * 4.0 + melody_off + delta)
                  for seq, (delta, _p, _d, _v) in enumerate(contacts)]
        # If clamping compressed the roll, spread it deterministically while
        # leaving the melody peak at its authored time whenever possible.
        peak_start = bar0 * 4.0 + melody_off
        if starts[-1] != peak_start:
            starts[-1] = peak_start
        for seq in range(1, len(starts)):
            if starts[seq] <= starts[seq - 1] + 1e-6:
                starts[seq] = starts[seq - 1] + .018
        if starts[-1] > peak_start + 1e-9:
            shift = starts[-1] - peak_start
            starts = [s - shift for s in starts]

        # Each gesture must span unique strings. In the rare case that the
        # support selector collides with the melody string, replace it with a
        # remaining chord string rather than stacking two states on one string.
        used = set()
        repaired = []
        alternatives = [p for p in VOICINGS[chord]]
        for delta, pos, dur, vel_delta in contacts:
            if pos[1] in used:
                pos = next(p for p in alternatives if p[1] not in used and p[1] != melody_string)
            used.add(pos[1])
            repaired.append((delta, pos, dur, vel_delta))
        # Always keep the actual melody as the final contact.
        repaired[-1] = (repaired[-1][0], melody_pos, repaired[-1][2], repaired[-1][3])

        for seq, ((_delta, pos, dur, vel_delta), start) in enumerate(zip(repaired, starts)):
            out.append(_arp_note(
                f"r3-b{bar0 + 1:02d}-g{j}-n{seq}",
                start,
                dur,
                pos,
                energy + vel_delta,
                gesture_id,
                seq,
                melody_peak=(seq == len(repaired) - 1),
                use_nail=(seq == len(repaired) - 1 and (bar0 + j) % 17 == 0),
            ))

    if percussive:
        if local % 2 == 0:
            out += [
                base.action(f"b{bar0+1:02d}-tap", "body_tap", bar0 * 4 + 1.50, .44, "lower_bout"),
                base.action(f"b{bar0+1:02d}-slap", "top_slap", bar0 * 4 + 3.00, .47, "soundboard"),
            ]
        else:
            out += [
                base.action(f"b{bar0+1:02d}-slap", "top_slap", bar0 * 4 + 1.50, .43, "soundboard"),
                base.action(f"b{bar0+1:02d}-ss", "string_slap", bar0 * 4 + 3.25, .46),
            ]
    return out


def build_events():
    ev = []
    for l in range(4):
        ev += base.harmonic_bar(l, l)
    for l in range(12):
        b = START["theme"] + l
        ev += finger_bar(b, l, "theme")
    for l in range(12):
        b = START["development"] + l
        ev += finger_bar(b, l, "development")
    for l in range(8):
        b = START["bridge"] + l
        ev += base.strum_bar(b, l, final_rake=l in {3, 7})
    for l in range(12):
        b = START["percussive"] + l
        ev += finger_bar(b, l, "percussive", True)
    for l in range(8):
        b = START["recap"] + l
        ev += finger_bar(b, l, "recap")
    for l in range(3):
        b = START["coda"] + l
        ev += base.harmonic_bar(b, l, final=l == 2)
    b = START["coda"] + 3
    ev.append(base.note("final-bass", b * 4, 1.85, (40, 6, 0), .46, "thumb"))
    sid = "final-rake"
    cfg = base.strum_cfg(sid, "down", 0, .54, False, True)
    for n, (m, s, f) in enumerate(VOICINGS["Em9"]):
        perf = {
            "string": s,
            "fret": f,
            "right_hand": {
                "method": "pick",
                "pluck_position": .12,
                "attack_angle_deg": cfg["attack_angle_deg"],
                "strength": cfg["entry_strength"],
            },
            "strum": deepcopy(cfg),
        }
        ev.append({
            "id": f"{sid}-{n}", "type": "note", "start_beat": b * 4 + 2.,
            "duration_beats": 1.35, "midi": m, "velocity": .56,
            "instrument_performance": perf,
        })
    return sorted(ev, key=lambda x: (float(x["start_beat"]), 0 if x["type"] == "note" else 1, x["id"]))


def build_song():
    song = base.build_song()
    song["meta"]["revision"] = "SOLO-ACOUSTIC-PROD-R3"
    return song


def validate_guitar_native_texture(events=None):
    events = build_events() if events is None else events
    arp = [e for e in events if e.get("instrument_performance", {}).get("arpeggio")]
    groups = {}
    for e in arp:
        a = e["instrument_performance"]["arpeggio"]
        groups.setdefault(a["gesture_id"], []).append(e)
    expected_bars = 12 + 12 + 12 + 8
    if len(groups) != expected_bars * 4:
        raise ValueError(f"R3 expected {expected_bars*4} arpeggio gestures, got {len(groups)}")

    melody_peaks = 0
    first_string_peaks = 0
    for gid, notes in groups.items():
        notes = sorted(notes, key=lambda e: e["instrument_performance"]["arpeggio"]["sequence_index"])
        strings = [int(e["instrument_performance"]["string"]) for e in notes]
        players = [e["instrument_performance"]["arpeggio"]["player"] for e in notes]
        if len(notes) < 3:
            raise ValueError(f"{gid}: isolated/underspecified gesture")
        if len(set(strings)) != len(strings) or len(set(strings)) < 3:
            raise ValueError(f"{gid}: gesture must span >=3 unique strings: {strings}")
        if players[-1] not in {"middle", "ring"}:
            raise ValueError(f"{gid}: melody peak not assigned to m/a finger: {players[-1]}")
        if not any(p == "thumb" for p in players) and len(notes) == 4:
            raise ValueError(f"{gid}: four-contact gesture missing thumb")
        peak = notes[-1]
        if peak.get("r3_texture_role") != "melody_peak":
            raise ValueError(f"{gid}: final contact must carry melody peak")
        melody_peaks += 1
        if int(peak["instrument_performance"]["string"]) == 1:
            first_string_peaks += 1

    first_string_ratio = first_string_peaks / max(1, melody_peaks)
    if first_string_ratio > .72:
        raise ValueError(f"R3 melody too concentrated on string 1: {first_string_ratio:.3f}")

    # No melody peak may arrive without at least two supporting contacts in the
    # previous 0.28 beat: this directly gates the user's piano-one-finger issue.
    isolated = 0
    for gid, notes in groups.items():
        notes = sorted(notes, key=lambda e: float(e["start_beat"]))
        peak = notes[-1]
        support = [e for e in notes[:-1] if 0.0 < float(peak["start_beat"]) - float(e["start_beat"]) <= .28]
        if len(support) < 2:
            isolated += 1
    if isolated:
        raise ValueError(f"R3 isolated melody peaks: {isolated}")

    return {
        "arpeggio_gesture_count": len(groups),
        "arpeggio_event_count": len(arp),
        "melody_peak_count": melody_peaks,
        "isolated_melody_peak_count": isolated,
        "first_string_melody_peak_ratio": first_string_ratio,
        "minimum_contacts_per_gesture": min(len(v) for v in groups.values()),
        "guitar_native_texture": True,
    }


# Renderer compatibility.
def bar_sigs(events):
    return base.bar_sigs(events)
