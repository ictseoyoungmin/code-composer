import json
from copy import deepcopy
from pathlib import Path
from _paths import SCHEMA_ROOT

import pytest
import jsonschema

from code_composer.agent.expressive_score_plan import (
    ExpressiveValidationContext,
    ExpressivePlanValidationError,
    expressive_score_plan_from_dict,
)
from code_composer.agent.performance_ir import compile_performance_ir
from code_composer.composition.motif_development import (
    MotifDevelopmentError,
    apply_transform_chain,
    motif_identity_metrics,
    realize_motif_statements,
)
from code_composer.composition.performance import attach_performance_ir, realize_performance_ir


SOURCE={"intervals":[0,1,3,4,3,1,2,0],"rhythm":[.5,.5,.5,.5,.5,.5,.5,.5]}


def _statement(op, floor=0.0):
    return {
        "statement_id":"s",
        "source_motif_id":"motif_A",
        "section_id":"one",
        "transform_chain":[op],
        "identity_floor":floor,
    }


@pytest.mark.parametrize("op,expected_intervals,expected_rhythm,shift",[
    ({"op":"exact"}, [0,1,3,4,3,1,2,0], [.5]*8, 0),
    ({"op":"fragment","start":2,"length":3}, [3,4,3], [.5]*3, 0),
    ({"op":"sequence","scale_degrees":2}, [2,3,5,6,5,3,4,2], [.5]*8, 0),
    ({"op":"transpose","semitones":2}, [0,1,3,4,3,1,2,0], [.5]*8, 2),
    ({"op":"register_shift","semitones":12}, [0,1,3,4,3,1,2,0], [.5]*8, 12),
    ({"op":"rhythm_scale","factor":1.5}, [0,1,3,4,3,1,2,0], [.75]*8, 0),
    ({"op":"rhythm_rewrite","rhythm":[.25,.25,.5,.5,.5,.75,.5,.75]}, [0,1,3,4,3,1,2,0], [.25,.25,.5,.5,.5,.75,.5,.75], 0),
    ({"op":"inversion"}, [0,-1,-3,-4,-3,-1,-2,0], [.5]*8, 0),
    ({"op":"retrograde"}, [0,2,1,3,4,3,1,0], [.5]*8, 0),
    ({"op":"cadence_rewrite","intervals":[1,0],"rhythm":[.25,.75]}, [0,1,3,4,3,1,1,0], [.5,.5,.5,.5,.5,.5,.25,.75], 0),
    ({"op":"ornament","start":2,"intervals":[2,4],"rhythm":[.125,.125]}, [0,1,3,2,4,4,3,1,2,0], [.5,.5,.5,.125,.125,.5,.5,.5,.5,.5], 0),
    ({"op":"call","intervals":[1,2,4,5],"rhythm":[.5,.5,.5,1.0]}, [1,2,4,5], [.5,.5,.5,1.0], 0),
    ({"op":"response","intervals":[4,3,1,0],"rhythm":[.5,.5,.75,1.0],"responds_to":"call_stmt"}, [4,3,1,0], [.5,.5,.75,1.0], 0),
])
def test_each_transform_is_explicit_and_deterministic(op,expected_intervals,expected_rhythm,shift):
    out=apply_transform_chain(SOURCE,_statement(op))
    assert out["intervals"]==expected_intervals
    assert out["rhythm"]==expected_rhythm
    assert out["semitone_shift"]==shift
    assert out==apply_transform_chain(SOURCE,_statement(op))


def test_identity_floor_is_qa_target_without_auto_fallback():
    stmt=_statement({"op":"inversion"},floor=.95)
    out=apply_transform_chain(SOURCE,stmt)
    assert out["identity"]["score"] < .95
    assert out["identity_target_met"] is False
    assert out["intervals"] == [0,-1,-3,-4,-3,-1,-2,0]


def test_identity_hard_min_is_explicit_compile_barrier():
    stmt=_statement({"op":"inversion"},floor=.95)
    stmt["identity_hard_min"]=.90
    with pytest.raises(MotifDevelopmentError):
        apply_transform_chain(SOURCE,stmt)


def test_identity_metrics_keep_sequence_and_rhythm_scale_recognizable():
    seq=apply_transform_chain(SOURCE,_statement({"op":"sequence","scale_degrees":2}))
    rhy=apply_transform_chain(SOURCE,_statement({"op":"rhythm_scale","factor":1.4}))
    assert seq["identity"]["score"] > .90
    assert rhy["identity"]["score"] > .90


def test_vague_rewrite_contracts_are_rejected():
    root=Path(__file__).resolve().parents[1]
    data=json.loads((root/'examples/v1.16/after_the_rain_expressive_score_plan.json').read_text())
    # Reintroduce the old vague cadence amount contract.
    t=data['motif_statements'][1]['transform_chain'][-1]
    t.clear(); t.update({'op':'cadence_rewrite','amount':.5})
    with pytest.raises(ExpressivePlanValidationError):
        plan=expressive_score_plan_from_dict(data)
        context=ExpressiveValidationContext(
            section_ids=('dawn','memory','bloom','stillness','horizon'),
            role_ids=('lead','pad','bass','arp','drums','topline'),
            source_material_ids=('motif_A',),
            section_spans={
                'dawn':(0,16),'memory':(16,32),'bloom':(32,48),
                'stillness':(48,64),'horizon':(64,84),
            },
        )
        compile_performance_ir(plan,context,seed=1)



