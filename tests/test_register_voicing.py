from copy import deepcopy

import pytest

from code_composer.composition.register_voicing import (
    RegisterVoicingError,
    realize_register_and_voicing,
    validate_register_voicing_contract,
)
from code_composer.analysis.register_analysis import analyze_register_collisions


def _perf(register_plans, orchestration=None):
    roles=list(register_plans)
    if orchestration is None:
        orchestration={
            "one":{
                "primary_roles":[roles[0]] if roles else [],
                "secondary_roles":roles[1:],
                "decorative_roles":[],
                "max_simultaneous_roles":max(1,len(roles)),
                "allowed_overlaps":[],
                "phrase_gap_only_roles":[],
                "silence_roles":[],
            }
        }
    return {
        "version":"1.16",
        "phrases":[],
        "motif_statements":[],
        "register_plans":register_plans,
        "orchestration_sections":orchestration,
        "transitions":[],
        "realization":{
            "seed":1,
            "microtiming":{"enabled":False,"max_abs_ms":0.0},
            "velocity_variation":{"enabled":False,"max_abs":0.0},
            "timing_quantization_guard_ms":0.0,
            "minimum_note_gap_ms":0.0,
        },
    }


def _plan(hard, preferred, center, max_span=24, spacing=0, motion="smooth", overlap="avoid"):
    return {
        "hard_range":list(hard),
        "preferred_range":list(preferred),
        "center":center,
        "max_span":max_span,
        "min_intervoice_distance":spacing,
        "overlap_policy":overlap,
        "motion_policy":motion,
    }


def test_monophonic_allocation_preserves_pitch_class_and_hits_preferred_range():
    ir={
        "performance_ir":_perf({"lead":_plan((48,84),(60,72),66)}),
        "tracks":[{"id":"lead","events":[
            {"start_beat":0.0,"duration_beats":1.0,"midi":48,"velocity":.6,"section_id":"one"},
            {"start_beat":1.0,"duration_beats":1.0,"midi":50,"velocity":.6,"section_id":"one"},
        ]}],
    }
    out=realize_register_and_voicing(ir)
    notes=[e["midi"] for e in out["tracks"][0]["events"]]
    assert notes==[60,62]
    assert all((a-b)%12==0 for a,b in zip(notes,[48,50]))
    assert all(60 <= n <= 72 for n in notes)


def test_chord_voicing_respects_hard_range_span_and_spacing():
    plan=_plan((43,65),(48,60),54,max_span=12,spacing=3,motion="smooth")
    ir={
        "performance_ir":_perf({"pad":plan}),
        "tracks":[{"id":"pad","events":[
            {"start_beat":0.0,"duration_beats":2.0,"midi":72,"velocity":.5,"section_id":"one"},
            {"start_beat":0.0,"duration_beats":2.0,"midi":76,"velocity":.5,"section_id":"one"},
            {"start_beat":0.0,"duration_beats":2.0,"midi":79,"velocity":.5,"section_id":"one"},
        ]}],
    }
    out=realize_register_and_voicing(ir)
    notes=sorted(e["midi"] for e in out["tracks"][0]["events"])
    assert notes==[48,52,55]
    assert notes[-1]-notes[0] <= 12
    assert min(b-a for a,b in zip(notes,notes[1:])) >= 3


def test_smooth_motion_prefers_nearby_second_voicing():
    plan=_plan((48,84),(55,72),64,max_span=16,spacing=3,motion="smooth")
    ir={
        "performance_ir":_perf({"pad":plan}),
        "tracks":[{"id":"pad","events":[
            {"start_beat":0.0,"duration_beats":1.0,"midi":60,"velocity":.5,"section_id":"one"},
            {"start_beat":0.0,"duration_beats":1.0,"midi":64,"velocity":.5,"section_id":"one"},
            {"start_beat":0.0,"duration_beats":1.0,"midi":67,"velocity":.5,"section_id":"one"},
            {"start_beat":1.0,"duration_beats":1.0,"midi":74,"velocity":.5,"section_id":"one"},
            {"start_beat":1.0,"duration_beats":1.0,"midi":77,"velocity":.5,"section_id":"one"},
            {"start_beat":1.0,"duration_beats":1.0,"midi":81,"velocity":.5,"section_id":"one"},
        ]}],
    }
    out=realize_register_and_voicing(ir)
    second=sorted(e["midi"] for e in out["tracks"][0]["events"] if e["start_beat"]==1.0)
    assert second==[62,65,69]


