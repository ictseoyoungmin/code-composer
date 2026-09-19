import json
from pathlib import Path

import numpy as np
import pytest

from code_composer.audio.engines import engine_for_patch
from code_composer.audio.engines.bowed_string import render_bowed_string_note
from code_composer.agent.composition_brief import brief_from_dict, validate_brief, BriefValidationError
from code_composer.agent.composer_planner import compile_brief, apply_composer_plan


ROOT = Path(__file__).resolve().parents[1]


def bowed_patch():
    # Repository-only dogfood values. This patch is intentionally not shipped as an
    # agent-facing example or template.
    return {
        "kind": "bowed_string",
        "engine": "bowed_string",
        "family": "violin",
        "bowed_string_graph": {
            "strings": {"max_partials": 15, "spectral_rolloff": 1.28, "inharmonicity": .00010},
            "bow": {
                "position": .19, "pressure": .54, "speed": .63,
                "noise_gain": .014, "noise_low_hz": 900, "noise_high_hz": 7600,
                "seed": 83
            },
            "vibrato": {"rate_hz": 5.4, "depth_cents": 17, "onset_s": .20, "fade_s": .15},
            "envelope": {"attack_s": .045, "release_s": .24},
            "body": {
                "resonances_hz": [470, 860, 1510, 2840],
                "gains": [.24, .19, .13, .08],
                "q": [3.4, 4.0, 4.8, 5.6],
                "mix": .16
            },
            "stereo_width": .18,
            "output_gain": .46
        }
    }


def test_bowed_string_engine_is_registered_and_deterministic():
    p = bowed_patch()
    assert engine_for_patch(p).name == "bowed_string"
    a = render_bowed_string_note(69, .8, 22050, p, velocity=.72, performance={"articulation": "legato"})
    b = render_bowed_string_note(69, .8, 22050, p, velocity=.72, performance={"articulation": "legato"})
    assert np.array_equal(a, b)
    assert a.shape[1] == 2
    assert len(a) > int(.8 * 22050)
    assert np.max(np.abs(a)) > .01


def test_bowed_expression_is_explicit_and_changes_result():
    p = bowed_patch()
    base = render_bowed_string_note(69, .9, 22050, p, velocity=.7, performance={"articulation": "tenuto"})
    expressive = render_bowed_string_note(
        69, .9, 22050, p, velocity=.7,
        performance={
            "articulation": "tenuto",
            "instrument_expression": {
                "bow_pressure": .82,
                "vibrato_depth_cents": 34,
                "vibrato_onset_s": .05,
            },
        },
    )
    n = min(len(base), len(expressive))
    corr = float(np.corrcoef(base[:n, 0], expressive[:n, 0])[0, 1])
    assert corr < .995


def _brief(patch):
    return {
        "source_prompt": "bowed-string engine architecture dogfood",
        "concept": "explicit bowed-string family patch",
        "hard_constraints": {},
        "transport": {"bpm": 96, "beats_per_bar": 4},
        "tonal": {"root": "D", "scale": "major"},
        "form": {"sections": [{"id": "main", "bars": 2, "energy": .7}]},
        "materials": {"progression": [1, 5, 6, 4], "motif": [0, 2, 4, 2], "motif_rhythm": [.5, .5, .5, .5]},
        "rhythm": {
            "groove": {"steps_per_bar": 16, "roles": {"kick": [0]*16, "snare": [0]*16, "hat": [0]*16}},
            "section_profiles": {"main": {"density": 0, "kick": 0, "snare": 0, "hat": 0, "fill": 0}},
        },
        "orchestration": {"sections": {"main": {"foreground_mode": "lead"}}},
        "harmony": {"colors": ["triad"]},
        "development": {"sections": {"main": {"stage": "establish"}}},
        "transitions": {},
        "sound_palette": {"roles": {"lead": {"patch": patch}}},
    }


def test_brief_compiles_bowed_string_family_without_new_role_type():
    seed = json.loads((ROOT / "tests/fixtures/topline_ir.json").read_text())
    brief = brief_from_dict(_brief(bowed_patch()))
    validate_brief(brief, seed)
    ir = apply_composer_plan(seed, compile_brief(seed, brief))
    inst_id = ir["arrangement"]["roles"]["lead"]["instrument"]
    patch = ir["instruments"][inst_id]
    assert patch["engine"] == "bowed_string"
    assert patch["family"] == "violin"


def test_brief_rejects_invalid_bow_geometry():
    seed = json.loads((ROOT / "tests/fixtures/topline_ir.json").read_text())
    bad = bowed_patch()
    bad["bowed_string_graph"]["bow"]["position"] = .9
    brief = brief_from_dict(_brief(bad))
    with pytest.raises(BriefValidationError):
        validate_brief(brief, seed)
