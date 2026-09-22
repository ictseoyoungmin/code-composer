from __future__ import annotations

import copy
import json
import wave
from pathlib import Path

import numpy as np

from code_composer.agent.composition_brief import brief_from_dict
from code_composer.agent.composer_planner import compile_brief, apply_composer_plan, plan_to_dict
from code_composer.analysis.form_development_analysis import analyze_form_development
from code_composer.analysis.harmonic_analysis import analyze_harmony
from code_composer.audio.dsp import soft_limit
from code_composer.composition.arrange import arrange_ir
from code_composer.composition.ensemble_interaction import realize_ensemble_interaction
from code_composer.performance.violin import plan_violin_track
from code_composer.render import _render_dry_track, _timeline_size
from code_composer.validation_contracts import validate_runtime_extensions

SR=24_000
BPM=112.0
BEAT_S=60.0/BPM
TAIL_S=2.2
SEED=300922
BARS=16

SECTIONS=[
    ('intro',0,2),
    ('verse',2,5),
    ('pre',5,7),
    ('chorus',7,11),
    ('return',11,14),
    ('final',14,16),
]

DRUM_PRESET='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_foot_gesture_metal_hihat'
PIANO_PRESET='piano.concert_grand_natural_unison_subtle'
VIOLIN_PRESET='bowed.violin.modeled_realistic'
BASS_PRESET='bass.electric_finger_modeled'


def section_for_beat(beat: float) -> str:
    for sid,a,b in SECTIONS:
        if a*4 <= beat < b*4:
            return sid
    return 'final'


def _seed_ir():
    return {
        'meta':{'title':'Threadline at First Light','version':'1.17.0','sample_rate':SR,'global_seed':SEED},
        'transport':{'bpm':BPM,'beats_per_bar':4},
        'tonal':{'root':'D','scale':'natural_minor'},
        'form':[{'id':'intro','start_bar':0,'bars':2,'energy':.32}],
        'materials':{
            'motifs':{'main':{'intervals':[0,2,4,3,1,2,1,0],'rhythm':[.5]*8}},
            'progressions':{'home':{'degrees':[1,6,3,7]}},
            'rhythms':{'composer':{'steps_per_bar':16,'roles':{'kick':[0]*16,'snare':[0]*16,'hat':[0]*16},'fills':{}}},
        },
        'arrangement':{
            'motif':'main',
            'profiles':{
                'intro':{'energy':.32,'lead_density':.42,'lead_octave':4,'lead_fragment':.55,'pad_gain':.70,'bass':False,'arp':False,'register_shift':-7},
                'verse':{'energy':.56,'lead_density':.64,'lead_octave':4,'lead_fragment':.86,'pad_gain':.86,'bass':True,'arp':False,'register_shift':0},
                'pre':{'energy':.74,'lead_density':.76,'lead_octave':4,'lead_fragment':.92,'pad_gain':.96,'bass':True,'arp':False,'register_shift':2},
                'chorus':{'energy':.94,'lead_density':.88,'lead_octave':4,'lead_fragment':1.0,'pad_gain':1.03,'bass':True,'arp':False,'register_shift':5},
                'return':{'energy':.68,'lead_density':.66,'lead_octave':4,'lead_fragment':.90,'pad_gain':.90,'bass':True,'arp':False,'register_shift':0},
                'final':{'energy':1.0,'lead_density':.92,'lead_octave':4,'lead_fragment':1.0,'pad_gain':1.05,'bass':True,'arp':False,'register_shift':7},
            },
            'roles':{
                'lead':{'instrument':'lead','gain':.34,'pan':.10,'tension':.66,'cadence_strength':.88,'max_leap_semitones':7},
                'pad':{'instrument':'pad','gain':.42,'pan':-.08,'source':{'progression':'home','chord_beats':4,'octave':3,'voice_center':58,'seventh':True,'velocity':.52,'gate':.88}},
                'bass':{'instrument':'bass','gain':.45,'pan':0.0,'source':{'progression':'home','octave':2,'pattern':[0.0,1.5,2.75],'duration_beats':.58,'velocity':.70}},
                'drums':{'instrument':'drums','gain':.82,'pan':0.0},
            },
        },
        'rhythm_engine':{
            'groove':'composer','steps_per_bar':16,'swing':.0,'humanize_beats':.003,'velocity_jitter':.015,'fill_probability':.55,'bass_coupling':.70,
            'section_profiles':{},
        },
        'instruments':{
            'lead':{'kind':'generic','graph':{'oscillators':[{'waveform':'sine','gain':1.0}]}},
            'pad':{'kind':'generic','graph':{'oscillators':[{'waveform':'sine','gain':1.0}]}},
            'bass':{'kind':'generic','graph':{'oscillators':[{'waveform':'sine','gain':1.0}]}},
            'drums':{'kind':'percussion'},
        },
        'tracks':[],
        'mix':{'tail_seconds':TAIL_S,'drive':1.16,'ceiling':.94},
    }


