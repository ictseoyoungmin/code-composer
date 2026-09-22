from copy import deepcopy

import pytest

from code_composer.composition.ensemble_interaction import (
    EnsembleInteractionError,
    realize_ensemble_interaction,
    validate_ensemble_interaction_contract,
)
from code_composer.composition.performance import realize_performance_ir


def _orch(interaction=None):
    cfg={
        "primary_roles":["violin"],
        "secondary_roles":["piano","bass"],
        "decorative_roles":["drums"],
        "max_simultaneous_roles":4,
        "allowed_overlaps":[["violin","piano"],["violin","bass"]],
        "phrase_gap_only_roles":[],
        "silence_roles":[],
    }
    if interaction is not None:
        cfg["ensemble_interaction"]=interaction
    return cfg


def _perf(interaction=None, *, ensemble=None):
    realization={
        "seed":7,
        "microtiming":{"enabled":False,"max_abs_ms":0.0},
        "velocity_variation":{"enabled":False,"max_abs":0.0},
        "timing_quantization_guard_ms":0.0,
        "minimum_note_gap_ms":0.0,
    }
    if ensemble is not None:
        realization["ensemble"]=ensemble
    return {
        "version":"1.16",
        "phrases":[],
        "motif_statements":[],
        "register_plans":{
            "violin":{"hard_range":[55,96],"preferred_range":[60,88],"center":72,"max_span":24,"min_intervoice_distance":0,"overlap_policy":"allow","motion_policy":"free"},
            "piano":{"hard_range":[21,108],"preferred_range":[36,88],"center":60,"max_span":60,"min_intervoice_distance":0,"overlap_policy":"allow","motion_policy":"free"},
            "bass":{"hard_range":[28,64],"preferred_range":[32,55],"center":43,"max_span":24,"min_intervoice_distance":0,"overlap_policy":"allow","motion_policy":"free"},
        },
        "orchestration_sections":{"one":_orch(interaction)},
        "transitions":[],
        "realization":realization,
    }


def _event(start,dur,midi,velocity=.8,role=None):
    e={
        "start_beat":float(start),"duration_beats":float(dur),"midi":int(midi),
        "velocity":float(velocity),"section_id":"one",
    }
    if role:
        e["arrangement_role"]=role
    return e


def _tracks():
    return [
        {"id":"violin","instrument":"v","source":{"type":"resolved"},"events":[
            _event(1.0,2.0,69,.8), _event(4.0,1.0,72,.75)
        ]},
        {"id":"piano","instrument":"p","source":{"type":"resolved"},"events":[
            _event(1.0,1.0,60,.8), _event(2.5,1.0,64,.8), _event(5.5,.5,67,.8)
        ]},
        {"id":"bass","instrument":"b","source":{"type":"resolved"},"events":[
            _event(1.0,2.0,40,.7)
        ]},
        {"id":"drums","instrument":"d","source":{"type":"resolved"},"events":[
            {"event_type":"drum","drum":"kick","start_beat":1.0,"duration_beats":.1,"velocity":.7,"section_id":"one"}
        ]},
    ]


def _ir(interaction=None, *, ensemble=None, graph=False):
    mix={"tail_seconds":.5}
    if graph:
        mix["graph"]={
            "tracks":{
                "violin":{"output":"music","pan":-0.10,"gain":1.0},
                "piano":{"output":"music","pan":0.10,"gain":1.0},
                "bass":{"output":"music","pan":0.0,"gain":1.0},
                "drums":{"output":"music","pan":0.0,"gain":1.0},
            },
            "buses":{"music":{"kind":"group","output":"master","gain":1.0,"fx":[]}},
            "master":{"gain":1.0,"fx":[]},
        }
    return {
        "meta":{"global_seed":1,"sample_rate":8000},
        "transport":{"bpm":120,"beats_per_bar":4},
        "tonal":{"root":"C","scale":"major"},
        "form":[{"id":"one","start_bar":0,"bars":2,"energy":.6}],
        "materials":{"motifs":{},"progressions":{},"rhythms":{}},
        "instruments":{
            "v":{"engine":"generic","kind":"pitched","oscillator":"sine","envelope":{"attack":.01,"decay":.05,"sustain":.8,"release":.1}},
            "p":{"engine":"generic","kind":"pitched","oscillator":"sine","envelope":{"attack":.01,"decay":.05,"sustain":.8,"release":.1}},
            "b":{"engine":"generic","kind":"pitched","oscillator":"sine","envelope":{"attack":.01,"decay":.05,"sustain":.8,"release":.1}},
            "d":{"kind":"percussion"},
        },
        "tracks":_tracks(),
        "mix":mix,
        "performance_ir":_perf(interaction,ensemble=ensemble),
    }


