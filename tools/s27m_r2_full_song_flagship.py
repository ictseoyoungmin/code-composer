from __future__ import annotations
import copy, json, wave
from pathlib import Path
import numpy as np

import s27l_full_song_drum_chain as base
from code_composer.audio.dsp import soft_limit
from code_composer.composition.ensemble_interaction import realize_ensemble_interaction
from code_composer.presets import materialize_preset
from code_composer.render import _render_dry_track, _timeline_size

SR=base.SR; BPM=base.BPM; BEAT_S=base.BEAT_S; TAIL_S=base.TAIL_S
PIANO_PRESET='piano.concert_grand_natural_unison_subtle'

SECTIONS=[('intro',0,8),('verse',8,20),('pre',20,28),('chorus',28,44),('outro',44,48)]

def section_for_beat(beat: float) -> str:
    for sid,a,b in SECTIONS:
        if a <= beat < b:
            return sid
    return 'outro'

def piano_control(bar: int):
    start=bar*4.0
    return {
        'event_type':'piano_control','control':'sustain_pedal','start_beat':start,
        'duration_beats':4.0,'section_id':section_for_beat(start),
        'points':[
            {'offset_beats':0.0,'position':0.0},
            {'offset_beats':0.06,'position':1.0},
            {'offset_beats':3.82,'position':1.0},
            {'offset_beats':3.93,'position':0.0},
            {'offset_beats':4.0,'position':0.0},
        ]
    }

def interaction_for(section: str, treatment: bool):
    leader='piano' if section in {'intro','outro'} else 'violin'
    timing={'piano':5.0,'bass':9.0,'drums':-2.0,'violin':0.0}
    overlap={'piano':.94,'bass':.95} if leader=='violin' else {'bass':.96,'violin':.96}
    x={'enabled':True,'leader_role':leader,'timing_offsets_ms':timing,'overlap_velocity_scales':overlap}
    if treatment:
        role_scales={
            'intro':{'drums':.92,'bass':.96},
            'verse':{'piano':.95,'bass':.97},
            'pre':{'piano':.93,'bass':.96},
            'chorus':{'piano':.91,'bass':.95},
            'outro':{'bass':.96,'drums':.94},
        }[section]
        x['role_velocity_scales']=role_scales
        x['targeted_onset_yields']=[{
            'leader_role':'drums',
            'leader_event_selector':{'event_type':'drum','drums':['kick']},
            'window_ms':72.0,
            'support_velocity_scales':{'piano':.86,'bass':.90},
        }]
    return x

def performance_ir(treatment: bool):
    orch={}
    for sid,_,_ in SECTIONS:
        orch[sid]={
            'primary_roles':['piano'] if sid in {'intro','outro'} else ['violin'],
            'secondary_roles':['violin','bass'] if sid in {'intro','outro'} else ['piano','bass'],
            'decorative_roles':['drums'],
            'max_simultaneous_roles':4,
            'allowed_overlaps':[['violin','piano'],['violin','bass']],
            'phrase_gap_only_roles':[], 'silence_roles':[],
            'ensemble_interaction':interaction_for(sid,treatment),
        }
    return {
        'version':'1.16','phrases':[],'motif_statements':[],
        'register_plans':{
            'violin':{'hard_range':[55,96],'preferred_range':[60,88],'center':72,'max_span':24,'min_intervoice_distance':0,'overlap_policy':'allow','motion_policy':'free'},
            'piano':{'hard_range':[21,108],'preferred_range':[36,88],'center':60,'max_span':60,'min_intervoice_distance':0,'overlap_policy':'allow','motion_policy':'free'},
            'bass':{'hard_range':[28,64],'preferred_range':[32,55],'center':43,'max_span':24,'min_intervoice_distance':0,'overlap_policy':'allow','motion_policy':'free'},
            'drums':{'hard_range':[0,127],'preferred_range':[0,127],'center':60,'max_span':127,'min_intervoice_distance':0,'overlap_policy':'allow','motion_policy':'free'},
        },
        'orchestration_sections':orch,'transitions':[],
        'realization':{
            'seed':2712026,
            'microtiming':{'enabled':False,'max_abs_ms':0.0},
            'velocity_variation':{'enabled':False,'max_abs':0.0},
            'timing_quantization_guard_ms':0.0,'minimum_note_gap_ms':0.0,
            'ensemble':{'enabled':True,'role_pan_offsets':{'piano':-.02,'violin':.02,'bass':0.0,'drums':0.0}},
        }
    }