def _groove():
    # Explicit authored 16th grid. Rendering remains deterministic; no genre inference.
    return {
        'steps_per_bar':16,
        'roles':{
            'kick':[1.0,0,0,.0, .32,0,.0,0, .90,0,.18,0, .44,0,.0,0],
            'snare':[0,0,0,0, .96,0,.14,0, 0,0,0,0, .98,0,.18,0],
            'hat':[.68,0,.52,0, .62,0,.50,0, .70,0,.54,0, .64,0,.52,0],
        },
        'fills':{
            'default':[[12,'snare',.44],[14,'snare',.58],[15,'hat',.65]],
            'final':[[10,'snare',.52],[12,'snare',.64],[14,'snare',.78],[15,'snare',.90]],
        },
    }


def _brief_dict(harmonic_treatment: bool):
    variants={
        'verse_answer':{'intervals':[0,2,4,3,1,2,3,1],'rhythm':[.5]*8,'identity_floor':.76,'identity_hard_min':.60},
        'pre_rise':{'intervals':[0,2,4,5,3,4,2,1],'rhythm':[.5]*8,'identity_floor':.64,'identity_hard_min':.55},
        'chorus_lift':{'intervals':[0,2,5,4,2,3,1,0],'rhythm':[.5]*8,'identity_floor':.75,'identity_hard_min':.62},
        'verse_return':{'intervals':[0,2,4,3,2,3,1,0],'rhythm':[.5]*8,'identity_floor':.84,'identity_hard_min':.72},
        'final_resolve':{'intervals':[0,2,4,3,2,1,1,0],'rhythm':[.5]*8,'identity_floor':.78,'identity_hard_min':.68},
    }
    sections=[
        {'id':'intro','bars':2,'energy':.32},
        {'id':'verse','bars':3,'energy':.56},
        {'id':'pre','bars':2,'energy':.74},
        {'id':'chorus','bars':4,'energy':.94},
        {'id':'return','bars':3,'energy':.68},
        {'id':'final','bars':2,'energy':1.0},
    ]
    dev={
        'intro':{'stage':'establish','lead_density_scale':.72,'rhythm_density_scale':.42,'fill_scale':.20},
        'verse':{'stage':'establish','lead_density_scale':.92,'rhythm_density_scale':.72,'fill_scale':.48},
        'pre':{'stage':'develop','lead_density_scale':1.0,'rhythm_density_scale':.90,'fill_scale':.76},
        'chorus':{'stage':'culminate','lead_density_scale':1.0,'rhythm_density_scale':1.0,'fill_scale':.92},
        'return':{'stage':'contrast','lead_density_scale':.88,'rhythm_density_scale':.78,'fill_scale':.42},
        'final':{'stage':'culminate','lead_density_scale':1.0,'rhythm_density_scale':.92,'fill_scale':1.0},
    }
    # S29 motif lineage is now the closed baseline for both A and B.
    for sid,vid in {
            'verse':'verse_answer','pre':'pre_rise','chorus':'chorus_lift','return':'verse_return','final':'final_resolve'
    }.items():
        dev[sid]['motif_variant']=vid

    progression_variants={
        'verse_ground':{'degrees':[1,6,3]},
        'pre_drive':{'degrees':[4,5]},
        'chorus_arrival':{'degrees':[6,7,3,1]},
        'return_turn':{'degrees':[4,6,5]},
        'final_cadence':{'degrees':[5,1]},
    }
    harmony_sections={
        'intro':{'colors':['triad','sus2'],'cadence_color':'sus2'},
        'verse':{'colors':['triad','add9','seventh','sus2'],'cadence_color':'add9'},
        'pre':{'colors':['add9','seventh','sus4','seventh'],'cadence_color':'seventh','passing_enabled':True,'passing_degree_offset':1,'passing_beats':.5,'passing_color':'triad','passing_velocity':.62},
        'chorus':{'colors':['add9','seventh','add9','sus4'],'cadence_color':'add9'},
        'return':{'colors':['triad','add9','seventh','triad'],'cadence_color':'triad'},
        'final':{'colors':['add9','seventh','sus4','add9'],'cadence_color':'add9'},
    }
    if harmonic_treatment:
        for sid,pid in {
            'verse':'verse_ground','pre':'pre_drive','chorus':'chorus_arrival',
            'return':'return_turn','final':'final_cadence',
        }.items():
            harmony_sections[sid]['progression_variant']=pid
    return {
        'source_prompt':'A code-only instrumental whose single violin theme clearly evolves across the whole form while piano, bass and drums remain one restrained ensemble.',
        'concept':'one recognizable theme changing function across intro, verse, pre, chorus, return and final resolution',
        'hard_constraints':{'bpm':BPM,'root':'D','scale':'natural_minor','forbidden_roles':['topline','arp']},
        'transport':{'bpm':BPM,'beats_per_bar':4},
        'tonal':{'root':'D','scale':'natural_minor'},
        'form':{'sections':sections},
        'materials':{
            'progression':[1,6,3,7,4,6,5,1],
            'motif':[0,2,4,3,1,2,1,0],
            'motif_rhythm':[.5]*8,
            'motif_variants':variants,
            **({'progression_variants':progression_variants} if harmonic_treatment else {}),
        },
        'rhythm':{
            'groove':_groove(),'swing':0.0,'humanize_beats':.003,'velocity_jitter':.015,'fill_probability':.55,'bass_coupling':.70,
            'section_profiles':{
                'intro':{'density':.34,'kick':.48,'snare':.20,'hat':.42,'fill':.15},
                'verse':{'density':.66,'kick':.76,'snare':.74,'hat':.72,'fill':.42},
                'pre':{'density':.82,'kick':.88,'snare':.84,'hat':.82,'fill':.70},
                'chorus':{'density':.96,'kick':1.0,'snare':.96,'hat':.92,'fill':.84},
                'return':{'density':.72,'kick':.78,'snare':.74,'hat':.76,'fill':.36},
                'final':{'density':.88,'kick':.92,'snare':.86,'hat':.82,'fill':1.0},
            },
        },
        'orchestration':{
            'default':{'foreground_mode':'lead'},
            'sections':{
                'intro':{'foreground_mode':'sparse','sparse_role':'lead','sparse_density_scale':.62},
                'verse':{'foreground_mode':'lead'},
                'pre':{'foreground_mode':'lead'},
                'chorus':{'foreground_mode':'lead'},
                'return':{'foreground_mode':'lead'},
                'final':{'foreground_mode':'lead'},
            },
        },
        'harmony':{
            'colors':['triad','add9','seventh','sus2'],'cadence_color':'add9','normalize_density':True,'motion_weight':1.0,'center_weight':.24,
            'sections':harmony_sections,
        },
        'development':{'families':{'theme_arc':['intro','verse','pre','chorus','return','final']},'default':{'stage':'develop'},'sections':dev},
        'transitions':{
            'pre':{'entry_gain':.78,'entry_soften_beats':.5,'pre_fill':.72},
            'chorus':{'entry_gain':.88,'entry_soften_beats':.35,'pre_fill':.92},
            'return':{'entry_gain':.82,'entry_soften_beats':.45},
            'final':{'entry_gain':.90,'entry_soften_beats':.25,'pre_fill':1.0},
        },
        'sound_palette':{'roles':{
            'lead':{'preset_id':VIOLIN_PRESET},
            'pad':{'preset_id':PIANO_PRESET},
            'bass':{'preset_id':BASS_PRESET},
            'drums':{'preset_id':DRUM_PRESET},
        }},
        'rationale':[
            'The same canonical theme is the source for every section.',
            'Treatment variants are complete agent-authored notes/rhythm, never generated by the engine.',
            'S29 thematic lineage, rhythm, form, instrument engines, seed, mix and ensemble interaction are identical in A/B.',
            'Treatment changes only explicit Composer-authored section progression variants.',
        ],
    }


