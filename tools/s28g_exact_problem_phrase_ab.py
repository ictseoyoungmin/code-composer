from pathlib import Path
import copy, json, wave, hashlib
import numpy as np
from code_composer.render import render
from code_composer.presets import materialize_preset
from code_composer.audio.piano_design import resolve_piano_design
from code_composer.agent.expressive_score_plan import ExpressiveValidationContext, expressive_score_plan_from_dict
from code_composer.agent.performance_ir import compile_performance_ir
from code_composer.composition.performance import attach_performance_ir, realize_performance_ir

SR=24000; BPM=92.0
OUT=Path('/mnt/data/s28g_exact_problem_phrase_ab'); OUT.mkdir(parents=True,exist_ok=True)
ORIGINAL=Path('/mnt/data/s28g_repro_source/s28e_exact_problem_repro_ab/01_A_ORIGINAL_PROBLEM_S28D.wav')
A_PATCH=resolve_piano_design(materialize_preset('piano.concert_grand_natural', role='piano'))
B_PATCH=resolve_piano_design(materialize_preset('piano.concert_grand_natural_unison_subtle', role='piano'))
CHORDS=[(0.0,3.45,[38,50,57,62,64,74]),(4.0,3.45,[34,46,53,58,62,69]),(8.0,3.45,[31,43,50,55,59,67]),(12.0,3.45,[36,48,55,60,64,72])]
ROLL=[0,4,8,11,13,15]; PHRASE_PITCH=[60,60,62,64,65,67,65,60]

def controls():
    out=[]
    for bar in range(4):
        st=bar*4.0
        pts=[(0,1.0),(3.86,1.0),(3.94,0.0),(4.0,0.0)] if bar==0 else [(0,0.0),(.04,1.0),(3.86,1.0),(3.94,0.0),(4.0,0.0)]
        out.append({'event_type':'piano_control','control':'sustain_pedal','start_beat':st,'duration_beats':4.0,'points':[{'offset_beats':x,'position':y} for x,y in pts]})
    return out

def score():
    ev=[]
    for st,dur,midis in CHORDS:
        for i,m in enumerate(midis):
            ev.append({'midi':m,'start_beat':st,'duration_beats':dur,'velocity':min(.86,.58+.035*i),'performance':{'piano_attack_offset_ms':ROLL[i]},'section_id':'chords','arrangement_role':'piano'})
    ev += controls()
    for i,m in enumerate(PHRASE_PITCH):
        ev.append({'midi':m,'start_beat':16+i*.5,'duration_beats':.28,'velocity':.68,'section_id':'phrase','arrangement_role':'piano'})
    return sorted(ev,key=lambda x:(x['start_beat'],0 if x.get('event_type')=='piano_control' else 1,x.get('midi',0)))

def base_ir(patch):
    return {'meta':{'global_seed':2820,'sample_rate':SR},'transport':{'bpm':BPM,'beats_per_bar':4},'tonal':{'root':'D','scale':'minor'},
      'form':[{'id':'chords','start_bar':0,'bars':4,'energy':.55},{'id':'phrase','start_bar':4,'bars':1,'energy':.62}],
      'materials':{'motifs':{'piano_phrase':{'intervals':[0,0,2,4,5,7,5,0],'rhythm':[.5]*8}},'progressions':{},'rhythms':{}},
      'instruments':{'piano':patch},'tracks':[{'id':'piano','instrument':'piano','source':{'type':'resolved'},'events':score(),'gain':.92}],
      'mix':{'tail_seconds':1.4,'drive':1.05,'ceiling':.95}}

