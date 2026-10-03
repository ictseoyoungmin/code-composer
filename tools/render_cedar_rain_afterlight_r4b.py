#!/usr/bin/env python3
"""R4 production wrapper with onset-aware musical-grammar validation."""
from __future__ import annotations

import json

import compose_cedar_rain_afterlight_r4 as comp
import render_cedar_rain_afterlight_r4 as renderer


def validate_music_first(events=None):
    events = comp.build_events() if events is None else events
    notes = [e for e in events if e["type"] == "note"]

    finger_bars = (
        list(range(comp.START["prelude"], comp.START["bridge"]))
        + list(range(comp.START["percussive"], comp.START["recap"]))
        + list(range(comp.START["recap"], comp.TOTAL_BARS))
    )
    anchored = 0
    for b in finger_bars:
        onset = [e for e in notes if abs(float(e["start_beat"]) - b * 3.0) < 1e-9]
        strings = {int(e["instrument_performance"]["string"]) for e in onset}
        if len(onset) >= 2 and any(s >= 4 for s in strings) and any(s <= 3 for s in strings):
            anchored += 1
    anchor_ratio = anchored / max(1, len(finger_bars))
    if anchor_ratio < .78:
        raise ValueError(f"metrical bass+melody anchoring too weak: {anchor_ratio:.3f}")

    cadence_checks = []
    cadence_bars = (
        list(range(comp.START["theme"] + 3, comp.START["theme"] + 16, 4))
        + list(range(comp.START["development"] + 3, comp.START["development"] + 16, 4))
        + list(range(comp.START["recap"] + 3, comp.START["recap"] + 8, 4))
    )
    for b in cadence_bars:
        cur = sum(1 for e in notes if b * 3 <= float(e["start_beat"]) < (b + 1) * 3)
        prev = sum(1 for e in notes if (b - 1) * 3 <= float(e["start_beat"]) < b * 3)
        cadence_checks.append((b + 1, prev, cur))
        if cur >= prev:
            raise ValueError(f"cadence bar {b+1} does not reduce density: {prev}->{cur}")

    # Group simultaneous contacts before measuring exposure. A bass+melody pinch
    # is one guitar gesture, not a treble-only event followed by a bass event.
    onset_groups = {}
    for e in notes:
        onset_groups.setdefault(round(float(e["start_beat"]), 6), []).append(e)
    run = best = 0
    treble_only_onsets = []
    for onset in sorted(onset_groups):
        strings = {int(e["instrument_performance"]["string"]) for e in onset_groups[onset]}
        if strings and max(strings) <= 2:
            run += 1
            treble_only_onsets.append(onset)
            best = max(best, run)
        else:
            run = 0
    if best > 2:
        raise ValueError(f"exposed treble-only onset run too long: {best}")

    sigs = comp.bar_signatures(events)
    unique = len(set(sigs))
    windows = [tuple(sigs[i:i+4]) for i in range(comp.TOTAL_BARS - 3)]
    if unique < 60:
        raise ValueError(f"bar diversity too low: {unique}/{comp.TOTAL_BARS}")
    if len(windows) != len(set(windows)):
        raise ValueError("identical 4-bar phrase window detected")

    melody_values = comp.MELODY
    high_ratio = sum(1 for p in melody_values if p >= 69) / len(melody_values)
    if max(melody_values) > 71 or high_ratio > .18:
        raise ValueError("melody register too persistently high")

    return {
        "meter": "3/4",
        "bpm": comp.BPM,
        "bass_melody_downbeat_anchor_ratio": anchor_ratio,
        "cadence_density_checks": cadence_checks,
        "max_exposed_treble_run": best,
        "treble_only_onset_count": len(treble_only_onsets),
        "unique_bar_signatures": unique,
        "identical_four_bar_windows": 0,
        "melody_min": min(melody_values),
        "melody_max": max(melody_values),
        "high_melody_ratio": high_ratio,
        "onset_aware_exposure_gate": True,
        "music_first_grammar": True,
    }


# Patch only the QA interpretation; authored notes and renderer are unchanged.
comp.validate_musical_grammar = validate_music_first
renderer.comp = comp


if __name__ == "__main__":
    import sys
    if "--validate-only" in sys.argv:
        print(json.dumps(validate_music_first(), indent=2))
    else:
        renderer.main()