def _piano_control(bar: int):
    start=bar*4.0
    return {
        'event_type':'piano_control','control':'sustain_pedal','start_beat':start,'duration_beats':4.0,
        'section_id':section_for_beat(start),
        'points':[
            {'offset_beats':0.0,'position':0.0},
            {'offset_beats':0.06,'position':1.0},
            {'offset_beats':3.80,'position':1.0},
            {'offset_beats':3.93,'position':0.0},
            {'offset_beats':4.0,'position':0.0},
        ],
    }


def _attach_violin_realization(events):
    notes=[e for e in events if 'midi' in e and e.get('event_type') not in {'piano_control','drum_control','drum'}]
    planned=plan_violin_track(notes,bpm=BPM)
    lookup={}
    for item in planned['events']:
        lookup.setdefault((float(item['start_beat']),int(item['midi'])),[]).append(item)
    out=[]
    for ev in events:
        x=copy.deepcopy(ev)
        if 'midi' in x:
            key=(float(x['start_beat']),int(x['midi']))
            item=lookup[key].pop(0)
            perf=x.setdefault('performance',{})
            vr={'left_hand':copy.deepcopy(item['left_hand']),'transition':copy.deepcopy(item['transition']),'bow':copy.deepcopy(item['bow'])}
            if 'technique' in item:
                vr['technique']=copy.deepcopy(item['technique'])
            perf['violin_realization']=vr
        out.append(x)
    return out


