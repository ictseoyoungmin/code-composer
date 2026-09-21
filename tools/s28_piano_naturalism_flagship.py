from pathlib import Path
import copy, json, wave
import numpy as np
from code_composer.render import render
from code_composer.presets import materialize_preset
from code_composer.audio.piano_design import resolve_piano_design
from code_composer.agent.expressive_score_plan import ExpressiveValidationContext, expressive_score_plan_from_dict
from code_composer.agent.performance_ir import compile_performance_ir
from code_composer.composition.performance import attach_performance_ir, realize_performance_ir

SR=24000; BPM=92.0; BEAT_S=60/BPM
OUT=Path('/mnt/data/s28_piano_naturalism_flagship'); OUT.mkdir(parents=True,exist_ok=True)
NATURAL=resolve_piano_design(materialize_preset('piano.concert_grand_natural', role='piano'))
STATIC=copy.deepcopy(NATURAL)
for k in STATIC['piano_graph']['strike_identity']:
    STATIC['piano_graph']['strike_identity'][k]=0.0

CHORDS=[
 (0.0,3.45,[38,50,57,62,64,74]),
 (4.0,3.45,[34,46,53,58,62,69]),
 (8.0,3.45,[31,43,50,55,59,67]),
 (12.0,3.45,[36,48,55,60,64,72]),
]
ROLL=[0,4,8,11,13,15]
PHRASE_PITCH=[60,60,62,64,65,67,65,60]

def controls():
    out=[]
    for bar in range(4):
        st=bar*4.0
        pts=[(0,1.0),(3.86,1.0),(3.94,0.0),(4.0,0.0)] if bar==0 else [(0,0.0),(.04,1.0),(3.86,1.0),(3.94,0.0),(4.0,0.0)]
        out.append({'event_type':'piano_control','control':'sustain_pedal','start_beat':st,'duration_beats':4.0,
                    'points':[{'offset_beats':x,'position':y} for x,y in pts]})
    return out

def score(treated):
    ev=[]
    for st,dur,midis in CHORDS:
        for i,m in enumerate(midis):
            perf={}
            if treated: perf['piano_attack_offset_ms']=ROLL[i]
            ev.append({'midi':m,'start_beat':st,'duration_beats':dur,'velocity':min(.86,.58+.035*i),'performance':perf,'section_id':'chords','arrangement_role':'piano'})
    ev += controls()
    for i,m in enumerate(PHRASE_PITCH):
        ev.append({'midi':m,'start_beat':16+i*.5,'duration_beats':.28,'velocity':.68,'section_id':'phrase','arrangement_role':'piano'})
    return sorted(ev,key=lambda x:(x['start_beat'],0 if x.get('event_type')=='piano_control' else 1,x.get('midi',0)))

def base_ir(treated):
    patch=NATURAL if treated else STATIC
    return {'meta':{'global_seed':2820,'sample_rate':SR},'transport':{'bpm':BPM,'beats_per_bar':4},
      'tonal':{'root':'D','scale':'minor'},
      'form':[{'id':'chords','start_bar':0,'bars':4,'energy':.55},{'id':'phrase','start_bar':4,'bars':1,'energy':.62}],
      'materials':{'motifs':{'piano_phrase':{'intervals':[0,0,2,4,5,7,5,0],'rhythm':[.5]*8}},'progressions':{},'rhythms':{}},
      'instruments':{'piano':patch},
      'tracks':[{'id':'piano','instrument':'piano','source':{'type':'resolved'},'events':score(treated),'gain':.92}],
      'mix':{'tail_seconds':1.4,'drive':1.05,'ceiling':.95}}

