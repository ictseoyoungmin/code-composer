from copy import deepcopy

import numpy as np
import pytest

from code_composer.agent.expressive_score_plan import (
    ExpressivePlanValidationError,
    ExpressiveValidationContext,
    expressive_score_plan_from_dict,
)
from code_composer.agent.performance_ir import compile_performance_ir
from code_composer.audio.engines import engine_for_patch
from code_composer.composition.performance import attach_performance_ir, realize_performance_ir
from code_composer.performance.violin import realize_violin_performance
from code_composer.presets import materialize_preset


def _context():
    return ExpressiveValidationContext(
        section_ids=("one",), role_ids=("lead",), source_material_ids=("main",),
        section_spans={"one": (0.0, 4.0)},
    )


def _base_ir(*, local_override=False):
    events=[]
    for i,midi in enumerate((62,64,67,69)):
        ev={
            "start_beat": float(i), "duration_beats": .92, "midi": midi,
            "velocity": .60, "section_id":"one", "arrangement_role":"lead",
        }
        if local_override and i==0:
            ev["performance"]={"instrument_expression":{"bow_pressure":.91}}
        events.append(ev)
    return {
        "meta":{"global_seed":11},
        "transport":{"bpm":72,"beats_per_bar":4},
        "tonal":{"root":"E","scale":"natural_minor"},
        "form":[{"id":"one","start_bar":0,"bars":1,"energy":.6}],
        "materials":{"motifs":{"main":{"intervals":[0,2,5,7],"rhythm":[1,1,1,1]}},"progressions":{},"rhythms":{}},
        "instruments":{"lead":materialize_preset("bowed.violin.modeled_expression",role="lead")},
        "tracks":[{"id":"lead","instrument":"lead","gain":.18,"pan":0.0,"source":{"type":"resolved"},"events":events}],
        "mix":{"tail_seconds":.2,"drive":1.0,"ceiling":.95},
    }


def _plan(*, expression=True):
    phrase={
        "phrase_id":"arc","section_id":"one","role":"lead","source_material":"main",
        "start_beat":0.0,"duration_beats":4.0,
        "dynamic_curve":[[0,.60],[1,.60]],
        "timing_curve_ms":[[0,0],[1,0]],
        "gate_curve":[[0,1],[1,1]],
        "articulation_curve":[{"position":0,"articulation":"legato"}],
        "accent_points":[],"apex_position":.55,"breath_after_beats":0.0,
    }
    if expression:
        phrase["instrument_expression_curves"]={
            "bow_pressure":[[0,.42],[.5,.72],[1,.45]],
            "bow_speed":[[0,.46],[.5,.67],[1,.44]],
            "bow_position":[[0,.15],[.5,.09],[1,.14]],
            "vibrato_depth_cents":[[0,3],[.5,24],[1,8]],
            "vibrato_rate_hz":[[0,4.9],[.5,5.8],[1,5.2]],
            "vibrato_onset_s":[[0,.34],[.5,.12],[1,.22]],
        }
    return {
        "version":"1.16","narrative":{"arc":"one violin breath"},"phrases":[phrase],
        "motif_statements":[],
        "register_plans":{"lead":{"hard_range":[55,90],"preferred_range":[60,81],"center":69,"max_span":24,"min_intervoice_distance":0,"overlap_policy":"allow","motion_policy":"smooth"}},
        "orchestration_sections":{"one":{"primary_roles":["lead"],"secondary_roles":[],"decorative_roles":[],"max_simultaneous_roles":1,"allowed_overlaps":[],"phrase_gap_only_roles":[],"silence_roles":[]}},
        "transitions":[],
    }


def _realized(*, expression=True, local_override=False):
    plan=expressive_score_plan_from_dict(_plan(expression=expression))
    perf=compile_performance_ir(plan,_context(),seed=9,realization={
        "microtiming":{"enabled":False,"max_abs_ms":0.0},
        "velocity_variation":{"enabled":False,"max_abs":0.0},
        "timing_quantization_guard_ms":0.0,
        "minimum_note_gap_ms":0.0,
    })
    return realize_performance_ir(attach_performance_ir(_base_ir(local_override=local_override),perf))


