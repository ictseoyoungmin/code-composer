from copy import deepcopy

import pytest

from code_composer.composition.musical_transitions import (
    MusicalTransitionError,
    realize_musical_transitions,
)


def _register_plan(lo, hi, center):
    return {
        "hard_range":[lo,hi],"preferred_range":[lo,hi],"center":center,
        "max_span":max(12,hi-lo),"min_intervoice_distance":0,
        "overlap_policy":"allow","motion_policy":"smooth",
    }


def _transition(bound=True):
    ant={
        "enabled":True,"role":"pad","beats":0.5,
        "chord_intervals":[0,2,4],"velocity":0.3,"gate":0.82,
    }
    if bound:
        ant["arrival_binding"]={"source":"destination_progression","progression_index":0}
    else:
        ant["target_degree"]=4
    return {
        "from_section":"a","to_section":"b",
        "harmonic_anticipation":ant,
        "pickup":{"enabled":False},"bass_approach":{"type":"none"},
        "cadence_extension":{},"texture_subtraction":{},"silence_beats":0.0,
        "register_preparation":{},"rhythm_fill":{},
    }


def _ir(bound=True):
    transition=_transition(bound)
    return {
        "meta":{"global_seed":31,"sample_rate":24000},
        "transport":{"bpm":112,"beats_per_bar":4},
        "tonal":{"root":"D","scale":"natural_minor"},
        "form":[{"id":"a","start_bar":0,"bars":1},{"id":"b","start_bar":1,"bars":1}],
        "materials":{
            "motifs":{"main":{"intervals":[0],"rhythm":[1.0]}},
            "progressions":{
                "home":{"degrees":[1,6,3,7]},
                "b_arrival":{"degrees":[6,7,3,1],"source_progression_id":"home"},
            },
            "rhythms":{},
        },
        "harmonic_grammar":{
            "enabled":True,
            "default":{"colors":["seventh"]},
            "sections":{"b":{"progression_variant":"b_arrival"}},
        },
        "performance_ir":{
            "version":"1.16","phrases":[],"motif_statements":[],
            "register_plans":{"pad":_register_plan(36,72,54)},
            "orchestration_sections":{
                "a":{"primary_roles":[],"secondary_roles":["pad"],"decorative_roles":[],"max_simultaneous_roles":1,"allowed_overlaps":[],"phrase_gap_only_roles":[],"silence_roles":[]},
                "b":{"primary_roles":[],"secondary_roles":["pad"],"decorative_roles":[],"max_simultaneous_roles":1,"allowed_overlaps":[],"phrase_gap_only_roles":[],"silence_roles":[]},
            },
            "transitions":[transition],
            "realization":{
                "seed":31,"microtiming":{"enabled":False,"max_abs_ms":0.0},
                "velocity_variation":{"enabled":False,"max_abs":0.0},
                "timing_quantization_guard_ms":0.0,"minimum_note_gap_ms":0.0,
            },
        },
        "tracks":[{"id":"pad","source":{"type":"resolved"},"events":[
            {"start_beat":4.0,"duration_beats":1.0,"midi":57,"velocity":0.4,"section_id":"b","harmonic_degree":6,"harmonic_progression_id":"b_arrival"}
        ]}],
    }


def _anticipation(out):
    return [e for e in out["tracks"][0]["events"] if e.get("transition_material")=="harmonic_anticipation"]


def test_s31_binding_resolves_destination_progression_degree_and_lineage():
    out=realize_musical_transitions(_ir(True))
    ant=_anticipation(out)
    assert len(ant)==3
    assert {e["musical_transition"]["target_degree"] for e in ant}=={6}
    assert ant[0]["musical_transition"]["arrival_binding"]["progression_id"]=="b_arrival"
    assert out["musical_transition_report"]["transitions"][0]["harmonic_arrival_binding_events"]==3


def test_s31_binding_tracks_destination_change_without_editing_transition_payload():
    ir=_ir(True)
    ir["materials"]["progressions"]["b_arrival"]["degrees"][0]=5
    out=realize_musical_transitions(ir)
    assert {e["musical_transition"]["target_degree"] for e in _anticipation(out)}=={5}


def test_s31_legacy_manual_target_degree_remains_supported():
    out=realize_musical_transitions(_ir(False))
    ant=_anticipation(out)
    assert {e["musical_transition"]["target_degree"] for e in ant}=={4}
    assert all("arrival_binding" not in e["musical_transition"] for e in ant)


def test_s31_binding_fails_when_destination_lineage_is_not_explicit():
    ir=_ir(True)
    ir["harmonic_grammar"]["sections"]["b"]={}
    with pytest.raises(MusicalTransitionError,match="explicit S30 progression_variant"):
        realize_musical_transitions(ir)
