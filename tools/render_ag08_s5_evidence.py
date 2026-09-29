#!/usr/bin/env python3
"""AG08-S5 continuous-performance transition evidence."""
from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path

import numpy as np

from code_composer.audio.acoustic_guitar.stateful import (
    _action_string_contact_schedule,
    _string_contact_loading_curve,
    _technique_carry_tau_scale,
)
from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files


OUT = Path(os.environ.get("AG08_S5_EVIDENCE_DIR", "artifacts/ag08-s5"))
S4 = "acoustic_guitar.steel_stateful_sympathetic"
S5 = "acoustic_guitar.steel_stateful_performance"
SR = 24000
BPM = 96
BEAT_S = 60.0 / BPM


def song(preset):
    return {
        "format": "code-composer-song/v1",
        "meta": {"title": "AG08 S5 Evidence", "global_seed": 113},
        "transport": {"bpm": BPM, "meter": {"beats_per_bar": 4, "beat_unit": 4}},
        "tonal": {"root": "E", "scale": "major"},
        "sections": [{"id": "a", "bars": 2}],
        "instruments": [{
            "id": "guitar",
            "family": "acoustic_guitar",
            "variant": "steel-string",
            "render_lock": {"preset": preset, "preset_version": "1.0.0"},
        }],
        "tracks": [{"id": "g", "function": "percussive-fingerstyle", "instrument": "guitar"}],
        "materials": [{"id": "m", "kind": "motif", "intervals": [0], "rhythm": [1]}],
        "parts": [{"id": "part", "section": "a", "track": "g", "material": "m"}],
    }


def note(
    eid, start, dur, midi, string, fret, *,
    method="finger", arpeggio=None, strum=None, left_hand=None, velocity=0.65,
):
    perf = {"string": int(string), "fret": int(fret)}
    if method is not None:
        perf["right_hand"] = {"method": method}
    if arpeggio is not None:
        perf["arpeggio"] = deepcopy(arpeggio)
    if strum is not None:
        perf["strum"] = deepcopy(strum)
    if left_hand is not None:
        perf["left_hand"] = deepcopy(left_hand)
    return {
        "id": eid,
        "type": "note",
        "start_beat": float(start),
        "duration_beats": float(dur),
        "midi": int(midi),
        "velocity": float(velocity),
        "instrument_performance": perf,
    }


def action(eid, start, kind, **parameters):
    return {
        "id": eid,
        "type": "instrument_action",
        "start_beat": float(start),
        "duration_beats": 0.08,
        "action": kind,
        "parameters": parameters,
    }


def strum_cfg(stroke_id):
    return {
        "stroke_id": stroke_id,
        "direction": "down",
        "traversal_ms": 34.0,
        "entry_strength": 0.62,
        "acceleration": 0.10,
        "pick_depth": 0.58,
        "attack_angle_deg": 42.0,
        "follow_through": 0.72,
        "accent_position": 0.50,
        "accent_amount": 0.08,
        "from_string": 6,
        "to_string": 1,
        "state": "sounding",
    }


def mixed_phrase():
    events = [
        note(
            "arp-bass", 0.00, 0.20, 48, 5, 3, method="thumb",
            arpeggio={"gesture_id": "pre-arp", "player": "thumb", "voice": "bass", "sequence_index": 0},
        ),
        note(
            "arp-inner", 0.25, 0.20, 55, 3, 0, method="finger",
            arpeggio={"gesture_id": "pre-arp", "player": "index", "voice": "inner", "sequence_index": 1},
        ),
    ]
    cfg = strum_cfg("g-down")
    for i, (midi, string, fret) in enumerate(
        [(43, 6, 3), (47, 5, 2), (50, 4, 0), (55, 3, 0), (59, 2, 0), (67, 1, 3)]
    ):
        events.append(
            note(
                f"strum-{i}", 0.65, 0.28, midi, string, fret,
                method="pick", strum=cfg,
            )
        )
    events += [
        action(
            "mute", 1.15, "muted_strum",
            strength=0.72, direction="down", traversal_ms=38.0,
            string_count=6, location="strings",
        ),
        action("slap", 1.45, "top_slap", strength=0.58, location="soundboard"),
        note(
            "post-bass", 1.75, 0.22, 40, 6, 0, method="thumb",
            arpeggio={"gesture_id": "post-arp", "player": "thumb", "voice": "bass", "sequence_index": 0},
        ),
        note(
            "post-treble", 2.00, 0.22, 59, 2, 0, method="finger",
            arpeggio={"gesture_id": "post-arp", "player": "middle", "voice": "treble", "sequence_index": 1},
        ),
    ]
    return events


