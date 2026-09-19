import hashlib
import numpy as np
import pytest
from code_composer.drum_analysis import analyze_drum_hit
from code_composer.percussion import render_drum_event
from code_composer.presets import PresetError, list_presets, materialize_preset
from code_composer.agent.expressive_score_plan import validate_expressive_score_plan, ExpressivePlanValidationError, ExpressiveValidationContext, expressive_score_plan_from_dict
from code_composer.composition.musical_transitions import realize_musical_transitions

SR=24000

def _s22(): return materialize_preset('drums.acoustic_kit_modeled_polished', role='drums')
def _s23(): return materialize_preset('drums.acoustic_kit_modeled_expressive', role='drums')
def _hash(y): return hashlib.sha256(y.tobytes()).hexdigest()

def test_s23_registers_separate_opt_in_expressive_preset():
    ids={x['preset_id'] for x in list_presets(engine='percussion')}
    assert 'drums.acoustic_kit_modeled_expressive' in ids
    p=_s23(); assert p['drum_graph']['performance_timbre']['enabled'] is True

def test_s23_omitted_controls_are_byte_identical_to_s22():
    a,b=_s22(),_s23()
    for kind,art in [('kick',None),('snare','center'),('hat','open'),('ride','bow'),('crash','crash'),('tom_mid','center')]:
        old=render_drum_event(kind,.10,SR,.82,seed=17,patch=a,articulation=art)
        new=render_drum_event(kind,.10,SR,.82,seed=17,patch=b,articulation=art)
        assert _hash(new)==_hash(old)

def test_s23_controls_are_deterministic():
    p=_s23()
    a=render_drum_event('snare',.10,SR,.82,seed=23,patch=p,articulation='center',strike_force=.88,strike_position=.72)
    b=render_drum_event('snare',.10,SR,.82,seed=23,patch=p,articulation='center',strike_force=.88,strike_position=.72)
    assert np.array_equal(a,b)

def test_s23_snare_force_changes_brightness_without_becoming_level_fader():
    p=_s23()
    soft=render_drum_event('snare',.10,SR,.82,seed=17,patch=p,articulation='center',strike_force=.20,strike_position=.35)
    hard=render_drum_event('snare',.10,SR,.82,seed=17,patch=p,articulation='center',strike_force=.90,strike_position=.35)
    ms,mh=analyze_drum_hit(soft,SR),analyze_drum_hit(hard,SR)
    assert mh['centroid_hz'] > ms['centroid_hz'] + 350
    rs=float(np.sqrt(np.mean(soft*soft))); rh=float(np.sqrt(np.mean(hard*hard)))
    assert .94 < rh/rs < 1.06

def test_s23_membrane_edge_position_excites_higher_modes():
    p=_s23()
    for kind in ('snare','tom_mid'):
        center=analyze_drum_hit(render_drum_event(kind,.10,SR,.82,seed=19,patch=p,articulation='center',strike_force=.62,strike_position=.10),SR)
        edge=analyze_drum_hit(render_drum_event(kind,.10,SR,.82,seed=19,patch=p,articulation='center',strike_force=.62,strike_position=.90),SR)
        assert edge['centroid_hz'] > center['centroid_hz']

def test_s23_crash_edge_position_is_darker_with_stronger_tail():
    p=_s23()
    c=analyze_drum_hit(render_drum_event('crash',.10,SR,.82,seed=19,patch=p,articulation='crash',strike_force=.72,strike_position=.12),SR)
    e=analyze_drum_hit(render_drum_event('crash',.10,SR,.82,seed=19,patch=p,articulation='crash',strike_force=.72,strike_position=.92),SR)
    assert e['centroid_hz'] < c['centroid_hz']
    assert e['decay_time_s'] > c['decay_time_s']

def test_s23_bounds_fail_loudly_at_renderer():
    p=_s23()
    with pytest.raises(ValueError): render_drum_event('snare',.1,SR,.8,patch=p,strike_force=1.1)
    with pytest.raises(ValueError): render_drum_event('snare',.1,SR,.8,patch=p,strike_position=-.1)

def test_s23_patch_parameter_bounds_fail_loudly():
    with pytest.raises(PresetError):
        materialize_preset('drums.acoustic_kit_modeled_expressive', role='drums', patch_overrides={'drum_graph':{'performance_timbre':{'force_brightness':2.0}}})
    with pytest.raises(PresetError):
        materialize_preset('drums.acoustic_kit_modeled_expressive', role='drums', patch_overrides={'drum_graph':{'voicing_polish':{'enabled':False},'performance_timbre':{'enabled':True}}})