def test_public_schema_rejects_vague_cadence_amount_contract():
    root=Path(__file__).resolve().parents[1]
    data=json.loads((root/'examples/v1.16/after_the_rain_expressive_score_plan.json').read_text())
    t=data['motif_statements'][1]['transform_chain'][-1]
    t.clear(); t.update({'op':'cadence_rewrite','amount':.5})
    schema=json.loads((SCHEMA_ROOT/'expressive_score_plan.schema.json').read_text())
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(data,schema)


def test_phrase_statement_must_belong_to_same_section():
    root=Path(__file__).resolve().parents[1]
    data=json.loads((root/'examples/v1.16/after_the_rain_expressive_score_plan.json').read_text())
    data['motif_statements'][1]['section_id']='dawn'
    plan=expressive_score_plan_from_dict(data)
    context=ExpressiveValidationContext(
        section_ids=('dawn','memory','bloom','stillness','horizon'),
        role_ids=('lead','pad','bass','arp','drums','topline'),
        source_material_ids=('motif_A',),
        section_spans={'dawn':(0,16),'memory':(16,32),'bloom':(32,48),'stillness':(48,64),'horizon':(64,84)},
    )
    with pytest.raises(ExpressivePlanValidationError):
        compile_performance_ir(plan,context,seed=1)

def _base_ir():
    events=[]
    for start,midi in [(0,62),(.5,64),(1,67),(1.5,69),(2,67),(2.5,64),(3,66),(3.5,62)]:
        events.append({
            'start_beat':start,'duration_beats':.42,'midi':midi,'velocity':.55,
            'section_id':'one','arrangement_role':'lead',
        })
    return {
        'transport':{'bpm':84,'beats_per_bar':4},
        'tonal':{'root':'D','scale':'major'},
        'form':[{'id':'one','start_bar':0,'bars':2,'energy':.7}],
        'materials':{'motifs':{'motif_A':deepcopy(SOURCE)}},
        'tracks':[{'id':'lead','source':{'type':'resolved'},'events':events}],
    }


def _plan(statement):
    return {
        'version':'1.16','narrative':{'arc':'motif development test'},
        'phrases':[{
            'phrase_id':'p','section_id':'one','role':'lead','source_material':statement['statement_id'],
            'start_beat':0.0,'duration_beats':6.0,
            'dynamic_curve':[[0,.5],[1,.5]],'timing_curve_ms':[[0,0],[1,0]],
            'gate_curve':[[0,1],[1,1]],
            'articulation_curve':[{'position':0,'articulation':'neutral'}],
            'accent_points':[],'breath_after_beats':0.0,
        }],
        'motif_statements':[statement],
        'register_plans':{'lead':{
            'hard_range':[48,84],'preferred_range':[55,76],'center':64,
            'max_span':24,'min_intervoice_distance':0,'overlap_policy':'allow','motion_policy':'smooth',
        }},
        'orchestration_sections':{'one':{
            'primary_roles':['lead'],'secondary_roles':[],'decorative_roles':[],
            'max_simultaneous_roles':1,'allowed_overlaps':[],
            'phrase_gap_only_roles':[],'silence_roles':[],
        }},
        'transitions':[],
    }


def _context():
    return ExpressiveValidationContext(
        section_ids=('one',),role_ids=('lead',),source_material_ids=('motif_A',),
        section_spans={'one':(0,8)},
    )


def test_statement_rewrites_notes_before_e1_phrase_expression():
    statement={
        'statement_id':'stmt','source_motif_id':'motif_A','section_id':'one',
        'transform_chain':[{'op':'fragment','start':0,'length':4},{'op':'sequence','scale_degrees':1}],
        'identity_floor':.55,
    }
    plan=expressive_score_plan_from_dict(_plan(statement))
    perf=compile_performance_ir(plan,_context(),seed=7,realization={
        'microtiming':{'enabled':False,'max_abs_ms':0},
        'velocity_variation':{'enabled':False,'max_abs':0},
    })
    attached=attach_performance_ir(_base_ir(),perf)
    motif_only=realize_motif_statements(attached)
    motif_events=motif_only['tracks'][0]['events']
    assert len(motif_events)==4
    assert [e['midi'] for e in motif_events] != [62,64,67,69]
    assert all(e['motif_statement']['statement_id']=='stmt' for e in motif_events)

    final=realize_performance_ir(attached)
    assert final['motif_development_resolved'] is True
    assert final['performance_resolved'] is True
    assert len(final['tracks'][0]['events'])==4
    assert all(e['performance']['phrase_id']=='p' for e in final['tracks'][0]['events'])
    assert final['motif_development_report']['phrases'][0]['statement_id']=='stmt'


def test_statement_duration_must_fit_phrase_window():
    statement={
        'statement_id':'stmt','source_motif_id':'motif_A','section_id':'one',
        'transform_chain':[{'op':'rhythm_scale','factor':2.0}],
        'identity_floor':.9,
    }
    data=_plan(statement)
    data['phrases'][0]['duration_beats']=5.0
    plan=expressive_score_plan_from_dict(data)
    perf=compile_performance_ir(plan,_context(),seed=1)
    with pytest.raises(MotifDevelopmentError):
        attach_performance_ir(_base_ir(),perf)
