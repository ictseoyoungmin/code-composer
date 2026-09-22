from __future__ import annotations

import copy
import json
import sys
import wave
from pathlib import Path

import numpy as np

# Reuse the accepted S30 flagship authoring surface without copying its music data
# into the runtime library. This tool is dogfood only.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s30_harmonic_narrative_flagship as s30

from code_composer.composition.musical_transitions import realize_musical_transitions
from code_composer.composition.ensemble_interaction import realize_ensemble_interaction
from code_composer.validation_contracts import validate_runtime_extensions
from code_composer.render import _render_dry_track, _timeline_size
from code_composer.audio.dsp import soft_limit

SR=s30.SR
BPM=s30.BPM
BEAT_S=s30.BEAT_S
TAIL_S=s30.TAIL_S
BARS=s30.BARS
SECTIONS=s30.SECTIONS


def _arrival_transition(from_section: str, to_section: str, beats: float, velocity: float, index: int = 0):
    return {
        'from_section':from_section,
        'to_section':to_section,
        'harmonic_anticipation':{
            'enabled':True,
            'role':'pad',
            'beats':float(beats),
            'arrival_binding':{
                'source':'destination_progression',
                'progression_index':int(index),
            },
            'chord_intervals':[0,2,4],
            'velocity':float(velocity),
            'gate':0.82,
        },
        'pickup':{'enabled':False},
        'bass_approach':{'type':'none'},
        'cadence_extension':{},
        'texture_subtraction':{},
        'silence_beats':0.0,
        'register_preparation':{},
        'rhythm_fill':{},
    }


def _s31_transitions():
    return [
        _arrival_transition('intro','verse',0.40,0.22),
        _arrival_transition('verse','pre',0.50,0.27),
        _arrival_transition('pre','chorus',0.65,0.31),
        _arrival_transition('chorus','return',0.45,0.24),
        _arrival_transition('return','final',0.70,0.33),
    ]


def build_ir(bound_transitions: bool):
    seed=s30._seed_ir()
    brief=s30.brief_from_dict(s30._brief_dict(True))  # S30 closed harmonic narrative
    plan=s30.compile_brief(seed,brief)
    ir=s30.apply_composer_plan(seed,plan)
    ir['meta']['title']='Threadline at First Light — S31 Destination-Bound Transitions' if bound_transitions else 'Threadline at First Light — S30 Closed Baseline'
    ir['mix']={'tail_seconds':TAIL_S,'drive':1.16,'ceiling':.94}
    ir=s30.arrange_ir(ir)

    pad=next(t for t in ir['tracks'] if t['id']=='pad')
    pad['events'].extend(s30._piano_control(bar) for bar in range(BARS))
    pad['events']=sorted(
        pad['events'],
        key=lambda e:(float(e.get('start_beat',0.0)),0 if e.get('event_type')=='piano_control' else 1,int(e.get('midi',0)))
    )
    lead=next(t for t in ir['tracks'] if t['id']=='lead')
    lead['events']=s30._attach_violin_realization(lead['events'])

    ir['performance_ir']=s30._ensemble_performance_ir()
    ir['performance_ir']['transitions']=_s31_transitions() if bound_transitions else []
    ir=realize_musical_transitions(ir)
    ir=realize_ensemble_interaction(ir)
    validate_runtime_extensions(ir)
    ir['s30_plan']=s30.plan_to_dict(plan)
    return ir


def _event_core(event):
    return {k:event.get(k) for k in (
        'event_type','drum','control','start_beat','duration_beats','midi','velocity',
        'section_id','arrangement_role','points','harmonic_degree','harmonic_progression_id',
    ) if k in event}


def assert_controlled_ab(a,b):
    for tid in ('lead','bass','drums'):
        ta=next(t for t in a['tracks'] if t['id']==tid)
        tb=next(t for t in b['tracks'] if t['id']==tid)
        if [_event_core(e) for e in ta['events']] != [_event_core(e) for e in tb['events']]:
            raise RuntimeError(f'{tid} changed outside S31 transition surface')

    pa=next(t for t in a['tracks'] if t['id']=='pad')['events']
    pb=next(t for t in b['tracks'] if t['id']=='pad')['events']
    pb_base=[e for e in pb if e.get('transition_material')!='harmonic_anticipation']
    if [_event_core(e) for e in pa] != [_event_core(e) for e in pb_base]:
        raise RuntimeError('existing pad events changed outside S31 transition surface')
    bound=[e for e in pb if e.get('transition_material')=='harmonic_anticipation']
    if len(bound)!=15:
        raise RuntimeError(f'expected 15 S31 anticipation notes, got {len(bound)}')


def rms(y):
    a=np.asarray(y,dtype=np.float64)
    return float(np.sqrt(np.mean(a*a)+1e-18))


def write_wav(path,y):
    pcm=(np.clip(y,-1,1)*32767).astype(np.int16)
    with wave.open(str(path),'wb') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(pcm.tobytes())