def test_phrase_expression_curves_interpolate_across_multi_note_breath():
    out=_realized()
    events=out["tracks"][0]["events"]
    a=events[0]["performance"]["instrument_expression"]
    mid=events[2]["performance"]["instrument_expression"]
    tail=events[3]["performance"]["instrument_expression"]
    assert a["bow_pressure"]==pytest.approx(.42)
    assert mid["bow_pressure"]==pytest.approx(.72)
    assert mid["bow_position"]==pytest.approx(.09)
    assert mid["vibrato_depth_cents"]==pytest.approx(24)
    # Event at beat 3 sits at phrase position .75 and is already relaxing from apex.
    assert .45 < tail["bow_pressure"] < .72
    assert 8 < tail["vibrato_depth_cents"] < 24
    assert out["performance_report"]["phrases"][0]["instrument_expression_controls"]==[
        "bow_position","bow_pressure","bow_speed","vibrato_depth_cents","vibrato_onset_s","vibrato_rate_hz"
    ]


def test_event_local_instrument_expression_overrides_phrase_envelope_only_for_that_control():
    out=_realized(local_override=True)
    perf=out["tracks"][0]["events"][0]["performance"]
    assert perf["phrase_instrument_expression"]["bow_pressure"]==pytest.approx(.42)
    assert perf["instrument_expression"]["bow_pressure"]==pytest.approx(.91)
    assert perf["instrument_expression"]["bow_speed"]==pytest.approx(.46)


def test_no_phrase_expression_curves_preserves_pre_s11_performance_surface():
    out=_realized(expression=False)
    for ev in out["tracks"][0]["events"]:
        p=ev["performance"]
        assert "instrument_expression" not in p
        assert "phrase_instrument_expression" not in p
    assert "instrument_expression_controls" not in out["performance_report"]["phrases"][0]


def test_violin_mechanical_realization_preserves_phrase_authored_controls():
    out=realize_violin_performance(_realized(),"lead",config={"strict_comfort":False})
    events=out["tracks"][0]["events"]
    for ev in events:
        expr=ev["performance"]["instrument_expression"]
        phrase_expr=ev["performance"]["phrase_instrument_expression"]
        assert expr["bow_pressure"]==phrase_expr["bow_pressure"]
        assert expr["bow_speed"]==phrase_expr["bow_speed"]
        assert "violin_realization" in ev["performance"]
    assert out["violin_performance_report"]["playability"]["classification"]=="comfortable"


def test_phrase_expression_changes_s10_render_without_changing_notes_or_timing():
    expressed=realize_violin_performance(_realized(),"lead",config={"strict_comfort":False})
    control=realize_violin_performance(_realized(expression=False),"lead",config={"strict_comfort":False})
    ee=expressed["tracks"][0]["events"]; ce=control["tracks"][0]["events"]
    assert [(e["midi"],e["start_beat"],e["duration_beats"]) for e in ee]==[
        (e["midi"],e["start_beat"],e["duration_beats"]) for e in ce
    ]
    patch=expressed["instruments"]["lead"]
    sr=8000; beat_s=60/72; n=int(4.4*beat_s*sr)
    a=engine_for_patch(patch).render_track(ee,n,sr,patch,beat_s,gain=.18,pan=0.0)
    b=engine_for_patch(patch).render_track(ce,n,sr,patch,beat_s,gain=.18,pan=0.0)
    assert a is not None and b is not None and np.isfinite(a).all() and np.isfinite(b).all()
    assert not np.array_equal(a,b)


def test_invalid_phrase_expression_control_and_ranges_are_rejected():
    bad=_plan(); bad["phrases"][0]["instrument_expression_curves"]["humanize_magic"]=[[0,0],[1,1]]
    with pytest.raises(ExpressivePlanValidationError):
        expressive_score_plan_from_dict(bad)  # structural parse only
        compile_performance_ir(expressive_score_plan_from_dict(bad),_context(),seed=1)
    bad=_plan(); bad["phrases"][0]["instrument_expression_curves"]["bow_position"]=[[0,.02],[1,.14]]
    with pytest.raises(ExpressivePlanValidationError):
        compile_performance_ir(expressive_score_plan_from_dict(bad),_context(),seed=1)