def _ensemble_performance_ir():
    orch={}
    scales={
        'intro':{'drums':.90,'bass':.96},
        'verse':{'pad':.96,'bass':.97},
        'pre':{'pad':.94,'bass':.96},
        'chorus':{'pad':.92,'bass':.95},
        'return':{'pad':.95,'bass':.97},
        'final':{'pad':.93,'bass':.96},
    }
    for sid,_,_ in SECTIONS:
        orch[sid]={
            'primary_roles':['lead'],'secondary_roles':['pad','bass'],'decorative_roles':['drums'],
            'max_simultaneous_roles':4,'allowed_overlaps':[['lead','pad'],['lead','bass']],
            'phrase_gap_only_roles':[],'silence_roles':[],
            'ensemble_interaction':{
                'enabled':True,
                'leader_role':'drums',
                'timing_offsets_ms':{'lead':2.0,'pad':5.0,'bass':9.0,'drums':0.0},
                'overlap_velocity_scales':{},
                'role_velocity_scales':scales[sid],
                'targeted_onset_yields':[{
                    'leader_role':'drums','leader_event_selector':{'event_type':'drum','drums':['kick']},
                    'window_ms':72.0,'support_velocity_scales':{'pad':.87,'bass':.91},
                }],
            },
        }
    return {
        'version':'1.16','phrases':[],'motif_statements':[],
        'register_plans':{
            'lead':{'hard_range':[55,96],'preferred_range':[60,88],'center':72,'max_span':24,'min_intervoice_distance':0,'overlap_policy':'allow','motion_policy':'free'},
            'pad':{'hard_range':[21,108],'preferred_range':[36,88],'center':60,'max_span':60,'min_intervoice_distance':0,'overlap_policy':'allow','motion_policy':'free'},
            'bass':{'hard_range':[28,64],'preferred_range':[32,55],'center':43,'max_span':24,'min_intervoice_distance':0,'overlap_policy':'allow','motion_policy':'free'},
            'drums':{'hard_range':[0,127],'preferred_range':[0,127],'center':60,'max_span':127,'min_intervoice_distance':0,'overlap_policy':'allow','motion_policy':'free'},
        },
        'orchestration_sections':orch,'transitions':[],
        'realization':{
            'seed':SEED,'microtiming':{'enabled':False,'max_abs_ms':0.0},
            'velocity_variation':{'enabled':False,'max_abs':0.0},
            'timing_quantization_guard_ms':0.0,'minimum_note_gap_ms':0.0,
            'ensemble':{'enabled':True,'role_pan_offsets':{'lead':.02,'pad':-.02,'bass':0.0,'drums':0.0}},
        },
    }


