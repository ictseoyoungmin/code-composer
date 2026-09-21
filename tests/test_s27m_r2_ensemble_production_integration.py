from copy import deepcopy
import json
from pathlib import Path

import jsonschema
import pytest

from code_composer.agent.expressive_score_plan import (
    ExpressiveValidationContext,
    expressive_score_plan_from_dict,
    validate_expressive_score_plan,
)
from code_composer.composition.ensemble_interaction import (
    EnsembleInteractionError,
    realize_ensemble_interaction,
    validate_ensemble_interaction_contract,
)


def _interaction():
    return {
        "enabled": True,
        "leader_role": "violin",
        "timing_offsets_ms": {},
        "overlap_velocity_scales": {},
        "role_velocity_scales": {"piano": 0.9, "bass": 0.95},
        "targeted_onset_yields": [
            {
                "leader_role": "drums",
                "leader_event_selector": {"event_type": "drum", "drums": ["kick"]},
                "window_ms": 100.0,
                "support_velocity_scales": {"piano": 0.72, "bass": 0.82},
            }
        ],
    }


def _perf(interaction=None):
    cfg = {
        "primary_roles": ["violin"],
        "secondary_roles": ["piano", "bass"],
        "decorative_roles": ["drums"],
        "max_simultaneous_roles": 4,
        "allowed_overlaps": [],
        "phrase_gap_only_roles": [],
        "silence_roles": [],
    }
    if interaction is not None:
        cfg["ensemble_interaction"] = interaction
    return {
        "version": "1.16",
        "phrases": [],
        "motif_statements": [],
        "register_plans": {
            "violin": {"hard_range": [55, 96], "preferred_range": [60, 88], "center": 72, "max_span": 24, "min_intervoice_distance": 0, "overlap_policy": "allow", "motion_policy": "free"},
            "piano": {"hard_range": [21, 108], "preferred_range": [36, 88], "center": 60, "max_span": 60, "min_intervoice_distance": 0, "overlap_policy": "allow", "motion_policy": "free"},
            "bass": {"hard_range": [28, 64], "preferred_range": [32, 55], "center": 43, "max_span": 24, "min_intervoice_distance": 0, "overlap_policy": "allow", "motion_policy": "free"},
        },
        "orchestration_sections": {"one": cfg},
        "transitions": [],
        "realization": {"seed": 1, "microtiming": {"enabled": False, "max_abs_ms": 0.0}, "velocity_variation": {"enabled": False, "max_abs": 0.0}, "timing_quantization_guard_ms": 0.0, "minimum_note_gap_ms": 0.0},
    }


def _note(start, dur, midi, velocity):
    return {"start_beat": float(start), "duration_beats": float(dur), "midi": int(midi), "velocity": float(velocity), "section_id": "one"}


def _ir(interaction=None):
    return {
        "meta": {"global_seed": 1, "sample_rate": 24000},
        "transport": {"bpm": 120, "beats_per_bar": 4},
        "tonal": {"root": "C", "scale": "major"},
        "form": [{"id": "one", "start_bar": 0, "bars": 2, "energy": 0.6}],
        "materials": {"motifs": {}, "progressions": {}, "rhythms": {}},
        "instruments": {},
        "tracks": [
            {"id": "violin", "arrangement_role": "violin", "events": [_note(0, 2, 69, 0.8)]},
            {"id": "piano", "arrangement_role": "piano", "events": [
                _note(0.0, 2.0, 60, 0.8),
                _note(1.0, 0.5, 64, 0.8),
                _note(1.1, 0.5, 67, 0.8),
                {"event_type": "piano_control", "control": "sustain_pedal", "start_beat": 1.0, "duration_beats": 0.0, "points": [[0, 1], [0.1, 0]], "section_id": "one"},
            ]},
            {"id": "bass", "arrangement_role": "bass", "events": [_note(1.0, 1.0, 40, 0.7)]},
            {"id": "drums", "arrangement_role": "drums", "events": [
                {"event_type": "drum", "drum": "kick", "start_beat": 1.0, "duration_beats": 0.1, "velocity": 0.8, "section_id": "one"},
                {"event_type": "drum", "drum": "snare", "start_beat": 2.0, "duration_beats": 0.1, "velocity": 0.8, "section_id": "one"},
            ]},
        ],
        "mix": {"tail_seconds": 0.5},
        "performance_ir": _perf(interaction),
    }