def _interaction():
    return {
        "enabled":True,
        "leader_role":"violin",
        "timing_offsets_ms":{"piano":8.0,"bass":12.0,"drums":-3.0},
        "overlap_velocity_scales":{"piano":.82,"bass":.90},
    }


def test_s15_absent_surface_preserves_pre_s15_ir_exactly():
    ir=_ir()
    out=realize_ensemble_interaction(ir)
    assert out==ir


def test_s15_disabled_surface_preserves_pre_s15_ir_exactly():
    ir=_ir({"enabled":False})
    out=realize_ensemble_interaction(ir)
    assert out==ir


def test_authored_role_offsets_are_deterministic_and_bounded_to_section():
    ir=_ir(_interaction())
    a=realize_ensemble_interaction(ir)
    b=realize_ensemble_interaction(ir)
    assert a==b
    piano=next(t for t in a["tracks"] if t["id"]=="piano")
    bass=next(t for t in a["tracks"] if t["id"]=="bass")
    drums=next(t for t in a["tracks"] if t["id"]=="drums")
    # 120 BPM => 500 ms/beat.
    assert piano["events"][0]["start_beat"]==pytest.approx(1.016)
    assert bass["events"][0]["start_beat"]==pytest.approx(1.024)
    assert drums["events"][0]["start_beat"]==pytest.approx(.994)
    assert all(0.0 <= e["start_beat"] < 8.0 for t in a["tracks"] for e in t["events"])


def test_support_velocity_yield_is_overlap_weighted_and_outside_notes_stay_full():
    out=realize_ensemble_interaction(_ir(_interaction()))
    piano=next(t for t in out["tracks"] if t["id"]=="piano")
    first,partial,outside=piano["events"]
    assert first["velocity"] < .8
    assert partial["velocity"] < .8
    assert first["velocity"] < partial["velocity"]  # more overlap => stronger yield
    assert outside["velocity"]==pytest.approx(.8)
    assert first["ensemble_interaction"]["authored_overlap_velocity_scale"]==pytest.approx(.82)


def test_role_pan_offsets_add_to_existing_mix_graph_pan_without_replacing_base():
    ir=_ir(_interaction(),ensemble={
        "enabled":True,
        "role_pan_offsets":{"violin":-.08,"piano":.06,"bass":.02},
    },graph=True)
    out=realize_ensemble_interaction(ir)
    routes=out["mix"]["graph"]["tracks"]
    assert routes["violin"]["pan"]==pytest.approx(-.18)
    assert routes["piano"]["pan"]==pytest.approx(.16)
    assert routes["bass"]["pan"]==pytest.approx(.02)
    rep=out["ensemble_interaction_report"]["role_pan_offsets"]
    assert rep["piano"]=={"base_pan":.1,"offset":.06,"final_pan":.16}


def test_ensemble_realization_is_idempotent():
    out=realize_ensemble_interaction(_ir(_interaction(),ensemble={
        "enabled":True,"role_pan_offsets":{"piano":.05}
    },graph=True))
    assert realize_ensemble_interaction(out)==out


@pytest.mark.parametrize("mutator",[
    lambda p: p["orchestration_sections"]["one"]["ensemble_interaction"].update({"leader_role":"ghost"}),
    lambda p: p["orchestration_sections"]["one"]["ensemble_interaction"]["timing_offsets_ms"].update({"piano":31.0}),
    lambda p: p["orchestration_sections"]["one"]["ensemble_interaction"]["overlap_velocity_scales"].update({"piano":.49}),
    lambda p: p["realization"].update({"ensemble":{"enabled":True,"role_pan_offsets":{"ghost":.1}}}),
])
def test_invalid_ensemble_contract_is_rejected(mutator):
    ir=_ir(_interaction())
    mutator(ir["performance_ir"])
    with pytest.raises(EnsembleInteractionError):
        validate_ensemble_interaction_contract(ir,ir["performance_ir"])


def test_full_performance_realizer_applies_s15_after_phrase_pipeline():
    ir=_ir(_interaction(),ensemble={"enabled":True,"role_pan_offsets":{"piano":.05}},graph=True)
    # Empty phrase list keeps this test focused on pipeline ordering while still
    # passing the complete Performance IR contract.
    out=realize_performance_ir(ir)
    assert out["performance_resolved"] is True
    assert out["ensemble_interaction_resolved"] is True
    assert out["ensemble_interaction_report"]["sections"]["one"]["yielded_events"] >= 1
    assert out["mix"]["graph"]["tracks"]["piano"]["pan"]==pytest.approx(.15)