def _register_plan(lo,hi,center):
    return {"hard_range":[lo,hi],"preferred_range":[lo,hi],"center":center,"max_span":max(12,hi-lo),"min_intervoice_distance":0,"overlap_policy":"allow","motion_policy":"smooth"}

def _transition_with_controls(force=.7,position=.8):
    return {
        "from_section":"a","to_section":"b",
        "harmonic_anticipation":{"enabled":False},"pickup":{"enabled":False},
        "bass_approach":{"type":"none"},"cadence_extension":{},"texture_subtraction":{},"silence_beats":0.0,
        "register_preparation":{},
        "rhythm_fill":{"role":"drums","events":[{"offset_beats":-.5,"drum":"snare","duration_beats":.1,"velocity":.8,"strike_force":force,"strike_position":position}]},
    }

def _plan_for_validation(transition):
    return {
        "version":"1.16","narrative":{"arc":"S23 strike-control validation"},
        "phrases":[],"motif_statements":[],
        "register_plans":{"lead":_register_plan(48,84,66),"pad":_register_plan(36,72,54),"bass":_register_plan(28,52,40)},
        "orchestration_sections":{
            "a":{"primary_roles":["lead"],"secondary_roles":["pad","bass"],"decorative_roles":["drums"],"max_simultaneous_roles":4,"allowed_overlaps":[],"phrase_gap_only_roles":[],"silence_roles":[]},
            "b":{"primary_roles":["lead"],"secondary_roles":["pad","bass"],"decorative_roles":["drums"],"max_simultaneous_roles":4,"allowed_overlaps":[],"phrase_gap_only_roles":[],"silence_roles":[]},
        },
        "transitions":[transition],
    }

def _ctx():
    return ExpressiveValidationContext(section_ids=("a","b"),role_ids=("lead","pad","bass","drums"),source_material_ids=("main",),section_spans={"a":(0.0,4.0),"b":(4.0,8.0)})

def test_s23_schema_accepts_and_validator_rejects_out_of_range_controls():
    plan=expressive_score_plan_from_dict(_plan_for_validation(_transition_with_controls()))
    validate_expressive_score_plan(plan,_ctx())
    bad=_transition_with_controls(force=1.2)
    plan=expressive_score_plan_from_dict(_plan_for_validation(bad))
    with pytest.raises(ExpressivePlanValidationError): validate_expressive_score_plan(plan,_ctx())

def _perf(transitions):
    sections={sid:{"primary_roles":["lead"],"secondary_roles":["pad","bass"],"decorative_roles":["drums"],"max_simultaneous_roles":4,"allowed_overlaps":[],"phrase_gap_only_roles":[],"silence_roles":[]} for sid in ("a","b")}
    return {"version":"1.16","phrases":[],"motif_statements":[],"register_plans":{"lead":_register_plan(48,84,66),"pad":_register_plan(36,72,54),"bass":_register_plan(28,52,40)},"orchestration_sections":sections,"transitions":transitions,"realization":{"seed":7,"microtiming":{"enabled":False,"max_abs_ms":0.0},"velocity_variation":{"enabled":False,"max_abs":0.0},"timing_quantization_guard_ms":0.0,"minimum_note_gap_ms":0.0}}

def _ir(transitions):
    return {"meta":{"global_seed":7,"sample_rate":24000},"transport":{"bpm":100,"beats_per_bar":4},"tonal":{"root":"D","scale":"major"},"form":[{"id":"a","start_bar":0,"bars":1},{"id":"b","start_bar":1,"bars":1}],"materials":{"motifs":{"main":{"intervals":[0],"rhythm":[1.0]}},"progressions":{},"rhythms":{}},"performance_ir":_perf(transitions),"tracks":[{"id":"lead","source":{"type":"resolved"},"events":[]},{"id":"pad","source":{"type":"resolved"},"events":[]},{"id":"bass","source":{"type":"resolved"},"events":[]},{"id":"drums","source":{"type":"resolved"},"events":[]}]}

def test_s23_transition_propagates_authored_strike_controls():
    out=realize_musical_transitions(_ir([_transition_with_controls(.73,.81)]))
    drums=next(t for t in out['tracks'] if t['id']=='drums')
    event=next(e for e in drums['events'] if e.get('transition_material')=='rhythm_fill')
    assert event['strike_force']==pytest.approx(.73)
    assert event['strike_position']==pytest.approx(.81)
