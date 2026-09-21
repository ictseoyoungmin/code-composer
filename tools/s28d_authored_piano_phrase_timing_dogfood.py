from pathlib import Path
import copy, json, wave
import numpy as np
from code_composer.render import render
from code_composer.presets import materialize_preset
from code_composer.audio.piano_design import resolve_piano_design
from code_composer.agent.expressive_score_plan import ExpressiveValidationContext, expressive_score_plan_from_dict
from code_composer.agent.performance_ir import compile_performance_ir
from code_composer.composition.performance import attach_performance_ir, realize_performance_ir

SR=24000; BPM=92.0
OUT=Path('/mnt/data/s28d_piano_phrase_timing_audition'); OUT.mkdir(parents=True,exist_ok=True)
PATCH=resolve_piano_design(materialize_preset('piano.concert_grand_natural', role='piano'))
PITCHES=[60,62,64,65,67,65,62,60]

def base_ir():
    events=[{'start_beat':i*.5,'duration_beats':.28,'midi':m,'velocity':.68,'section_id':'one','arrangement_role':'piano'} for i,m in enumerate(PITCHES)]
    return {'meta':{'global_seed':2814,'sample_rate':SR},'transport':{'bpm':BPM,'beats_per_bar':4},
      'tonal':{'root':'C','scale':'major'},'form':[{'id':'one','start_bar':0,'bars':1,'energy':.6}],
      'materials':{'motifs':{'main':{'intervals':[0,2,4,5,7,5,2,0],'rhythm':[.5]*8}},'progressions':{},'rhythms':{}},
      'instruments':{'piano':PATCH},'tracks':[{'id':'piano','instrument':'piano','source':{'type':'resolved'},'events':events,'gain':.92}],
      'mix':{'tail_seconds':1.2,'drive':1.05,'ceiling':.95}}

def plan():
    return {'version':'1.16','narrative':{'arc':'forward rise then relaxed resolution'},
      'phrases':[{'phrase_id':'piano_direction','section_id':'one','role':'piano','source_material':'main','start_beat':0.0,'duration_beats':4.0,
        'dynamic_curve':[[0,.68],[1,.68]],
        'timing_curve_ms':[[0,0.0],[.43,-8.0],[.72,2.0],[1,8.0]],
        'gate_curve':[[0,.96],[.43,1.03],[.72,.98],[1,.92]],
        'articulation_curve':[{'position':0,'articulation':'neutral'}],
        'accent_points':[],'apex_position':.43,'breath_after_beats':0.0}],
      'motif_statements':[],
      'register_plans':{'piano':{'hard_range':[36,96],'preferred_range':[48,84],'center':64,'max_span':36,'min_intervoice_distance':0,'overlap_policy':'allow','motion_policy':'smooth'}},
      'orchestration_sections':{'one':{'primary_roles':['piano'],'secondary_roles':[],'decorative_roles':[],'max_simultaneous_roles':1,'allowed_overlaps':[],'phrase_gap_only_roles':[],'silence_roles':[]}},'transitions':[]}

def treated_ir():
    ir=base_ir()
    ctx=ExpressiveValidationContext(section_ids=('one',),role_ids=('piano',),source_material_ids=('main',),section_spans={'one':(0.0,4.0)})
    perf=compile_performance_ir(expressive_score_plan_from_dict(plan()),ctx,seed=2814,realization={
      'microtiming':{'enabled':False,'max_abs_ms':0.0},'velocity_variation':{'enabled':False,'max_abs':0.0},
      'timing_quantization_guard_ms':0.0,'minimum_note_gap_ms':1.0})
    return realize_performance_ir(attach_performance_ir(ir,perf))

def wavcat(a,b,out,gap=.45):
    parts=[]
    for p in (a,b):
        with wave.open(str(p),'rb') as wf:
            x=np.frombuffer(wf.readframes(wf.getnframes()),dtype=np.int16).reshape(-1,wf.getnchannels()); sr=wf.getframerate()
        parts += [x,np.zeros((int(gap*sr),2),dtype=np.int16)]
    y=np.concatenate(parts[:-1])
    with wave.open(str(out),'wb') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(y.tobytes())

base=base_ir(); treated=treated_ir()
base_path=OUT/'01_EXACT_GRID_PHRASE.wav'; treated_path=OUT/'02_S28D_AUTHORED_DIRECTION_PHRASE.wav'
render(base,base_path); render(treated,treated_path); wavcat(base_path,treated_path,OUT/'03_EXACT_GRID_then_S28D_AB.wav')
ev=treated['tracks'][0]['events']
metrics={'sample_rate':SR,'bpm':BPM,'microtiming_enabled':False,
         'authored_timing_ms':[e['performance']['authored_timing_ms'] for e in ev],
         'gate_multipliers':[e['performance']['gate_multiplier'] for e in ev],
         'realized_start_beats':[e['start_beat'] for e in ev],
         'realized_durations_beats':[e['duration_beats'] for e in ev]}
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
(OUT/'README.md').write_text('''# S28-D Authored Piano Phrase Timing\n\n01 is a perfectly quantized eighth-note phrase with fixed .28-beat gates.\n02 uses the existing v1.16 E1 timing_curve_ms + gate_curve with random microtiming and velocity variation disabled.\n03 is 01 then 02. The rising phrase pulls forward to about -8 ms, then the resolution relaxes toward +8 ms; gate length follows an authored phrase curve.\n''',encoding='utf-8')
print(json.dumps(metrics,indent=2))
