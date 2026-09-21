from pathlib import Path
import json, wave
import numpy as np

from code_composer.render import render
from code_composer.presets import materialize_preset
from code_composer.audio.piano_design import resolve_piano_design
from code_composer.agent.expressive_score_plan import ExpressiveValidationContext, expressive_score_plan_from_dict
from code_composer.agent.performance_ir import compile_performance_ir
from code_composer.composition.performance import attach_performance_ir, realize_performance_ir

SR=24000
BPM=92.0
OUT=Path('/mnt/data/s28h_piano_naturalism_production_closure')
OUT.mkdir(parents=True,exist_ok=True)
PRESET='piano.concert_grand_natural_unison_subtle'

ROLL=[0,4,8,11,13,15]

# Deliberately spans low single-string, mid two-string and treble three-string registers.
CHORDS=[
    (16.0,3.35,[38,50,57,62,64,74]),
    (20.0,3.35,[34,46,53,58,62,69]),
    (24.0,3.35,[31,43,50,55,59,67]),
    (28.0,3.35,[36,48,55,60,64,72]),
    (48.0,3.35,[38,50,57,62,69,76]),
    (52.0,3.35,[34,46,53,58,65,74]),
    (56.0,3.35,[31,43,50,55,62,71]),
    (60.0,3.35,[36,48,55,60,67,76]),
]

LOW_LINE=[38,34,31,36,38,41,43,36]
TREBLE_LINE=[72,74,76,74,72,71,69,67,69,71,72,74,76,74,72,69]
RESOLVE_LINE=[64,62,60,59,57,55,53,50]


def pedal_control(start_beat, initial_down=False):
    # Clear harmony just before each barline, then repedal after the new attack.
    pts=[]
    if initial_down:
        pts.append({'offset_beats':0.0,'position':1.0})
    else:
        pts.extend([
            {'offset_beats':0.0,'position':0.0},
            {'offset_beats':0.055,'position':1.0},
        ])
    pts.extend([
        {'offset_beats':3.84,'position':1.0},
        {'offset_beats':3.93,'position':0.0},
        {'offset_beats':4.0,'position':0.0},
    ])
    return {'event_type':'piano_control','control':'sustain_pedal','start_beat':start_beat,
            'duration_beats':4.0,'points':pts}


def score_events():
    ev=[]
    # Bars 0-3: exposed low register / sparse middle response.
    for i,m in enumerate(LOW_LINE):
        st=i*2.0
        ev.append({'midi':m,'start_beat':st,'duration_beats':1.45,'velocity':.62 + .025*(i%3),
                   'section_id':'low_opening','arrangement_role':'piano'})
        if i%2==1:
            ev.append({'midi':m+12,'start_beat':st+.035,'duration_beats':.82,'velocity':.48,
                       'performance':{'piano_attack_offset_ms':5.0},
                       'section_id':'low_opening','arrangement_role':'piano'})
    for bar in range(4):
        ev.append(pedal_control(bar*4.0, initial_down=(bar==0)))

    # Bars 4-7: wide chords / hand attack / explicit repedal.
    for st,dur,midis in CHORDS[:4]:
        for i,m in enumerate(midis):
            ev.append({'midi':m,'start_beat':st,'duration_beats':dur,
                       'velocity':min(.87,.58+.038*i),
                       'performance':{'piano_attack_offset_ms':ROLL[i]},
                       'section_id':'wide_chords','arrangement_role':'piano'})
        ev.append(pedal_control(st, initial_down=False))

    # Bars 8-11: exposed treble 3-string repeated/connected phrase.
    for i,m in enumerate(TREBLE_LINE):
        ev.append({'midi':m,'start_beat':32+i*.5,'duration_beats':.31,
                   'velocity':.61 + .06*np.sin(i*np.pi/7.5),
                   'section_id':'treble_phrase','arrangement_role':'piano'})
    for bar in range(8,12):
        ev.append(pedal_control(bar*4.0, initial_down=False))

    # Bars 12-15: mixed-register closure; last bars expose both high unison and low anchor.
    for st,dur,midis in CHORDS[4:]:
        for i,m in enumerate(midis):
            ev.append({'midi':m,'start_beat':st,'duration_beats':dur,
                       'velocity':min(.86,.56+.036*i),
                       'performance':{'piano_attack_offset_ms':ROLL[i]},
                       'section_id':'resolution','arrangement_role':'piano'})
        ev.append(pedal_control(st, initial_down=False))
    for i,m in enumerate(RESOLVE_LINE):
        ev.append({'midi':m,'start_beat':60+i*.46,'duration_beats':.27,'velocity':.57,
                   'section_id':'resolution','arrangement_role':'piano'})

    return sorted(ev,key=lambda x:(x['start_beat'],0 if x.get('event_type')=='piano_control' else 1,x.get('midi',0)))


