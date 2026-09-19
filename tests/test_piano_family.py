import json
from pathlib import Path
import numpy as np

from code_composer.audio.piano import render_piano_note
from code_composer.audio.piano_design import resolve_piano_design, validate_piano_design
from code_composer.analysis.piano_analysis import spectral_centroid, decay_ratio
from code_composer.agent.composition_brief import brief_from_dict
from code_composer.agent.composer_planner import compile_brief, apply_composer_plan


ROOT=Path(__file__).resolve().parents[1]


def acoustic_patch():
    return {
        "kind":"piano",
        "piano_design":{
            "family":"acoustic",
            "categories":{
                "body":"concert_grand","hammer":"medium_felt","stringing":"concert",
                "soundboard":"open_board","perspective":"player",
            },
            "controls":{"stereo_width":.84,"modal_gain":.075,"bridge_coupling":.42}
        }
    }


def electric_patch(mechanism="tine"):
    return {
        "kind":"piano",
        "piano_design":{
            "family":"electric",
            "categories":{
                "mechanism":mechanism,"pickup":"neutral","amp":"clean_combo",
                "modulation":"tremolo","perspective":"wide",
            },
            "controls":{"tremolo_depth":.16,"output_gain":.62}
        }
    }


def test_family_is_explicit_category_level_choice():
    a=resolve_piano_design(acoustic_patch())
    e=resolve_piano_design(electric_patch())
    assert a["piano_engine"]=="acoustic"
    assert "piano_graph" in a and "electric_piano_graph" not in a
    assert e["piano_engine"]=="electric"
    assert "electric_piano_graph" in e and "piano_graph" not in e
    assert a["piano_design_resolved"]["family"]=="acoustic"
    assert e["piano_design_resolved"]["family"]=="electric"


def test_old_design_without_family_remains_acoustic():
    p={"kind":"piano","piano_design":{"categories":{"body":"upright"},"controls":{}}}
    r=resolve_piano_design(p)
    assert r["piano_engine"]=="acoustic"


def test_family_specific_categories_do_not_cross():
    import pytest
    from code_composer.audio.piano_design import PianoDesignError
    with pytest.raises(PianoDesignError):
        validate_piano_design({
            "family":"electric",
            "categories":{"body":"concert_grand"},
            "controls":{}
        })
    with pytest.raises(PianoDesignError):
        validate_piano_design({
            "family":"acoustic",
            "categories":{"mechanism":"tine"},
            "controls":{}
        })


def test_acoustic_and_electric_are_not_same_engine_family():
    sr=22050
    a=render_piano_note(60,1.0,sr,acoustic_patch(),velocity=.72)
    e=render_piano_note(60,1.0,sr,electric_patch("tine"),velocity=.72)
    n=min(len(a),len(e))
    corr=float(np.corrcoef(a[:n,0],e[:n,0])[0,1])
    assert corr < .80
    # The families must have measurably different decay behavior; neither family is
    # forced to be universally longer because tine/reed designs can sustain strongly.
    assert abs(decay_ratio(a,sr)-decay_ratio(e,sr)) > .15


def test_electric_mechanisms_are_perceptually_distinct():
    sr=22050
    waves=[
        render_piano_note(64,.9,sr,electric_patch(m),velocity=.78)
        for m in ("tine","reed","digital_fm")
    ]
    corrs=[]
    for i in range(3):
        for j in range(i+1,3):
            n=min(len(waves[i]),len(waves[j]))
            corrs.append(abs(float(np.corrcoef(waves[i][:n,0],waves[j][:n,0])[0,1])))
    assert max(corrs) < .97
    cents=[spectral_centroid(x,sr,.30) for x in waves]
    assert max(cents)-min(cents) > 250


def _brief(patch):
    return {
      "source_prompt":"agent chooses piano family for musical purpose",
      "concept":"explicit piano family design",
      "hard_constraints":{},
      "transport":{"bpm":96,"beats_per_bar":4},
      "tonal":{"root":"D","scale":"major"},
      "form":{"sections":[{"id":"main","bars":2,"energy":.7}]},
      "materials":{"progression":[1,5,6,4],"motif":[0,2,4,2],"motif_rhythm":[.5,.5,.5,.5]},
      "rhythm":{
        "groove":{"steps_per_bar":16,"roles":{"kick":[0]*16,"snare":[0]*16,"hat":[0]*16}},
        "section_profiles":{"main":{"density":0,"kick":0,"snare":0,"hat":0,"fill":0}}
      },
      "orchestration":{"sections":{"main":{"foreground_mode":"lead"}}},
      "harmony":{"colors":["triad"]},
      "development":{"sections":{"main":{"stage":"establish"}}},
      "transitions":{},
      "sound_palette":{"roles":{"lead":{"patch":patch}}}
    }


def test_composer_agent_brief_compiles_electric_family():
    seed=json.loads((ROOT/"tests/fixtures/topline_ir.json").read_text())
    brief=brief_from_dict(_brief(electric_patch("reed")))
    ir=apply_composer_plan(seed,compile_brief(seed,brief))
    inst_id=ir["arrangement"]["roles"]["lead"]["instrument"]
    inst=ir["instruments"][inst_id]
    assert inst["piano_engine"]=="electric"
    assert inst["piano_design_resolved"]["categories"]["mechanism"]=="reed"
    assert "electric_piano_graph" in inst
