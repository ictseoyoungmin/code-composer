from __future__ import annotations
import copy, json, wave
from pathlib import Path
import numpy as np

from code_composer.analysis.drummer_performance_analysis import analyze_drummer_performance
from code_composer.audio.dsp import soft_limit
from code_composer.performance.violin import plan_violin_track
from code_composer.presets import materialize_preset
from code_composer.render import _render_dry_track, _timeline_size

SR=24_000; BPM=112.0; BEAT_S=60.0/BPM; BARS=12; SEED=2712026; TAIL_S=2.2
DRUM_PRESET='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_foot_gesture_metal_hihat'

HARM=['Dm','Bb','F','C','Dm','Gm','Bb','A','Dm','Bb','F','A']
VOICINGS={
'Dm':[50,57,62,65],'Bb':[46,53,58,62],'F':[48,53,57,60],'C':[48,55,60,64],
'Gm':[43,50,55,58],'A':[45,52,57,61]}
ROOTS={'Dm':38,'Bb':34,'F':41,'C':36,'Gm':43,'A':45}

def note(start,dur,midi,vel,perf=None):
    x={'start_beat':float(start),'duration_beats':float(dur),'midi':int(midi),'velocity':float(vel)}
    if perf: x['performance']=copy.deepcopy(perf)
    return x

def de(kind,beat,vel=.8,dur=.1,section=''):
    return {'event_type':'drum','drum':kind,'start_beat':float(beat),'duration_beats':float(dur),'velocity':float(vel),'section_id':section}

def ctrl(start,points,dur,section=''):
    return {'event_type':'drum_control','control':'hi_hat_pedal_openness','start_beat':float(start),'duration_beats':float(dur),
            'points':[{'offset_beats':float(a),'openness':float(b)} for a,b in points],'section_id':section}

def piano_events():
    out=[]; j=[0,-.009,.005,-.004]
    for bar,h in enumerate(HARM):
        b=bar*4.; c=VOICINGS[h]
        if bar<2:
            seq=[0,2,1,3,1,2,0,2]
            for i,k in enumerate(seq): out.append(note(b+i*.5+j[i%4],.42,c[k]+(12 if k==3 else 0),.47+.03*(i%2)))
        elif bar<5:
            for off,v in [(0,.58),(1.5,.49),(2.75,.53)]:
                for n,m in enumerate(c[1:]): out.append(note(b+off+j[n],.65 if off else .85,m+(12 if n==2 else 0),v-n*.02))
        elif bar<7:
            for n,m in enumerate(c): out.append(note(b+j[n],1.7,m+(12 if n>=2 else 0),.56+n*.015))
            for m in c[1:]: out.append(note(b+2.5,1.1,m+12,.47))
        elif bar<11:
            for off,v,d in [(0,.66,1.1),(2,.61,1.0),(3.5,.45,.4)]:
                for n,m in enumerate(c): out.append(note(b+off+j[n],d,m+(12 if n>=2 else 0),v-n*.02))
        else:
            for n,m in enumerate(c): out.append(note(b+j[n],3.4,m+(12 if n>=2 else 0),.44-n*.015))
    return out

def bass_events():
    out=[]
    for bar,h in enumerate(HARM):
        if bar==0: continue
        b=bar*4.; r=ROOTS[h]; fifth=r+7; octv=r+12; nxt=ROOTS[HARM[min(bar+1,BARS-1)]]
        if bar<5: patt=[(0,r,.72,.9),(1.5,fifth,.56,.55),(2.5,octv,.63,.7),(3.5,nxt,.49,.35)]
        elif bar<7: patt=[(0,r,.76,.9),(1,octv,.61,.5),(2,fifth,.67,.7),(3,nxt,.60,.5)]
        elif bar<11: patt=[(0,r,.81,.8),(.75,fifth,.60,.4),(1.5,octv,.72,.62),(2.5,fifth,.65,.52),(3.5,nxt,.60,.35)]
        else: patt=[(0,r,.64,1.8),(2.5,fifth,.47,.85)]
        for off,m,v,d in patt: out.append(note(b+off,d,m,v))
    return out

