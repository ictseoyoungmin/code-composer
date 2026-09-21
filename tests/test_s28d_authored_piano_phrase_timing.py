from code_composer.agent.expressive_score_plan import ExpressiveValidationContext, expressive_score_plan_from_dict
from code_composer.agent.performance_ir import compile_performance_ir
from code_composer.composition.performance import attach_performance_ir, realize_performance_ir


def _base_ir():
    pitches=[60,62,64,65,67,65,62,60]
    return {
      'transport':{'bpm':92,'beats_per_bar':4},
      'form':[{'id':'one','start_bar':0,'bars':1,'energy':.6}],
      'materials':{'motifs':{'main':{'intervals':[0,2,4,5,7,5,2,0],'rhythm':[.5]*8}}},
      'tracks':[{'id':'piano','instrument':'piano','source':{'type':'resolved'},'events':[
        {'start_beat':i*.5,'duration_beats':.28,'midi':m,'velocity':.68,'section_id':'one','arrangement_role':'piano'}
        for i,m in enumerate(pitches)
      ]}],
    }


def _plan():
    return {
      'version':'1.16','narrative':{'arc':'forward rise then relaxed resolution'},
      'phrases':[{'phrase_id':'piano_direction','section_id':'one','role':'piano','source_material':'main',
        'start_beat':0.0,'duration_beats':4.0,
        'dynamic_curve':[[0,.68],[1,.68]],
        'timing_curve_ms':[[0,0.0],[.43,-8.0],[.72,2.0],[1,8.0]],
        'gate_curve':[[0,.96],[.43,1.03],[.72,.98],[1,.92]],
        'articulation_curve':[{'position':0,'articulation':'neutral'}],
        'accent_points':[],'apex_position':.43,'breath_after_beats':0.0}],
      'motif_statements':[],
      'register_plans':{'piano':{'hard_range':[36,96],'preferred_range':[48,84],'center':64,'max_span':36,'min_intervoice_distance':0,'overlap_policy':'allow','motion_policy':'smooth'}},
      'orchestration_sections':{'one':{'primary_roles':['piano'],'secondary_roles':[],'decorative_roles':[],'max_simultaneous_roles':1,'allowed_overlaps':[],'phrase_gap_only_roles':[],'silence_roles':[]}},
      'transitions':[],
    }


def _realized(seed=2814):
    ctx=ExpressiveValidationContext(section_ids=('one',),role_ids=('piano',),source_material_ids=('main',),section_spans={'one':(0.0,4.0)})
    perf=compile_performance_ir(expressive_score_plan_from_dict(_plan()),ctx,seed=seed,realization={
      'microtiming':{'enabled':False,'max_abs_ms':0.0},
      'velocity_variation':{'enabled':False,'max_abs':0.0},
      'timing_quantization_guard_ms':0.0,'minimum_note_gap_ms':1.0,
    })
    return realize_performance_ir(attach_performance_ir(_base_ir(),perf))


def test_directional_timing_is_authored_not_random():
    a=_realized(1); b=_realized(999)
    ea=a['tracks'][0]['events']; eb=b['tracks'][0]['events']
    assert [e['start_beat'] for e in ea]==[e['start_beat'] for e in eb]
    assert [e['duration_beats'] for e in ea]==[e['duration_beats'] for e in eb]
    assert all(e['performance']['microtiming_ms']==0.0 for e in ea)
    offsets=[e['performance']['authored_timing_ms'] for e in ea]
    assert min(offsets)<-5.0 and max(offsets)>5.0


def test_phrase_moves_forward_then_relaxes_and_varies_gate():
    out=_realized(); ev=out['tracks'][0]['events']
    offsets=[e['performance']['authored_timing_ms'] for e in ev]
    assert offsets[0] == 0.0
    assert offsets[2] < offsets[1] < 0.0
    assert offsets[3] < -5.0
    assert offsets[-1] > 5.0
    gates=[e['performance']['gate_multiplier'] for e in ev]
    assert max(gates)-min(gates) > .06
    assert len({e['midi'] for e in ev})>1


def test_score_pitch_identity_is_preserved():
    out=_realized(); base=_base_ir()
    assert [e['midi'] for e in out['tracks'][0]['events']] == [e['midi'] for e in base['tracks'][0]['events']]


def test_performance_resolution_preserves_piano_controls_without_orchestration_metadata():
    ir=_base_ir()
    ir['tracks'][0]['events'].insert(0,{
      'event_type':'piano_control','control':'sustain_pedal','start_beat':0.0,'duration_beats':.25,
      'points':[{'offset_beats':0.0,'position':0.0},{'offset_beats':.25,'position':1.0}],
    })
    ctx=ExpressiveValidationContext(section_ids=('one',),role_ids=('piano',),source_material_ids=('main',),section_spans={'one':(0.0,4.0)})
    perf=compile_performance_ir(expressive_score_plan_from_dict(_plan()),ctx,seed=2814,realization={
      'microtiming':{'enabled':False,'max_abs_ms':0.0},'velocity_variation':{'enabled':False,'max_abs':0.0},
      'timing_quantization_guard_ms':0.0,'minimum_note_gap_ms':1.0,
    })
    out=realize_performance_ir(attach_performance_ir(ir,perf))
    controls=[e for e in out['tracks'][0]['events'] if e.get('event_type')=='piano_control']
    assert len(controls)==1
    assert 'orchestration_budget' not in controls[0]
    assert controls[0]['points'][1]['position']==1.0


def test_phrase_resolution_never_adds_note_fields_to_piano_control_inside_phrase():
    ir=_base_ir()
    control={
      'event_type':'piano_control','control':'sustain_pedal','start_beat':1.0,'duration_beats':2.0,
      'points':[{'offset_beats':0.0,'position':1.0},{'offset_beats':2.0,'position':0.0}],
    }
    ir['tracks'][0]['events'].append(control)
    ctx=ExpressiveValidationContext(section_ids=('one',),role_ids=('piano',),source_material_ids=('main',),section_spans={'one':(0.0,4.0)})
    perf=compile_performance_ir(expressive_score_plan_from_dict(_plan()),ctx,seed=2814,realization={
      'microtiming':{'enabled':False,'max_abs_ms':0.0},'velocity_variation':{'enabled':False,'max_abs':0.0},
      'timing_quantization_guard_ms':0.0,'minimum_note_gap_ms':1.0,
    })
    out=realize_performance_ir(attach_performance_ir(ir,perf))
    got=[e for e in out['tracks'][0]['events'] if e.get('event_type')=='piano_control'][0]
    assert got == control
    assert 'velocity' not in got
    assert 'performance' not in got