def base_ir():
    patch=resolve_piano_design(materialize_preset(PRESET,role='piano'))
    return {
        'meta':{'global_seed':282800,'sample_rate':SR,'title':'Quiet Mechanics of Light'},
        'transport':{'bpm':BPM,'beats_per_bar':4},
        'tonal':{'root':'D','scale':'minor'},
        'form':[
            {'id':'low_opening','start_bar':0,'bars':4,'energy':.34},
            {'id':'wide_chords','start_bar':4,'bars':4,'energy':.58},
            {'id':'treble_phrase','start_bar':8,'bars':4,'energy':.52},
            {'id':'resolution','start_bar':12,'bars':4,'energy':.47},
        ],
        'materials':{'motifs':{
            'treble_motif':{'intervals':[0,2,4,2,0,-1,-3,-5], 'rhythm':[.5]*8},
            'resolve_motif':{'intervals':[0,-2,-4,-5,-7,-9,-11,-14], 'rhythm':[.46]*8},
        },'progressions':{},'rhythms':{}},
        'instruments':{'piano':patch},
        'tracks':[{'id':'piano','instrument':'piano','source':{'type':'resolved'},'events':score_events(),'gain':.92}],
        # S28-F production decision: source piano has no automatic ducking.
        'mix':{'tail_seconds':1.5,'drive':1.04,'ceiling':.95},
    }


def apply_phrases(ir):
    plan={
      'version':'1.16',
      'narrative':{'arc':'exposed low register -> hand-shaped chords -> forward treble line -> relaxed mixed-register resolution'},
      'phrases':[
        {'phrase_id':'treble_forward','section_id':'treble_phrase','role':'piano','source_material':'treble_motif',
         'start_beat':32.0,'duration_beats':8.0,'dynamic_curve':[[0,.62],[.45,.73],[1,.61]],
         'timing_curve_ms':[[0,0],[.45,-7],[.72,-3],[1,5]],
         'gate_curve':[[0,.97],[.45,1.03],[.72,1.0],[1,.94]],
         'articulation_curve':[{'position':0,'articulation':'neutral'}], 'accent_points':[],
         'apex_position':.45,'breath_after_beats':0.0},
        {'phrase_id':'resolve_relax','section_id':'resolution','role':'piano','source_material':'resolve_motif',
         'start_beat':60.0,'duration_beats':3.5,'dynamic_curve':[[0,.61],[1,.49]],
         'timing_curve_ms':[[0,-2],[.45,2],[1,8]],
         'gate_curve':[[0,.99],[.5,.96],[1,.90]],
         'articulation_curve':[{'position':0,'articulation':'neutral'}], 'accent_points':[],
         'apex_position':.2,'breath_after_beats':0.0},
      ],
      'motif_statements':[],
      'register_plans':{'piano':{'hard_range':[28,96],'preferred_range':[36,84],'center':60,'max_span':60,
                                 'min_intervoice_distance':0,'overlap_policy':'allow','motion_policy':'smooth'}},
      'orchestration_sections':{
          sid:{'primary_roles':['piano'],'secondary_roles':[],'decorative_roles':[],
               'max_simultaneous_roles':1,'allowed_overlaps':[],'phrase_gap_only_roles':[],'silence_roles':[]}
          for sid in ('low_opening','wide_chords','treble_phrase','resolution')},
      'transitions':[],
    }
    ctx=ExpressiveValidationContext(
        section_ids=('low_opening','wide_chords','treble_phrase','resolution'),role_ids=('piano',),
        source_material_ids=('treble_motif','resolve_motif'),
        section_spans={'low_opening':(0,16),'wide_chords':(16,32),'treble_phrase':(32,48),'resolution':(48,64)})
    perf=compile_performance_ir(expressive_score_plan_from_dict(plan),ctx,seed=282800,realization={
        'microtiming':{'enabled':False,'max_abs_ms':0.0},
        'velocity_variation':{'enabled':False,'max_abs':0.0},
        'timing_quantization_guard_ms':0.0,'minimum_note_gap_ms':1.0})
    return realize_performance_ir(attach_performance_ir(ir,perf))