def test_s27m_role_velocity_scales_are_section_authored_and_controls_are_untouched():
    ir = _ir(_interaction())
    control_before = deepcopy(ir["tracks"][1]["events"][3])
    out = realize_ensemble_interaction(ir)
    piano = out["tracks"][1]
    assert piano["events"][0]["velocity"] == pytest.approx(0.72)
    assert piano["events"][3] == control_before
    assert out["ensemble_interaction_report"]["sections"]["one"]["role_scaled_events"] >= 4


def test_s27m_exact_kick_coincidence_gets_full_targeted_yield_but_existing_sustain_does_not():
    out = realize_ensemble_interaction(_ir(_interaction()))
    piano = out["tracks"][1]["events"]
    # Long note began one beat before the kick: role balance only; no attack yield.
    assert piano[0]["velocity"] == pytest.approx(0.8 * 0.9)
    # Coincident note gets role balance then full authored kick yield.
    assert piano[1]["velocity"] == pytest.approx(0.8 * 0.9 * 0.72)
    assert piano[1]["ensemble_interaction"]["targeted_onset_yield"]["distance_ms"] == 0.0


def test_s27m_targeted_yield_fades_to_unity_at_window_edge():
    out = realize_ensemble_interaction(_ir(_interaction()))
    near = out["tracks"][1]["events"][2]
    # 120 BPM => 0.1 beat = 50 ms, halfway through a 100 ms window.
    expected = 0.8 * 0.9 * (1.0 - 0.5 * (1.0 - 0.72))
    assert near["velocity"] == pytest.approx(expected)
    assert near["ensemble_interaction"]["targeted_onset_yield"]["distance_ms"] == pytest.approx(50.0)


def test_s27m_selector_targets_kick_not_unselected_snare():
    ir = _ir(_interaction())
    ir["tracks"][1]["events"].append(_note(2.0, 0.5, 72, 0.8))
    out = realize_ensemble_interaction(ir)
    note = out["tracks"][1]["events"][-1]
    assert note["velocity"] == pytest.approx(0.8 * 0.9)
    assert "targeted_onset_yield" not in note.get("ensemble_interaction", {})


def test_s27m_realization_is_deterministic_and_idempotent():
    ir = _ir(_interaction())
    a = realize_ensemble_interaction(ir)
    b = realize_ensemble_interaction(ir)
    assert a == b
    assert realize_ensemble_interaction(a) == a


def test_s27m_invalid_targeted_contract_is_rejected():
    interaction = _interaction()
    interaction["targeted_onset_yields"][0]["window_ms"] = 251.0
    interaction["targeted_onset_yields"][0]["support_velocity_scales"] = {"drums": 0.8}
    ir = _ir(interaction)
    with pytest.raises(EnsembleInteractionError):
        validate_ensemble_interaction_contract(ir, ir["performance_ir"])


def test_s27m_public_schemas_and_expressive_validator_accept_new_surface():
    root = Path(__file__).resolve().parents[1]
    perf = _perf(_interaction())
    pschema = json.loads((root / "skills/code-composer/kit/schemas/performance_ir.schema.json").read_text())
    jsonschema.validate(perf, pschema)

    data = json.loads((root / "examples/v1.16/after_the_rain_expressive_score_plan.json").read_text())
    section = "dawn"
    active = (
        data["orchestration_sections"][section]["primary_roles"]
        + data["orchestration_sections"][section]["secondary_roles"]
        + data["orchestration_sections"][section]["decorative_roles"]
    )
    leader = active[0]
    support = active[1]
    data["orchestration_sections"][section]["ensemble_interaction"] = {
        "enabled": True,
        "leader_role": leader,
        "timing_offsets_ms": {},
        "overlap_velocity_scales": {},
        "role_velocity_scales": {support: 0.95},
        "targeted_onset_yields": [{
            "leader_role": leader,
            "leader_event_selector": {},
            "window_ms": 80.0,
            "support_velocity_scales": {support: 0.9},
        }],
    }
    eschema = json.loads((root / "skills/code-composer/kit/schemas/expressive_score_plan.schema.json").read_text())
    jsonschema.validate(data, eschema)
    ctx = ExpressiveValidationContext(
        section_ids=("dawn", "memory", "bloom", "stillness", "horizon"),
        role_ids=("lead", "pad", "bass", "arp", "drums", "topline"),
        source_material_ids=("motif_A",),
        section_spans={"dawn": (0, 16), "memory": (16, 32), "bloom": (32, 48), "stillness": (48, 64), "horizon": (64, 84)},
    )
    validate_expressive_score_plan(expressive_score_plan_from_dict(data), ctx)