def score(preset, events):
    s = song(preset)
    return s, {
        "format": "code-composer-performance-score/v1",
        "source_song": {
            "format": "code-composer-song/v1",
            "fingerprint": song_fingerprint(s),
        },
        "meta": {"title": "AG08 S5 Evidence"},
        "tracks": [{"id": "g", "events": deepcopy(events)}],
        "render": {
            "sample_rate": SR,
            "tail_seconds": 0.1,
            "mix": {
                "tracks": [{"track": "g", "gain": 0.32, "pan": 0.0, "reverb_send": 0.0}],
                "music_bus_gain": 1.0,
                "room_return_gain": 0.0,
                "master_gain": 0.8,
            },
        },
    }


def render_case(case, preset, events, suffix=""):
    s, sc = score(preset, events)
    tag = "A_S4" if preset == S4 else "B_S5"
    if suffix:
        tag += "_" + suffix
    path = OUT / f"{case}_{tag}.wav"
    result = render_song_score_to_files(
        s, sc, path, render_ir_path=OUT / f"{case}_{tag}_render_ir.json"
    )
    return path, result["audio"], result["render_ir"]


def rms(x):
    x = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(x * x))) if x.size else 0.0


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    isolated = [note("e4", 0.0, 0.70, 64, 1, 0)]
    pa0, a0, ir_a0 = render_case("isolated_e4", S4, isolated)
    pb0, b0, ir_b0 = render_case("isolated_e4", S5, isolated)
    isolated_exact = bool(np.array_equal(a0, b0))
    isolated_event_exact = ir_a0["tracks"][0]["events"] == ir_b0["tracks"][0]["events"]
    if not isolated_exact or not isolated_event_exact:
        raise AssertionError("S5 changed an isolated no-transition S4 note")

    events = mixed_phrase()
    pa, a, ir_a = render_case("mixed_transition", S4, events)
    pb, b, ir_b = render_case("mixed_transition", S5, events)
    pb2, b2, ir_b2 = render_case("mixed_transition", S5, events, "repeat")

    boundary = int(1.15 * BEAT_S * SR)
    prefix_exact = bool(np.array_equal(a[:boundary], b[:boundary]))
    deterministic = bool(np.array_equal(b, b2))
    event_exact = (
        ir_a["tracks"][0]["events"]
        == ir_b["tracks"][0]["events"]
        == ir_b2["tracks"][0]["events"]
    )
    event_count = len(ir_b["tracks"][0]["events"])
    delta_ratio = rms(b[boundary:] - a[boundary:]) / (rms(a[boundary:]) + 1e-12)
    peak = float(np.max(np.abs(b))) if b.size else 0.0

    if not prefix_exact:
        raise AssertionError("S5 changed audio before the first technique-state transition")
    if not deterministic:
        raise AssertionError("S5 mixed performance is not deterministic")
    if not event_exact or event_count != len(events):
        raise AssertionError("S5 changed authored/Render-IR event authority")
    if not (0.002 < delta_ratio < 0.55):
        raise AssertionError(f"S5 post-mute delta ratio out of bound: {delta_ratio}")
    if peak >= 0.98:
        raise AssertionError(f"S5 peak too high: {peak}")

    down = _action_string_contact_schedule(
        "muted_strum",
        {"direction": "down", "traversal_ms": 38.0, "string_count": 6},
        SR,
    )
    muted = _string_contact_loading_curve(
        0.82, "muted_strum", 0.72, 0.05, SR, 4096
    )
    dead = _string_contact_loading_curve(
        0.82, "dead_strum", 0.72, 0.05, SR, 4096
    )
    hammer_scale = _technique_carry_tau_scale(
        {"performance": {"left_hand_realization": {"technique": "hammer_on"}}},
        0.82,
    )
    dead_scale = _technique_carry_tau_scale(
        {"performance": {"left_hand_realization": {"technique": "dead_note"}}},
        0.82,
    )

    report = {
        "sample_rate": SR,
        "isolated_no_transition": {
            "sample_exact": isolated_exact,
            "event_exact": isolated_event_exact,
            "sha256_a": sha256(pa0),
            "sha256_b": sha256(pb0),
        },
        "mixed_transition": {
            "sequence": "arpeggio -> strum -> muted_strum -> top_slap -> fingerstyle",
            "prefix_exact_before_mute": prefix_exact,
            "deterministic": deterministic,
            "event_exact": event_exact,
            "render_ir_event_count": event_count,
            "delta_rms_ratio_after_mute_vs_s4": delta_ratio,
            "peak": peak,
            "sha256_a": sha256(pa),
            "sha256_b": sha256(pb),
            "sha256_b_repeat": sha256(pb2),
        },
        "string_contact": {
            "down_order": [idx + 1 for idx, _ in down],
            "down_offsets_samples": [offset for _, offset in down],
            "muted_long_term_retain": float(muted[-1]),
            "dead_long_term_retain": float(dead[-1]),
        },
        "same_string_transition": {
            "hammer_on_carry_tau_scale": float(hammer_scale),
            "dead_note_carry_tau_scale": float(dead_scale),
        },
    }

    (OUT / "REPORT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