def build_ir(treatment: bool):
    ir=base.build_ir()
    ir['meta']['title']='Crossing Meridian — S27-M R2 Flagship' if treatment else 'Crossing Meridian — S15 Baseline'
    ir['instruments']['piano']=materialize_preset(PIANO_PRESET,role='piano')
    for tr in ir['tracks']:
        tr['arrangement_role']=tr['id']
        for ev in tr['events']:
            ev.setdefault('section_id',section_for_beat(float(ev.get('start_beat',0.0))))
    piano=next(t for t in ir['tracks'] if t['id']=='piano')
    piano['events'].extend(piano_control(bar) for bar in range(12))
    piano['events']=sorted(piano['events'],key=lambda e:(float(e.get('start_beat',0.0)),0 if e.get('event_type')=='piano_control' else 1,e.get('midi',0)))
    ir['performance_ir']=performance_ir(treatment)
    return realize_ensemble_interaction(ir)

def write_wav(path,y):
    pcm=(np.clip(y,-1,1)*32767).astype(np.int16)
    with wave.open(str(path),'wb') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(pcm.tobytes())

def rms(y):
    a=np.asarray(y,dtype=np.float64); return float(np.sqrt(np.mean(a*a)+1e-18))

def render_track(variant,track_id,out_path):
    treatment=variant=='b'
    ir=build_ir(treatment)
    n=_timeline_size(ir,SR,BEAT_S)
    tr=next(t for t in ir['tracks'] if t['id']==track_id)
    y=_render_dry_track(ir,tr,n,SR,BEAT_S,graph_mode=False)
    np.save(out_path,y)
    print(json.dumps({'variant':variant,'track':track_id,'samples':len(y),'rms':rms(y)}))

def finalize(out_dir,parts_dir):
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True); parts=Path(parts_dir)
    mixes={}; stems={}
    for variant in ('a','b'):
        ss={k:np.load(parts/f'{variant}_{k}.npy') for k in ('piano','bass','violin','drums')}
        raw=sum(ss.values()); master=soft_limit(raw,drive=1.18,ceiling=.94)
        mixes[variant]=master; stems[variant]=ss
    write_wav(out/'01_S15_BASELINE_FULL.wav',mixes['a'])
    write_wav(out/'02_S27M_R2_TREATMENT_FULL.wav',mixes['b'])
    gap=np.zeros((int(.8*SR),2),dtype=np.float64)
    ab=np.concatenate([mixes['a'],gap,mixes['b']],axis=0)
    write_wav(out/'03_A_then_B_FULL.wav',ab)
    ca=int(7*4*BEAT_S*SR); cb=int(11*4*BEAT_S*SR)
    chorus=np.concatenate([mixes['a'][ca:cb],gap,mixes['b'][ca:cb]],axis=0)
    write_wav(out/'04_A_then_B_CHORUS.wav',chorus)
    for k,y in stems['b'].items(): write_wav(out/f'05_B_{k.upper()}_STEM.wav',y)
    ir_a=build_ir(False); ir_b=build_ir(True)
    report=ir_b.get('ensemble_interaction_report',{})
    metrics={
        'sample_rate':SR,'bpm':BPM,'bars':12,
        'rendered_seconds':len(mixes['b'])/SR,
        'piano_preset':PIANO_PRESET,
        'a_rms':rms(mixes['a']),'b_rms':rms(mixes['b']),
        'a_peak':float(np.max(np.abs(mixes['a']))),'b_peak':float(np.max(np.abs(mixes['b']))),
        'b_clipped_sample_ratio':float(np.mean(np.abs(mixes['b'])>=1.0)),
        'track_event_counts':{t['id']:len(t['events']) for t in ir_b['tracks']},
        'treatment_report':report,
        'automatic_music_bus_ducking':False,
        'same_score_seed_instruments_mix_except_ensemble_interaction':True,
    }
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    (out/'treatment_ir.json').write_text(json.dumps(ir_b,indent=2),encoding='utf-8')
    (out/'README.md').write_text('''# Crossing Meridian — S27-M R2 Full-Song Flagship\n\n12 bars / 24 kHz / 112 BPM. A and B use the same score, accepted S28-H/S28-G piano preset, modeled bass, articulated violin, locked S27 drum chain, seed and mix. Both use the same S15 timing/pan interaction. B adds only section `role_velocity_scales` and kick-selected `targeted_onset_yields`.\n\nNo music-bus sidechain ducking is used. Targeted onset yield changes only support attacks inside the authored 72 ms kick window; already-ringing sustain and `*_control` events are untouched.\n\nListen first to `03_A_then_B_FULL.wav`, then `04_A_then_B_CHORUS.wav`.\n''',encoding='utf-8')
    print(json.dumps({k:metrics[k] for k in ('rendered_seconds','a_rms','b_rms','a_peak','b_peak','b_clipped_sample_ratio','track_event_counts')},indent=2))

if __name__=='__main__':
    import sys
    if len(sys.argv)==5 and sys.argv[1]=='track': render_track(sys.argv[2],sys.argv[3],sys.argv[4])
    elif len(sys.argv)==4 and sys.argv[1]=='finalize': finalize(sys.argv[2],sys.argv[3])
    else: raise SystemExit('usage: track <a|b> <track> <npy> | finalize <outdir> <partsdir>')
