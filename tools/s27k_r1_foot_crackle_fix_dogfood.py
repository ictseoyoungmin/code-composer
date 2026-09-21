from __future__ import annotations
import argparse, copy, json, wave
from pathlib import Path
import numpy as np

from code_composer.presets import materialize_preset
from code_composer.audio.percussion import render_hi_hat_pedal_control
from code_composer.render import _render_dry_track
from code_composer.analysis.drummer_performance_analysis import analyze_drummer_performance

SR=24000; BPM=116.0; BEAT_S=60.0/BPM
PRESET='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_foot_gesture'

def ev(kind,beat,vel=.82,dur=.12):
    return {'event_type':'drum','drum':kind,'start_beat':float(beat),'duration_beats':float(dur),'velocity':float(vel)}
def ctrl(start,duration,points):
    return {'event_type':'drum_control','control':'hi_hat_pedal_openness','start_beat':float(start),'duration_beats':float(duration),'points':[{'offset_beats':float(x),'openness':float(y)} for x,y in points]}
def rms(x):
    x=np.asarray(x,dtype=np.float64); return float(np.sqrt(np.mean(x*x)+1e-18)) if len(x) else 0.0
def max_step(x,a,b):
    m=np.asarray(x,dtype=np.float64).mean(axis=1); s=m[int(a*SR):min(len(m),int(b*SR))]
    return float(np.max(np.abs(np.diff(s)))) if len(s)>1 else 0.0
def crest(x,a,b):
    m=np.asarray(x,dtype=np.float64).mean(axis=1); s=m[int(a*SR):min(len(m),int(b*SR))]
    return float(np.max(np.abs(s))/max(rms(s),1e-18)) if len(s) else 0.0
def legacy_patch():
    p=materialize_preset(PRESET,role='drums'); p=copy.deepcopy(p)
    p['drum_graph']['hi_hat_state']['pedal_audio'].pop('collision_profiles',None)
    p['drum_graph']['hi_hat_state']['pedal_audio']['model']='authored_motion_collision_v1'
    return p
def r1_patch(): return materialize_preset(PRESET,role='drums')
def render_control(patch,event,seed): return render_hi_hat_pedal_control(event,SR,BEAT_S,seed,patch)
def render_track(patch,events,seconds,room,seed=273103):
    patch=copy.deepcopy(patch)
    if not room: patch['drum_graph']['kit_integration']['enabled']=False
    ir={'meta':{'global_seed':seed},'instruments':{'drums':patch}}
    tr={'id':'drums','instrument':'drums','events':events}
    return _render_dry_track(ir,tr,int(seconds*SR),SR,BEAT_S,graph_mode=True)
def match(x,ref):
    g=rms(ref)/max(1e-12,rms(x)); return x*g,g
def pair(a,b,gap=.35):
    z=np.zeros((int(gap*SR),2),dtype=np.float64); return np.concatenate([a,z,b],axis=0)
def write_wav(path,y):
    y=np.asarray(y,dtype=np.float64); peak=max(1e-9,float(np.max(np.abs(y)))); scale=min(1.0,.98/peak)
    pcm=np.int16(np.clip(y*scale,-1,1)*32767)
    with wave.open(str(path),'wb') as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes(pcm.tobytes())