def render_track(kind: str, out_path: str):
    a=build_ir(False); b=build_ir(True); assert_controlled_ab(a,b)
    variant=b if kind.endswith('_b') else a
    tid=kind[:-2] if kind.endswith('_a') or kind.endswith('_b') else kind
    n=_timeline_size(variant,SR,BEAT_S)
    tr=next(t for t in variant['tracks'] if t['id']==tid)
    y=s30._render_lead_sectionwise(variant,n) if tid=='lead' else _render_dry_track(variant,tr,n,SR,BEAT_S,graph_mode=False)
    np.save(out_path,y)
    print(json.dumps({'kind':kind,'track':tid,'samples':len(y),'rms':rms(y)},indent=2),flush=True)
    import os
    os._exit(0)


def finalize(out_dir: str, parts_dir: str):
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True); parts=Path(parts_dir)
    a=build_ir(False); b=build_ir(True); assert_controlled_ab(a,b)
    lead=np.load(parts/'lead.npy'); bass=np.load(parts/'bass.npy'); drums=np.load(parts/'drums.npy')
    pad_a=np.load(parts/'pad_a.npy'); pad_b=np.load(parts/'pad_b.npy')
    mix_a=soft_limit(lead+bass+drums+pad_a,drive=1.16,ceiling=.94)
    mix_b=soft_limit(lead+bass+drums+pad_b,drive=1.16,ceiling=.94)

    gap=np.zeros((int(.8*SR),2),dtype=np.float64)
    write_wav(out/'01_S30_CLOSED_BASELINE_FULL.wav',mix_a)
    write_wav(out/'02_S31_DESTINATION_BOUND_TRANSITIONS_FULL.wav',mix_b)
    write_wav(out/'03_A_then_B_FULL.wav',np.concatenate([mix_a,gap,mix_b],axis=0))
    start=int(4*4*BEAT_S*SR); end=int(16*4*BEAT_S*SR)
    write_wav(out/'04_VERSE_TO_FINAL_A_then_B.wav',np.concatenate([mix_a[start:end],gap,mix_b[start:end]],axis=0))
    write_wav(out/'05_A_then_B_PIANO_STEM.wav',np.concatenate([pad_a,gap,pad_b],axis=0))

    match_gain=rms(mix_a)/max(rms(mix_b),1e-12)
    mix_b_matched=mix_b*match_gain
    pad_b_matched=pad_b*match_gain
    write_wav(out/'06_A_then_B_FULL_RMS_MATCHED.wav',np.concatenate([mix_a,gap,mix_b_matched],axis=0))
    write_wav(out/'07_VERSE_TO_FINAL_A_then_B_RMS_MATCHED.wav',np.concatenate([mix_a[start:end],gap,mix_b_matched[start:end]],axis=0))
    write_wav(out/'08_A_then_B_PIANO_STEM_RMS_MATCHED.wav',np.concatenate([pad_a,gap,pad_b_matched],axis=0))

    rep=b['musical_transition_report']['transitions']
    bindings=[r['harmonic_arrival_binding'] for r in rep]
    metrics={
        'title':'Threadline at First Light',
        'sample_rate':SR,'bpm':BPM,'bars':BARS,'rendered_seconds':len(mix_b)/SR,
        'a_rms':rms(mix_a),'b_rms':rms(mix_b),
        'a_peak':float(np.max(np.abs(mix_a))),'b_peak':float(np.max(np.abs(mix_b))),
        'b_clipped_sample_ratio':float(np.mean(np.abs(mix_b)>=1.0)),
        'rms_match_gain':match_gain,'rms_match_gain_db':20*np.log10(max(match_gain,1e-12)),
        'lead_bass_drums_identity':True,
        'existing_pad_event_identity':True,
        's31_added_harmonic_anticipation_notes':sum(r['harmonic_anticipation_events'] for r in rep),
        's31_arrival_bindings':bindings,
        'automatic_music_bus_ducking':False,
        'violin_preview_section_state_reset':True,
    }
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    (out/'control_ir.json').write_text(json.dumps(a,indent=2),encoding='utf-8')
    (out/'treatment_ir.json').write_text(json.dumps(b,indent=2),encoding='utf-8')
    (out/'README.md').write_text('''# S31 Destination-Bound Transition — Threadline at First Light\n\nA is the CLOSED S30 harmonic-narrative baseline. B preserves S29 thematic lineage and S30 section progressions, then adds only five explicitly authored E5 harmonic-anticipation gestures. Each gesture points to `destination_progression` plus an explicit `progression_index=0`; the runtime validates and resolves that pointer instead of duplicating a scale degree.\n\nListen first to `06_A_then_B_FULL_RMS_MATCHED.wav`, then `07_VERSE_TO_FINAL_A_then_B_RMS_MATCHED.wav`, then the piano-only `08_A_then_B_PIANO_STEM_RMS_MATCHED.wav`. The gate is whether B makes section boundaries feel intentionally prepared and causally connected to the destination harmony without sounding like extra chords pasted on top.\n''',encoding='utf-8')
    print(json.dumps(metrics,indent=2))


if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='track':
        render_track(sys.argv[2],sys.argv[3])
    elif len(sys.argv)==4 and sys.argv[1]=='finalize':
        finalize(sys.argv[2],sys.argv[3])
    else:
        raise SystemExit('usage: track <lead|bass|drums|pad_a|pad_b> <npy> | finalize <outdir> <partsdir>')