def build_ir(harmonic_treatment: bool):
    seed=_seed_ir()
    brief=brief_from_dict(_brief_dict(harmonic_treatment))
    plan=compile_brief(seed,brief)
    ir=apply_composer_plan(seed,plan)
    ir['meta']['title']='Threadline at First Light — S30 Harmonic Narrative' if harmonic_treatment else 'Threadline at First Light — S29 Closed Baseline'
    ir['mix']={'tail_seconds':TAIL_S,'drive':1.16,'ceiling':.94}
    ir=arrange_ir(ir)
    pad=next(t for t in ir['tracks'] if t['id']=='pad')
    pad['events'].extend(_piano_control(bar) for bar in range(BARS))
    pad['events']=sorted(pad['events'],key=lambda e:(float(e.get('start_beat',0.0)),0 if e.get('event_type')=='piano_control' else 1,int(e.get('midi',0))))
    lead=next(t for t in ir['tracks'] if t['id']=='lead')
    lead['events']=_attach_violin_realization(lead['events'])
    ir['performance_ir']=_ensemble_performance_ir()
    ir=realize_ensemble_interaction(ir)
    validate_runtime_extensions(ir)
    ir['s29_plan']=plan_to_dict(plan)
    return ir


def _event_core(event):
    return {k:event.get(k) for k in ('event_type','drum','control','start_beat','duration_beats','midi','velocity','section_id','arrangement_role','points') if k in event}


def assert_controlled_ab(a,b):
    # S30 isolates harmonic degree/progression routing. Lead/drums must be exact.
    for tid in ('lead','drums'):
        ta=next(t for t in a['tracks'] if t['id']==tid)
        tb=next(t for t in b['tracks'] if t['id']==tid)
        if [_event_core(e) for e in ta['events']] != [_event_core(e) for e in tb['events']]:
            raise RuntimeError(f'{tid} changed outside S30 harmonic surface')
    # Piano/bass rhythm and dynamics remain fixed; only pitched harmonic content/lineage may differ.
    for tid in ('pad','bass'):
        ta=next(t for t in a['tracks'] if t['id']==tid)['events']
        tb=next(t for t in b['tracks'] if t['id']==tid)['events']
        if len(ta)!=len(tb):
            raise RuntimeError(f'{tid} event count changed')
        for x,y in zip(ta,tb):
            core=lambda e:(e.get('event_type'),e.get('control'),e.get('start_beat'),e.get('duration_beats'),e.get('velocity'),e.get('section_id'),e.get('points'))
            if core(x)!=core(y):
                raise RuntimeError(f'{tid} timing/duration/velocity/control changed outside S30 harmonic surface')


def rms(y):
    a=np.asarray(y,dtype=np.float64)
    return float(np.sqrt(np.mean(a*a)+1e-18))


def write_wav(path,y):
    pcm=(np.clip(y,-1,1)*32767).astype(np.int16)
    with wave.open(str(path),'wb') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(pcm.tobytes())