def violin_raw():
    out=[]
    # intro pizzicato call
    for off,m,v in [(0,62,.5),(1,65,.47),(2,69,.54),(3,67,.46)]: out.append(note(4+off,.5,m,v,{'articulation':'pizzicato'}))
    # verse answers
    for off,m,d in [(0,69,1.4),(1.7,67,.75),(2.7,65,1.0)]: out.append(note(3*4+off,d,m,.58,{'articulation':'tenuto'}))
    # pre spiccato rise
    for bar,seq in [(5,[62,65,67,69,70,69,67,65]),(6,[65,67,69,70,72,70,69,67])]:
        for i,m in enumerate(seq): out.append(note(bar*4+i*.5,.33,m,.52+.02*(i%4),{'articulation':'spiccato'}))
    # chorus motif + development
    motif=[(0,74,.9),(1,72,.7),(2,69,.8),(3,67,.7),(4,69,.8),(5,72,.7),(6,74,1.3)]
    for off,m,d in motif: out.append(note(7*4+off,d,m,.66+.03*(off in (0,4)),{'articulation':'tenuto'}))
    for off,m,d in motif: out.append(note(9*4+off,d,m+2,.65+.03*(off in (0,4)),{'articulation':'tenuto'}))
    out.append(note(10*4+.22,1.0,81,.60,{'articulation':'harmonic'})); out.append(note(10*4+1.7,.7,77,.58,{'articulation':'spiccato'})); out.append(note(10*4+2.7,1.0,74,.60,{'articulation':'tenuto'}))
    out.append(note(11*4,.8,72,.55,{'articulation':'tenuto'})); out.append(note(11*4+1.0,2.5,69,.46,{'articulation':'tenuto'}))
    return out

def realize_violin(events):
    plan=plan_violin_track(events,bpm=BPM); by={(float(x['start_beat']),int(x['midi'])):x for x in plan['events']}; out=[]
    for ev in events:
        x=copy.deepcopy(ev); item=by[(float(x['start_beat']),int(x['midi']))]; perf=x.setdefault('performance',{})
        vr={'left_hand':copy.deepcopy(item['left_hand']),'transition':copy.deepcopy(item['transition']),'bow':copy.deepcopy(item['bow'])}
        if 'technique' in item: vr['technique']=copy.deepcopy(item['technique'])
        perf['violin_realization']=vr; out.append(x)
    return out