def groove():
    E=[]
    E += [ctrl(.25,.12,[(0,1.0),(.12,0.0)])]
    for b in [0,1,2,3]: E.append(ev('kick',b,.90 if b in (0,2) else .78))
    for b in [1,3]: E.append(ev('snare_center',b,.90,.10))
    for b in [.75,1.5,2.5,3.5]: E.append(ev('hat_open',b,.79))
    E += [ctrl(2.8,.75,[(0,0.0),(.75,.72)])]
    E += [ctrl(4.25,.20,[(0,.72),(.10,0.0),(.20,.86)])]
    for b in [4,5,6,7]: E.append(ev('kick',b,.88))
    for b in [5,7]: E.append(ev('snare_rimshot',b,.94,.10))
    for b in [4.5,5.5,6.5,7.5]: E.append(ev('hat_open',b,.81))
    E += [ctrl(8.25,.80,[(0,.86),(.80,.06)])]
    for b in [8,9,10,11]: E.append(ev('kick',b,.86))
    for b in [9,11]: E.append(ev('snare_center',b,.88,.10))
    for b in [8.5,9.5,10.5,11.5]: E.append(ev('hat_open',b,.78))
    E += [ctrl(12.25,.14,[(0,.06),(.02,.86),(.14,0.0)])]
    E += [ctrl(13.0,.55,[(0,0.0),(.55,.58)])]
    for b in [12,13,14]: E.append(ev('kick',b,.90))
    E += [ev('snare_rimshot',13,.96,.10),ev('hat_open',12.5,.82),ev('hat_open',13.75,.82),ev('hat_open',14.5,.84)]
    E += [ev('tom_high',15,.84,.10),ev('tom_mid',15.25,.87,.10),ev('tom_floor',15.5,.91,.12),ev('crash',15.75,.96,.12)]
    return sorted(E,key=lambda x:(float(x.get('start_beat',0)),0 if x.get('event_type')=='drum_control' else 1))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    old=legacy_patch(); new=r1_patch(); outputs={}; metrics={}
    chick=ctrl(0,.12,[(0,1),(.12,0)])
    a=render_control(old,chick,273102); b=render_control(new,chick,273102)
    outputs['01_OLD_S27K_then_R1_FAST_CLOSE_CHICK_DRY.wav']=pair(a,b)
    metrics['chick']={'old_rms_20_160':rms(a[int(.02*SR):int(.16*SR)]),'r1_rms_20_160':rms(b[int(.02*SR):int(.16*SR)]),'old_max_step_20_160':max_step(a,.02,.16),'r1_max_step_20_160':max_step(b,.02,.16),'old_crest_20_160':crest(a,.02,.16),'r1_crest_20_160':crest(b,.02,.16)}
    splash=ctrl(0,.20,[(0,1),(.10,0),(.20,.86)])
    a=render_control(old,splash,273102); b=render_control(new,splash,273102)
    outputs['02_OLD_S27K_then_R1_CLOSE_REOPEN_SPLASH_DRY.wav']=pair(a,b)
    metrics['splash']={'old_rms_180_420':rms(a[int(.18*SR):int(.42*SR)]),'r1_rms_180_420':rms(b[int(.18*SR):int(.42*SR)]),'old_max_step_180_420':max_step(a,.18,.42),'r1_max_step_180_420':max_step(b,.18,.42),'old_crest_180_420':crest(a,.18,.42),'r1_crest_180_420':crest(b,.18,.42)}
    slow=ctrl(0,1.0,[(0,1),(1.0,0)])
    a=render_control(old,slow,273102); b=render_control(new,slow,273102)
    outputs['03_SLOW_CLOSE_OLD_S27K_then_R1_SILENT.wav']=pair(a if len(a) else np.zeros((int(.2*SR),2)),b if len(b) else np.zeros((int(.2*SR),2)))
    metrics['slow_close']={'old_len':len(a),'r1_len':len(b),'both_silent':bool((len(a)==0 or rms(a)<1e-12) and (len(b)==0 or rms(b)<1e-12))}
    G=groove(); duration=(16.6*BEAT_S)+1.8
    ga=render_track(old,G,duration,True); gb=render_track(new,G,duration,True)
    outputs['04_GROOVE_OLD_S27K_then_R1_ROOM_RAW.wav']=pair(ga,gb,.5)
    gbm,g=match(gb,ga); outputs['05_GROOVE_OLD_S27K_then_R1_ROOM_RMS_MATCHED.wav']=pair(ga,gbm,.5)
    da=render_track(old,G,duration,False); db=render_track(new,G,duration,False); dbm,dg=match(db,da)
    outputs['06_GROOVE_OLD_S27K_then_R1_DRY_RMS_MATCHED.wav']=pair(da,dbm,.5)
    rep=analyze_drummer_performance({'transport':{'bpm':BPM,'beats_per_bar':4},'tracks':[{'id':'drums','instrument':'drums','events':G}]})
    metrics['groove']={'events':len(G),'raw_rms_old':rms(ga),'raw_rms_r1':rms(gb),'rms_match_gain':g,'dry_rms_match_gain':dg,'drummer':rep}
    for n,y in outputs.items(): write_wav(out/n,y)
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2))
    (out/'events.json').write_text(json.dumps(G,indent=2))
    (out/'README.md').write_text('''# S27-K R1 Foot-Crackle Fix Audition\n\n24 kHz / 116 BPM. Every A/B is old S27-K first, then S27-K R1.\n\nPrimary gate: `05_GROOVE_OLD_S27K_then_R1_ROOM_RMS_MATCHED.wav`.\n\n`01` isolates the fast-close chick. `02` isolates the close/reopen splash where the user heard a small crackling tail. `03` verifies slow pedal motion remains silent. `04`/`06` provide raw-room and dry context.\n\nR1 changes only control-derived foot-gesture collision texture. Direct S27-J/S27-K foot articulations remain byte-exact. Pass only if the small digital crackle disappears without turning chick/splash into a dull filtered noise or removing the physical two-cymbal identity.\n''')
    print(json.dumps(metrics,indent=2))
if __name__=='__main__': main()