def test_impossible_octave_equivalent_range_fails_instead_of_changing_pitch_class():
    plan=_plan((62,71),(62,71),66)
    ir={
        "performance_ir":_perf({"lead":plan}),
        "tracks":[{"id":"lead","events":[
            {"start_beat":0.0,"duration_beats":1.0,"midi":61,"velocity":.5,"section_id":"one"},
        ]}],
    }
    with pytest.raises(RegisterVoicingError):
        realize_register_and_voicing(ir)


def test_register_realization_is_deterministic_and_idempotent():
    plan=_plan((48,84),(60,72),66)
    ir={
        "performance_ir":_perf({"lead":plan}),
        "tracks":[{"id":"lead","events":[
            {"start_beat":0.0,"duration_beats":1.0,"midi":48,"velocity":.5,"section_id":"one"},
        ]}],
    }
    a=realize_register_and_voicing(ir)
    b=realize_register_and_voicing(ir)
    assert a==b
    assert realize_register_and_voicing(a)==a


def _collision_fixture(with_plans=True):
    plans={
        "lead":_plan((60,76),(64,72),68,overlap="primary_wins"),
        "pad":_plan((36,60),(43,55),50,max_span=12,spacing=3,overlap="avoid"),
        "arp":_plan((72,96),(76,88),82,overlap="short_only"),
    }
    perf=_perf(plans,{
        "one":{
            "primary_roles":["lead"],"secondary_roles":["pad"],"decorative_roles":["arp"],
            "max_simultaneous_roles":3,"allowed_overlaps":[["lead","pad"]],
            "phrase_gap_only_roles":[],"silence_roles":[],
        }
    })
    tracks=[
        {"id":"lead","events":[{"start_beat":0.0,"duration_beats":2.0,"midi":67,"velocity":.7,"section_id":"one"}]},
        {"id":"pad","events":[
            {"start_beat":0.0,"duration_beats":2.0,"midi":60,"velocity":.5,"section_id":"one"},
            {"start_beat":0.0,"duration_beats":2.0,"midi":64,"velocity":.5,"section_id":"one"},
            {"start_beat":0.0,"duration_beats":2.0,"midi":67,"velocity":.5,"section_id":"one"},
        ]},
        {"id":"arp","events":[{"start_beat":0.0,"duration_beats":.75,"midi":64,"velocity":.5,"section_id":"one"}]},
    ]
    return {"performance_ir":perf,"tracks":tracks}


def test_register_collision_score_drops_after_agent_authored_range_allocation():
    ir=_collision_fixture()
    before=analyze_register_collisions(ir)
    after_ir=realize_register_and_voicing(ir)
    after=analyze_register_collisions(after_ir)
    assert before["collision_score"] > 0
    assert after["collision_score"] < before["collision_score"] * .20
    for track in after_ir["tracks"]:
        role=track["id"]
        lo,hi=after_ir["performance_ir"]["register_plans"][role]["hard_range"]
        assert all(lo <= e["midi"] <= hi for e in track["events"])


def test_register_report_preserves_traceability():
    out=realize_register_and_voicing(_collision_fixture())
    assert out["register_voicing_resolved"] is True
    assert out["register_voicing_report"]["role_count"]==3
    pad=next(t for t in out["tracks"] if t["id"]=="pad")
    rv=pad["events"][0]["register_voicing"]
    assert rv["base_midi"] in {60,64,67}
    assert rv["resolved_midi"]==pad["events"][0]["midi"]
    assert rv["octave_shift"] % 12 == 0

def test_monophonic_contour_is_not_flipped_by_center_gravity_when_avoidable():
    plan=_plan((58,81),(62,76),69,motion="smooth")
    ir={
        "performance_ir":_perf({"lead":plan}),
        "tracks":[{"id":"lead","events":[
            {"start_beat":0.0,"duration_beats":1.0,"midi":69,"velocity":.5,"section_id":"one"},
            {"start_beat":1.0,"duration_beats":1.0,"midi":62,"velocity":.5,"section_id":"one"},
        ]}],
    }
    out=realize_register_and_voicing(ir)
    notes=[e["midi"] for e in out["tracks"][0]["events"]]
    assert notes==[69,62]  # do not turn an authored descent into 69 -> 74


def test_preflight_rejects_impossible_resolved_register_plan_before_synthesis():
    plan=_plan((62,71),(62,71),66)
    perf=_perf({"lead":plan})
    ir={
        "performance_ir":perf,
        "tracks":[{"id":"lead","source":{"type":"resolved"},"events":[
            {"start_beat":0.0,"duration_beats":1.0,"midi":61,"velocity":.5,"section_id":"one"},
        ]}],
    }
    with pytest.raises(RegisterVoicingError):
        validate_register_voicing_contract(ir,perf)