def drum_events():
    e=[]; micro=[0,-.006,.004,-.004,.003,-.005,.004,-.003]
    for bar in range(BARS):
        b=bar*4.; section='intro' if bar<2 else 'verse' if bar<5 else 'pre' if bar<7 else 'chorus' if bar<11 else 'outro'
        if bar==0: continue
        for step in range(8):
            t=b+step*.5+micro[step]
            if step==0 and bar in {2,5,7,9,11}: e.append(de('crash',t,.94 if bar!=7 else .98,.28,section)); continue
            if bar<2: k='hat_tight_closed'; v=.56 if step%2 else .65; d=.06
            elif bar<4: k='hat_closed'; v=.59 if step%2 else .68; d=.07
            elif bar<5: k='hat_half_open' if step in {3,7} else 'hat_closed'; v=.65 if 'half' in k else (.60 if step%2 else .69); d=.11 if 'half' in k else .07
            elif bar<7: k='hat_open' if step in {3,7} else 'hat_half_open'; v=.70 if k=='hat_open' else .63; d=.17 if k=='hat_open' else .11
            elif bar<11: k='ride'; v=.65 if step%2 else .75; d=.14
            else: k='hat_closed'; v=.53 if step%2 else .62; d=.07
            e.append(de(k,t,v,d,section))
        if bar<2: sn,sv='snare_cross_stick',.55
        elif bar<5: sn,sv='snare_cross_stick',.62
        elif bar<7: sn,sv='snare_center',.81
        elif bar<11: sn,sv='snare_rimshot',.90
        else: sn,sv='snare_center',.67
        backbeats=(1.012,) if bar==11 else (1.012,3.014)
        for off in backbeats: e.append(de(sn,b+off,sv,.11,section))
        if bar<2: kp=[(0,.70),(2,.66)]
        elif bar<5: kp=[(0,.83),(1.5,.65),(2,.77),(3.5,.63)]
        elif bar<7: kp=[(0,.86),(1,.67),(2,.81),(3.5,.71)]
        elif bar<11: kp=[(0,.91),(1.5,.71),(2,.86),(2.75,.66),(3.5,.73)]
        else: kp=[(0,.73),(2,.67)]
        for off,v in kp: e.append(de('kick',b+off,v,.12,section))
        if 2<=bar<7: e.append(de('snare_ghost',b+.742,.27 if bar<5 else .30,.06,section))
        if 7<=bar<10 and bar%2==1: e.append(de('snare_ghost',b+2.742,.29,.06,section))
    # pedal gesture chain in pre
    e += [
        ctrl(5*4+3.50,[(0,.88),(.12,0)],.12,'pre'),
        ctrl(6*4+1.50,[(0,0),(.12,.82)],.12,'pre'),
        ctrl(6*4+3.45,[(0,.90),(.14,0),(.26,.84)],.26,'pre')]
    # left-foot chicks under ride
    for bar in range(7,11):
        b=bar*4
        for off in (1.5,3.5): e.append(ctrl(b+off+.006,[(0,1),(.10,0)],.10,'chorus'))
    # chorus fill at bar 10, replacing timekeeper/backbeat in last half
    lo=10*4+2.0; hi=11*4; kept=[]
    for x in e:
        if x.get('event_type')!='drum' or x.get('drum')=='kick': kept.append(x); continue
        t=float(x['start_beat'])
        if lo<=t<hi and x.get('drum') in {'ride','snare_rimshot','snare_ghost','crash'}: continue
        kept.append(x)
    e=kept; b=10*4
    for off,k,v in [(2.04,'tom_high',.77),(2.54,'tom_mid',.81),(3.04,'tom_floor',.87),(3.54,'tom_floor',.91)]: e.append(de(k,b+off,v,.15,'chorus'))
    e.append(de('crash',b+3.78,.97,.30,'chorus')); e.append(de('kick',b+3.78,.93,.12,'chorus'))
    # final punctuation
    b=11*4; e.append(de('tom_floor',b+3.12,.75,.16,'outro')); e.append(de('crash',b+3.55,.87,.30,'outro')); e.append(de('kick',b+3.55,.81,.12,'outro'))
    return sorted(e,key=lambda x:(float(x['start_beat']),0 if x.get('event_type')=='drum_control' else 1,x.get('drum','')))

def build_ir():
    tracks=[
        {'id':'piano','instrument':'piano','source':{'type':'resolved'},'gain':.48,'pan':-.10,'events':piano_events()},
        {'id':'bass','instrument':'bass','source':{'type':'resolved'},'gain':.52,'pan':0.0,'events':bass_events()},
        {'id':'violin','instrument':'violin','source':{'type':'resolved'},'gain':.39,'pan':.13,'events':realize_violin(violin_raw())},
        {'id':'drums','instrument':'drums','source':{'type':'resolved'},'gain':.86,'pan':0.0,'events':drum_events()},]
    return {
        'meta':{'global_seed':SEED,'sample_rate':SR,'title':'Cobalt Meridian'},'transport':{'bpm':BPM,'beats_per_bar':4},
        'tonal':{'root':'D','scale':'natural_minor'},
        'form':[{'id':'intro','start_bar':0,'bars':2,'energy':.45},{'id':'verse','start_bar':2,'bars':3,'energy':.62},{'id':'pre','start_bar':5,'bars':2,'energy':.78},{'id':'chorus','start_bar':7,'bars':4,'energy':1.0},{'id':'outro','start_bar':11,'bars':1,'energy':.48}],
        'materials':{'motifs':{},'progressions':{},'rhythms':{}},
        'instruments':{'piano':materialize_preset('piano.concert_grand',role='piano'),'bass':materialize_preset('bass.electric_finger_modeled',role='bass'),'violin':materialize_preset('bowed.violin.modeled_articulated',role='lead'),'drums':materialize_preset(DRUM_PRESET,role='drums')},
        'tracks':tracks,'mix':{'tail_seconds':TAIL_S,'drive':1.18,'ceiling':.94}}