def apply_phrase(ir):
    plan={'version':'1.16','narrative':{'arc':'forward rise then relaxed resolution'},'phrases':[{'phrase_id':'natural_phrase','section_id':'phrase','role':'piano','source_material':'piano_phrase','start_beat':16.0,'duration_beats':4.0,'dynamic_curve':[[0,.68],[1,.68]],'timing_curve_ms':[[0,0],[.43,-8],[.72,2],[1,8]],'gate_curve':[[0,.96],[.43,1.03],[.72,.98],[1,.92]],'articulation_curve':[{'position':0,'articulation':'neutral'}],'accent_points':[],'apex_position':.43,'breath_after_beats':0.0}],
      'motif_statements':[],'register_plans':{'piano':{'hard_range':[28,96],'preferred_range':[40,84],'center':60,'max_span':48,'min_intervoice_distance':0,'overlap_policy':'allow','motion_policy':'smooth'}},
      'orchestration_sections':{'chords':{'primary_roles':['piano'],'secondary_roles':[],'decorative_roles':[],'max_simultaneous_roles':1,'allowed_overlaps':[],'phrase_gap_only_roles':[],'silence_roles':[]},'phrase':{'primary_roles':['piano'],'secondary_roles':[],'decorative_roles':[],'max_simultaneous_roles':1,'allowed_overlaps':[],'phrase_gap_only_roles':[],'silence_roles':[]}},'transitions':[]}
    ctx=ExpressiveValidationContext(section_ids=('chords','phrase'),role_ids=('piano',),source_material_ids=('piano_phrase',),section_spans={'chords':(0,16),'phrase':(16,20)})
    perf=compile_performance_ir(expressive_score_plan_from_dict(plan),ctx,seed=2820,realization={'microtiming':{'enabled':False,'max_abs_ms':0.0},'velocity_variation':{'enabled':False,'max_abs':0.0},'timing_quantization_guard_ms':0.0,'minimum_note_gap_ms':1.0})
    return realize_performance_ir(attach_performance_ir(ir,perf))

def read(path):
    with wave.open(str(path),'rb') as wf:
        return np.frombuffer(wf.readframes(wf.getnframes()),dtype=np.int16).reshape(-1,wf.getnchannels()),wf.getframerate()
def write(path,x):
    with wave.open(str(path),'wb') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(np.asarray(x,dtype=np.int16).tobytes())
def cat(a,b,path,gap=.55):
    xa,_=read(a); xb,_=read(b); z=np.zeros((int(gap*SR),2),dtype=np.int16); write(path,np.concatenate([xa,z,xb]))
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

# Re-render A through the current code to prove the baseline path is untouched.
a_render=OUT/'01_A_RERENDER_CURRENT.wav'; render(apply_phrase(base_ir(A_PATCH)),a_render)
orig,_=read(ORIGINAL); ar,_=read(a_render)
if not np.array_equal(orig,ar):
    raise RuntimeError(f'A baseline reproduction failed: original={orig.shape}, rerender={ar.shape}, maxdiff={np.max(np.abs(orig.astype(np.int32)-ar.astype(np.int32)))}')
# Use the exact original file bytes for the listening A.
a_exact=OUT/'02_A_EXACT_ORIGINAL.wav'; a_exact.write_bytes(ORIGINAL.read_bytes())
b_path=OUT/'03_B_SUBTLE_S28G.wav'; render(apply_phrase(base_ir(B_PATCH)),b_path)
cat(a_exact,b_path,OUT/'04_A_then_B_FULL.wav')
# First two held chord windows end before key release; they isolate the originally reported context.
windows=((.90,2.24,'FIRST_CHORD',5),(3.52,4.84,'SECOND_CHORD',8))
for lo,hi,label,base_no in windows:
    xa,_=read(a_exact); xb,_=read(b_path); s=int(lo*SR); e=int(hi*SR)
    pa=OUT/f'{base_no:02d}_{label}_HELD_A.wav'; pb=OUT/f'{base_no+1:02d}_{label}_HELD_B.wav'; pab=OUT/f'{base_no+2:02d}_{label}_HELD_A_then_B.wav'
    write(pa,xa[s:e]); write(pb,xb[s:e]); cat(pa,pb,pab,.30)
metrics={'sample_rate':SR,'bpm':BPM,'a_exact_sha256':sha(a_exact),'a_rerender_byte_exact_to_original':True,'b_sha256':sha(b_path),'frames_a':len(orig),'frames_b':len(read(b_path)[0]),'only_intended_change':'piano.concert_grand_natural -> piano.concert_grand_natural_unison_subtle','preserved':['score','seed','pedal timeline','S28-B strike identity semantics','S28-C hand-roll','S28-D phrase timing/gate','gain','drive','ceiling','tail']}
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2)+"\n")
(OUT/'README.md').write_text('# S28-G Exact Problem-Phrase A/B\n\nA is the byte-exact original S28-D treatment WAV the user previously evaluated. The current code first re-renders A and requires byte identity before B is allowed. B changes only the opt-in treble unison decoherence preset; 3 strings and mean detune are preserved. Held-chord windows end before key release to keep pedal-up out of the comparison.\n')
print(json.dumps(metrics,indent=2))