def _render_lead_sectionwise(ir, n):
    """Render the long modeled-violin preview with bounded section state.

    The production waveguide can enter a very slow denormal-heavy path after a long
    sequence of persistent string/body state. S29 does not own that renderer. For
    this listening artifact only, each authored form section is rendered with an
    independent violin state and its natural release tail is summed into the next
    section. A and B use the exact same preview policy, so the perceptual comparison
    remains isolated to explicit motif pitch lineage.
    """
    lead=next(t for t in ir['tracks'] if t['id']=='lead')
    out=np.zeros((int(n),2),dtype=np.float64)
    for sid,_,_ in SECTIONS:
        part=copy.deepcopy(lead)
        part['events']=[copy.deepcopy(e) for e in lead['events'] if e.get('section_id')==sid]
        if not part['events']:
            continue
        y=_render_dry_track(ir,part,n,SR,BEAT_S,graph_mode=False)
        out[:len(y)] += y
    peak=float(np.max(np.abs(out))) if len(out) else 0.0
    if peak > 1.0:
        out /= peak
    return out


def render_track(kind: str, out_path: str):
    a=build_ir(False); b=build_ir(True); assert_controlled_ab(a,b)
    variant=b if kind.endswith('_b') else a
    tid=kind[:-2] if kind.endswith('_a') or kind.endswith('_b') else kind
    n=_timeline_size(variant,SR,BEAT_S)
    tr=next(t for t in variant['tracks'] if t['id']==tid)
    y=_render_lead_sectionwise(variant,n) if tid=='lead' else _render_dry_track(variant,tr,n,SR,BEAT_S,graph_mode=False)
    np.save(out_path,y)
    print(json.dumps({'kind':kind,'track':tid,'samples':len(y),'rms':rms(y),'sectionwise_violin_preview':tid=='lead'}), flush=True)
    # The renderer may leave numerical worker threads alive in this container.
    # Track mode is an isolated subprocess, so exit immediately after the durable NPY is flushed.
    import os
    os._exit(0)