def rms(x): return float(np.sqrt(np.mean(np.asarray(x,dtype=np.float64)**2)+1e-18)) if len(x) else 0.
def peak(x): return float(np.max(np.abs(np.asarray(x,dtype=np.float64)))) if len(x) else 0.
def write_wav(path,y):
    pcm=(np.clip(y,-1,1)*32767).astype(np.int16)
    with wave.open(str(path),'wb') as wf: wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(pcm.tobytes())

def render_track_to_npy(track_id,out_path):
    ir=build_ir(); n=_timeline_size(ir,SR,BEAT_S); tr=next(t for t in ir['tracks'] if t['id']==track_id)
    y=_render_dry_track(ir,tr,n,SR,BEAT_S,graph_mode=False); np.save(out_path,y); return y

def finalize(out_dir,parts_dir):
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True); parts=Path(parts_dir); ir=build_ir(); d=next(t for t in ir['tracks'] if t['id']=='drums')
    perf=analyze_drummer_performance({'transport':ir['transport'],'tracks':[d]})
    if not perf['playable'] or perf['strained'] or perf['issue_count']!=0: raise RuntimeError(perf)
    stems={k:np.load(parts/f'{k}.npy') for k in ('piano','bass','violin','drums')}
    raw=sum(stems.values()); master=soft_limit(raw,drive=1.18,ceiling=.94)
    write_wav(out/'01_COBALT_MERIDIAN_FULL_PRODUCTION.wav',master); write_wav(out/'02_DRUM_STEM.wav',stems['drums'])
    nd=soft_limit(stems['piano']+stems['bass']+stems['violin'],drive=1.18,ceiling=.94); write_wav(out/'03_NO_DRUMS_STEM.wav',nd)
    a=int(5*4*BEAT_S*SR); b=int(11*4*BEAT_S*SR); write_wav(out/'04_PRE_TO_CHORUS_PRODUCTION_GATE.wav',master[a:b])
    metrics={'title':'Cobalt Meridian','sample_rate':SR,'bpm':BPM,'bars':BARS,'symbolic_duration_s':BARS*4*BEAT_S,'render_duration_s':len(master)/SR,'master_rms':rms(master),'master_peak':peak(master),'clipped_sample_ratio':float(np.mean(np.abs(master)>=1.0)),'stem_rms':{k:rms(v) for k,v in stems.items()},'track_event_counts':{t['id']:len(t['events']) for t in ir['tracks']},'drummer_performance':perf,'drum_preset':DRUM_PRESET,'global_seed':SEED}
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8'); (out/'drum_events.json').write_text(json.dumps(d['events'],indent=2),encoding='utf-8'); (out/'song_ir.json').write_text(json.dumps(ir,indent=2),encoding='utf-8')
    (out/'README.md').write_text('# S27-L Full-Song Production Closure — Cobalt Meridian\n\n24 kHz / 112 BPM / 12-bar compressed full-form production (Intro → Verse → Pre → Chorus → Outro). Uses locked S27-B R1 metal hi-hat + S27-K R2 pedal path.\n\nListen first to `01_COBALT_MERIDIAN_FULL_PRODUCTION.wav`; `04_PRE_TO_CHORUS_PRODUCTION_GATE.wav` concentrates open/half-open hats, pedal motion, crash, ride, rimshot and tom transition.\n\nS27-L adds no synthesis feature; it is a listening-first production closure gate for discovering the next audible bottleneck.\n',encoding='utf-8')
    print(json.dumps({k:metrics[k] for k in ('symbolic_duration_s','render_duration_s','master_rms','master_peak','clipped_sample_ratio','track_event_counts')},indent=2)); print(json.dumps({'playable':perf['playable'],'strained':perf['strained'],'issue_count':perf['issue_count'],'limb_event_counts':perf['limb_event_counts'],'issue_counts':perf['issue_counts']},indent=2))

if __name__=='__main__':
    import sys
    if len(sys.argv)>=3 and sys.argv[1]=='track': render_track_to_npy(sys.argv[2],sys.argv[3])
    elif len(sys.argv)>=4 and sys.argv[1]=='finalize': finalize(sys.argv[2],sys.argv[3])
    else: raise SystemExit('usage: track <id> <npy> | finalize <outdir> <partsdir>')