def apply_phrase(ir):
    plan={'version':'1.16','narrative':{'arc':'forward rise then relaxed resolution'},'phrases':[{
      'phrase_id':'natural_phrase','section_id':'phrase','role':'piano','source_material':'piano_phrase','start_beat':16.0,'duration_beats':4.0,
      'dynamic_curve':[[0,.68],[1,.68]],'timing_curve_ms':[[0,0],[.43,-8],[.72,2],[1,8]],
      'gate_curve':[[0,.96],[.43,1.03],[.72,.98],[1,.92]],'articulation_curve':[{'position':0,'articulation':'neutral'}],
      'accent_points':[],'apex_position':.43,'breath_after_beats':0.0}],
      'motif_statements':[],'register_plans':{'piano':{'hard_range':[28,96],'preferred_range':[40,84],'center':60,'max_span':48,'min_intervoice_distance':0,'overlap_policy':'allow','motion_policy':'smooth'}},
      'orchestration_sections':{
        'chords':{'primary_roles':['piano'],'secondary_roles':[],'decorative_roles':[],'max_simultaneous_roles':1,'allowed_overlaps':[],'phrase_gap_only_roles':[],'silence_roles':[]},
        'phrase':{'primary_roles':['piano'],'secondary_roles':[],'decorative_roles':[],'max_simultaneous_roles':1,'allowed_overlaps':[],'phrase_gap_only_roles':[],'silence_roles':[]}},
      'transitions':[]}
    ctx=ExpressiveValidationContext(section_ids=('chords','phrase'),role_ids=('piano',),source_material_ids=('piano_phrase',),section_spans={'chords':(0,16),'phrase':(16,20)})
    perf=compile_performance_ir(expressive_score_plan_from_dict(plan),ctx,seed=2820,realization={
      'microtiming':{'enabled':False,'max_abs_ms':0.0},'velocity_variation':{'enabled':False,'max_abs':0.0},
      'timing_quantization_guard_ms':0.0,'minimum_note_gap_ms':1.0})
    return realize_performance_ir(attach_performance_ir(ir,perf))

def wavcat(a,b,out,gap=.6):
    xs=[]
    for p in (a,b):
        with wave.open(str(p),'rb') as wf:
            x=np.frombuffer(wf.readframes(wf.getnframes()),dtype=np.int16).reshape(-1,wf.getnchannels()); sr=wf.getframerate()
        xs += [x,np.zeros((int(gap*sr),2),dtype=np.int16)]
    y=np.concatenate(xs[:-1])
    with wave.open(str(out),'wb') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(y.tobytes())

baseline=base_ir(False)
treatment=apply_phrase(base_ir(True))
p0=OUT/'01_S28A_R2_STATIC_GRID_BASELINE.wav'; p1=OUT/'02_S28A_TO_D_NATURALISM_TREATMENT.wav'
a,_,_=render(baseline,p0); b,_,_=render(treatment,p1); wavcat(p0,p1,OUT/'03_BASELINE_then_S28A_TO_D_AB.wav')
# extract phrase only from master wave arrays for quick comparison
start=int(15.5*SR); end=min(len(a),int(20.0*SR))
def write(path,x):
    q=np.clip(x,-1,1); q=(q*32767).astype(np.int16)
    with wave.open(str(path),'wb') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(q.tobytes())
write(OUT/'04_BASELINE_PHRASE_WINDOW.wav',a[start:end]); write(OUT/'05_TREATMENT_PHRASE_WINDOW.wav',b[start:end]); wavcat(OUT/'04_BASELINE_PHRASE_WINDOW.wav',OUT/'05_TREATMENT_PHRASE_WINDOW.wav',OUT/'06_PHRASE_WINDOW_AB.wav',gap=.35)
metrics={'sample_rate':SR,'bpm':BPM,'score_notes_identical':True,'pedal_timeline_identical':True,
         'treatment_features':['S28-A R2 continuous pedal','S28-B per-strike identity','S28-C authored chord hand-roll','S28-D authored phrase timing/gate'],
         'random_microtiming':False,'random_velocity_variation':False}
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
(OUT/'README.md').write_text('''# S28 Piano Naturalism Flagship\n\n01 baseline: S28-A R2 continuous pedal is present, but repeated strikes use static identity, wide chords are exact-sample simultaneous, and the final phrase is exact-grid with fixed gates.\n02 treatment: same score and pedal timeline + S28-B deterministic per-strike identity + S28-C authored 0..15 ms chord hand-roll + S28-D authored directional timing/gate curves with random microtiming disabled.\n03 is the full A/B. 04/05/06 isolate the final repeated-note phrase.\n''',encoding='utf-8')
print(json.dumps(metrics,indent=2))