def finalize(out_dir: str, parts_dir: str):
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True); parts=Path(parts_dir)
    a=build_ir(False); b=build_ir(True); assert_controlled_ab(a,b)
    lead=np.load(parts/'lead.npy'); drums=np.load(parts/'drums.npy')
    support_a=np.load(parts/'pad_a.npy')+np.load(parts/'bass_a.npy')+drums
    support_b=np.load(parts/'pad_b.npy')+np.load(parts/'bass_b.npy')+drums
    mix_a=soft_limit(support_a+lead,drive=1.16,ceiling=.94)
    mix_b=soft_limit(support_b+lead,drive=1.16,ceiling=.94)
    write_wav(out/'01_S29_CLOSED_BASELINE_FULL.wav',mix_a)
    write_wav(out/'02_S30_HARMONIC_NARRATIVE_FULL.wav',mix_b)
    gap=np.zeros((int(.8*SR),2),dtype=np.float64)
    write_wav(out/'03_A_then_B_FULL.wav',np.concatenate([mix_a,gap,mix_b],axis=0))
    start=int(5*4*BEAT_S*SR); end=int(16*4*BEAT_S*SR)
    write_wav(out/'04_PRE_THROUGH_FINAL_A_then_B.wav',np.concatenate([mix_a[start:end],gap,mix_b[start:end]],axis=0))
    write_wav(out/'05_A_then_B_PIANO_STEM.wav',np.concatenate([np.load(parts/'pad_a.npy'),gap,np.load(parts/'pad_b.npy')],axis=0))
    write_wav(out/'06_A_then_B_BASS_STEM.wav',np.concatenate([np.load(parts/'bass_a.npy'),gap,np.load(parts/'bass_b.npy')],axis=0))
    match_gain=rms(mix_a)/max(rms(mix_b),1e-12)
    mix_b_matched=mix_b*match_gain
    write_wav(out/'07_A_then_B_FULL_RMS_MATCHED.wav',np.concatenate([mix_a,gap,mix_b_matched],axis=0))
    write_wav(out/'08_PRE_THROUGH_FINAL_A_then_B_RMS_MATCHED.wav',np.concatenate([mix_a[start:end],gap,mix_b_matched[start:end]],axis=0))

    thematic_report=analyze_form_development(b)
    harmonic_report=analyze_harmony(b)
    pad_a_events=next(t for t in a['tracks'] if t['id']=='pad')['events']
    pad_b_events=next(t for t in b['tracks'] if t['id']=='pad')['events']
    bass_a_events=next(t for t in a['tracks'] if t['id']=='bass')['events']
    bass_b_events=next(t for t in b['tracks'] if t['id']=='bass')['events']
    pad_pitch_changes=sum(int(x.get('midi')!=y.get('midi')) for x,y in zip(pad_a_events,pad_b_events) if 'midi' in x and 'midi' in y)
    bass_pitch_changes=sum(int(x.get('midi')!=y.get('midi')) for x,y in zip(bass_a_events,bass_b_events))
    metrics={
        'title':'Threadline at First Light','sample_rate':SR,'bpm':BPM,'bars':BARS,
        'rendered_seconds':len(mix_b)/SR,
        'a_rms':rms(mix_a),'b_rms':rms(mix_b),
        'a_peak':float(np.max(np.abs(mix_a))),'b_peak':float(np.max(np.abs(mix_b))),
        'b_clipped_sample_ratio':float(np.mean(np.abs(mix_b)>=1.0)),
        'rms_match_gain':match_gain,'rms_match_gain_db':20.0*np.log10(max(match_gain,1e-12)),
        'lead_event_identity':True,'drum_event_identity':True,
        'pad_event_count':len(pad_b_events),'bass_event_count':len(bass_b_events),
        'pad_pitch_changes_vs_baseline':pad_pitch_changes,'bass_pitch_changes_vs_baseline':bass_pitch_changes,
        'pad_bass_timing_duration_velocity_identity':True,
        'automatic_music_bus_ducking':False,
        'violin_preview_section_state_reset':True,
        's29_thematic_report':thematic_report,
        's30_harmonic_report':harmonic_report,
    }
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    (out/'control_ir.json').write_text(json.dumps(a,indent=2),encoding='utf-8')
    (out/'treatment_ir.json').write_text(json.dumps(b,indent=2),encoding='utf-8')
    (out/'README.md').write_text('''# S30 Harmonic Narrative — Threadline at First Light\n\nA/B use the CLOSED S29 thematic lineage and hold form, rhythm, instruments, seed, mix, lead, drums, and ensemble interaction fixed. B changes only explicit Composer-authored section progression variants routed consistently to piano and bass. The long modeled-violin listening preview resets physical violin state at authored section boundaries to avoid a known long-run renderer slowdown; natural release tails overlap across boundaries and the identical preview policy is used for A/B.\n\nListen first to `07_A_then_B_FULL_RMS_MATCHED.wav`, then `08_PRE_THROUGH_FINAL_A_then_B_RMS_MATCHED.wav`. Raw-level files `03`/`04` are retained as render evidence. The gate is whether B creates clearer harmonic departure, tension, arrival and final resolution across the same thematic form without making the song sound over-composed or changing the lead/drum performance.\n''',encoding='utf-8')
    print(json.dumps({k:metrics[k] for k in ('rendered_seconds','a_rms','b_rms','a_peak','b_peak','b_clipped_sample_ratio','pad_pitch_changes_vs_baseline','bass_pitch_changes_vs_baseline')},indent=2))
    print(json.dumps(harmonic_report,indent=2))


if __name__=='__main__':
    import sys
    if len(sys.argv)==4 and sys.argv[1]=='track':
        render_track(sys.argv[2],sys.argv[3])
    elif len(sys.argv)==4 and sys.argv[1]=='finalize':
        finalize(sys.argv[2],sys.argv[3])
    else:
        raise SystemExit('usage: track <lead|pad_a|pad_b|bass_a|bass_b|drums> <npy> | finalize <outdir> <partsdir>')