def test_s15_public_schemas_accept_authored_ensemble_surfaces():
    import json
    from pathlib import Path
    import jsonschema

    root=Path(__file__).resolve().parents[1]
    perf=_perf(_interaction(),ensemble={
        "enabled":True,"role_pan_offsets":{"violin":-.08,"piano":.06}
    })
    schema=json.loads((root/"skills/code-composer/kit/schemas/performance_ir.schema.json").read_text())
    jsonschema.validate(perf,schema)


def test_masking_qa_recognizes_explicit_dynamic_yield_as_managed_overlap():
    from code_composer.analysis.expressive_qa import analyze_expressive_qa

    interaction=_interaction()
    perf=_perf(interaction)
    # Remove the pre-existing allowed overlap so only S15 dynamic yielding manages it.
    perf["orchestration_sections"]["one"]["allowed_overlaps"]=[]
    ir=_ir(interaction)
    ir["performance_ir"]=perf
    out=realize_ensemble_interaction(ir)
    qa=analyze_expressive_qa(out)
    assert not [i for i in qa["issues"] if i["code"]=="ORCHESTRATION_MASKING" and i.get("roles")==["violin","piano"]]
    row=next(
        r for r in qa["evidence"]["orchestration_masking"]
        if r["primary_role"]=="violin" and r["subordinate_role"]=="piano"
    )
    assert row["dynamically_managed"] is True
    assert row["ensemble_yield_scale"]==pytest.approx(.82)


def test_leader_overlap_works_when_resolved_events_omit_explicit_section_id():
    ir=_ir(_interaction())
    for track in ir["tracks"]:
        for event in track["events"]:
            event.pop("section_id",None)
    out=realize_ensemble_interaction(ir)
    piano=next(t for t in out["tracks"] if t["id"]=="piano")
    assert piano["events"][0]["velocity"] < .8
    assert out["ensemble_interaction_report"]["sections"]["one"]["yielded_events"] >= 1


def test_multiple_tracks_sharing_arrangement_role_all_receive_interaction():
    ir=_ir(_interaction())
    piano=next(t for t in ir["tracks"] if t["id"]=="piano")
    piano["arrangement_role"]="piano"
    layer=deepcopy(piano)
    layer["id"]="piano_layer"
    layer["events"]=[_event(1.25,.75,72,.6),_event(5.0,.5,76,.6)]
    ir["tracks"].append(layer)
    out=realize_ensemble_interaction(ir)
    p0=next(t for t in out["tracks"] if t["id"]=="piano")
    p1=next(t for t in out["tracks"] if t["id"]=="piano_layer")
    assert p0["events"][0]["start_beat"]==pytest.approx(1.016)
    assert p1["events"][0]["start_beat"]==pytest.approx(1.266)
    assert p0["events"][0]["velocity"] < .8
    assert p1["events"][0]["velocity"] < .6
    role_report=out["ensemble_interaction_report"]["sections"]["one"]["roles"]["piano"]
    assert role_report["timing_adjusted_events"]==5
    assert role_report["yielded_events"] >= 3


def test_s15_ensemble_interaction_keeps_control_events_byte_exact():
    ir = _ir(_interaction())
    violin = next(t for t in ir["tracks"] if t["id"] == "violin")
    piano = next(t for t in ir["tracks"] if t["id"] == "piano")
    drums = next(t for t in ir["tracks"] if t["id"] == "drums")
    violin_control = {
        "event_type": "violin_control",
        "control": "bow_pressure",
        "start_beat": 1.25,
        "duration_beats": 0.5,
        "points": [[0.0, 0.4], [0.5, 0.6]],
        "section_id": "one",
    }
    piano_control = {
        "event_type": "piano_control",
        "control": "sustain_pedal",
        "start_beat": 1.0,
        "duration_beats": 0.25,
        "points": [[0.0, 1.0], [0.25, 0.0]],
        "section_id": "one",
    }
    drum_control = {
        "event_type": "drum_control",
        "control": "hi_hat_pedal_openness",
        "start_beat": 1.0,
        "duration_beats": 0.5,
        "points": [[0.0, 1.0], [0.5, 0.2]],
        "section_id": "one",
    }
    violin["events"].append(deepcopy(violin_control))
    piano["events"].append(deepcopy(piano_control))
    drums["events"].append(deepcopy(drum_control))

    out = realize_ensemble_interaction(ir)
    out_violin = next(t for t in out["tracks"] if t["id"] == "violin")
    out_piano = next(t for t in out["tracks"] if t["id"] == "piano")
    out_drums = next(t for t in out["tracks"] if t["id"] == "drums")

    assert out_violin["events"][-1] == violin_control
    assert out_piano["events"][-1] == piano_control
    assert out_drums["events"][-1] == drum_control
    assert out["ensemble_interaction_report"]["sections"]["one"]["leader_event_count"] == 2