def write_excerpt(path,x,start_s,end_s):
    a=max(0,int(start_s*SR)); b=min(len(x),int(end_s*SR)); y=np.asarray(x[a:b],dtype=float)
    q=(np.clip(y,-1,1)*32767).astype(np.int16)
    with wave.open(str(path),'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes(q.tobytes())

ir=apply_phrases(base_ir())
master=OUT/'01_QUIET_MECHANICS_OF_LIGHT_S28H.wav'
audio,manifest,analysis=render(ir,master)
# Useful listening windows: wide chords, treble phrase, final mixed resolution.
write_excerpt(OUT/'02_WIDE_CHORDS_WINDOW.wav',audio,10.0,22.0)
write_excerpt(OUT/'03_TREBLE_PHRASE_WINDOW.wav',audio,20.0,33.0)
write_excerpt(OUT/'04_RESOLUTION_WINDOW.wav',audio,31.0,43.5)

notes=[e for e in score_events() if e.get('event_type')!='piano_control']
controls=[e for e in score_events() if e.get('event_type')=='piano_control']
arr=np.asarray(audio,float)
metrics={
  'sample_rate':SR,'bpm':BPM,'bars':16,'rendered_seconds':len(audio)/SR,
  'preset':PRESET,'note_events':len(notes),'piano_control_events':len(controls),
  'midi_min':min(e['midi'] for e in notes),'midi_max':max(e['midi'] for e in notes),
  'contains_low_1string_register':any(e['midi']<43 for e in notes),
  'contains_mid_2string_register':any(43<=e['midi']<=60 for e in notes),
  'contains_treble_3string_register':any(e['midi']>=61 for e in notes),
  'random_microtiming':False,'random_velocity_variation':False,
  'automatic_music_bus_ducking':False,
  'peak':float(np.max(np.abs(arr))),
  'rms':float(np.sqrt(np.mean(arr*arr)+1e-18)),
  'clipped_sample_ratio':float(np.mean(np.abs(arr)>=.9999)),
  'accepted_chain':['S28-A R2 continuous sustain pedal','S28-B deterministic per-strike identity',
                    'S28-C authored chord hand-roll','S28-D authored phrase timing/gate',
                    'S28-G subtle treble unison decoherence','S28-F no-duck source baseline'],
  'rejected':['S28-E coupled-unison sustain'],
}
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
(OUT/'README.md').write_text('''# S28-H Piano Naturalism Production Closure\n\n`Quiet Mechanics of Light` is a 16-bar / 24 kHz piano-only closure dogfood. It deliberately crosses the low 1-string, middle 2-string and treble 3-string regions and includes repeated treble notes, wide hand-rolled chords, explicit sustain-pedal up/repedal and deterministic authored phrase timing/gate.\n\nAccepted chain under test:\n- S28-A R2 continuous sustain pedal\n- S28-B deterministic per-strike identity\n- S28-C authored chord hand-roll\n- S28-D authored phrase timing/gate\n- S28-G subtle treble-unison decoherence\n- S28-F decision: no automatic music-bus ducking in the canonical source-piano baseline\n\nS28-E coupled-unison sustain is rejected and is not present.\n\nListening order: full master, wide chords, exposed treble phrase, mixed-register resolution.\n''',encoding='utf-8')
print(json.dumps(metrics,indent=2))
