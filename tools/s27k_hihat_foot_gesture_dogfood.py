from __future__ import annotations
import argparse, copy, json, wave
from pathlib import Path
import numpy as np

from code_composer.presets import materialize_preset
from code_composer.render import _render_dry_track
from code_composer.analysis.drummer_performance_analysis import analyze_drummer_performance

SR=24000; BPM=116.0; BEAT_S=60.0/BPM
OLD='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_persistent_hihat'
NEW='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_foot_gesture'

def ev(kind,beat,vel=.82,dur=.12):
    return {'event_type':'drum','drum':kind,'start_beat':float(beat),'duration_beats':float(dur),'velocity':float(vel)}
def ctrl(start,duration,points):
    return {'event_type':'drum_control','control':'hi_hat_pedal_openness','start_beat':float(start),'duration_beats':float(duration),'points':[{'offset_beats':float(x),'openness':float(y)} for x,y in points]}
def rms(x):
    x=np.asarray(x,dtype=np.float64); return float(np.sqrt(np.mean(x*x)+1e-18)) if len(x) else 0.0
def render(preset,events,seconds,room,seed=273100):
    patch=materialize_preset(preset,role='drums')
    if not room:
        patch=copy.deepcopy(patch); patch['drum_graph']['kit_integration']['enabled']=False
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
def window(y,a,b): return y[int(a*SR):int(b*SR)]

def groove():
    E=[]
    # Bar 1: explicit fast close -> physical chick in S27-K, then stored closed state.
    E += [ctrl(.25,.12,[(0,1.0),(.12,0.0)])]
    for b in [0,1,2,3]: E.append(ev('kick',b,.90 if b in (0,2) else .78))
    for b in [1,3]: E.append(ev('snare_center',b,.90,.10))
    for b in [.75,1.5,2.5,3.5]: E.append(ev('hat_open',b,.79))
    # Slow release: pedal state changes but should not create a splash transient.
    E += [ctrl(2.8,.75,[(0,0.0),(.75,.72)])]
    # Bar 2: authored fast close+reopen -> chick + foot-splash consequence.
    E += [ctrl(4.25,.20,[(0,.72),(.10,0.0),(.20,.86)])]
    for b in [4,5,6,7]: E.append(ev('kick',b,.88))
    for b in [5,7]: E.append(ev('snare_rimshot',b,.94,.10))
    for b in [4.5,5.5,6.5,7.5]: E.append(ev('hat_open',b,.81))
    # Bar 3: slow close should remain mechanically quiet while altering later strike state.
    E += [ctrl(8.25,.80,[(0,.86),(.80,.06)])]
    for b in [8,9,10,11]: E.append(ev('kick',b,.86))
    for b in [9,11]: E.append(ev('snare_center',b,.88,.10))
    for b in [8.5,9.5,10.5,11.5]: E.append(ev('hat_open',b,.78))
    # Bar 4: fast chick then a deliberately slow reopen, plus tom fill/crash.
    E += [ctrl(12.25,.14,[(0,.06),(.02,.86),(.14,0.0)])]
    E += [ctrl(13.0,.55,[(0,0.0),(.55,.58)])]
    for b in [12,13,14]: E.append(ev('kick',b,.90))
    E += [ev('snare_rimshot',13,.96,.10),ev('hat_open',12.5,.82),ev('hat_open',13.75,.82),ev('hat_open',14.5,.84)]
    E += [ev('tom_high',15,.84,.10),ev('tom_mid',15.25,.87,.10),ev('tom_floor',15.5,.91,.12),ev('crash',15.75,.96,.12)]
    return sorted(E,key=lambda x:(float(x.get('start_beat',0)),0 if x.get('event_type')=='drum_control' else 1))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    outputs={}; metrics={}
    # 1) Fast close: old control is silent, new control produces collision chick.
    fast=[ctrl(0,.12,[(0,1),(.12,0)])]
    a=render(OLD,fast,.85,False); b=render(NEW,fast,.85,False)
    outputs['01_FAST_CLOSE_CHICK_S27J_then_S27K_DRY.wav']=pair(a,b)
    metrics['fast_close']={'s27j_rms':rms(a),'s27k_rms':rms(b),'s27k_peak':float(np.max(np.abs(b)))}
    # 2) Slow close applied after an open hit: state damping remains, but S27-K must not add a fake chick.
    slow=[ev('hat_open',0,.86),ctrl(.40,1.0,[(0,1),(1.0,0)])]
    a=render(OLD,slow,1.5,False,seed=273101); b=render(NEW,slow,1.5,False,seed=273101)
    outputs['02_SLOW_CLOSE_NO_FAKE_CHICK_S27J_then_S27K_DRY.wav']=pair(a,b)
    metrics['slow_close']={'max_abs_diff':float(np.max(np.abs(a-b))),'rms_diff':rms(a-b)}
    # 3) Fast close->reopen foot splash.
    splash=[ctrl(0,.20,[(0,1),(.10,0),(.20,.86)])]
    a=render(OLD,splash,1.0,False,seed=273102); b=render(NEW,splash,1.0,False,seed=273102)
    outputs['03_FAST_CLOSE_REOPEN_SPLASH_S27J_then_S27K_DRY.wav']=pair(a,b)
    metrics['splash']={'s27j_rms':rms(a),'s27k_rms':rms(b),'late_rms_180_420ms':rms(window(b,.18,.42))}
    # 4-6) Full groove.
    G=groove(); duration=(16.6*BEAT_S)+1.8
    gj=render(OLD,G,duration,True,seed=273103); gk=render(NEW,G,duration,True,seed=273103)
    outputs['04_GROOVE_S27J_then_S27K_ROOM_RAW.wav']=pair(gj,gk,.5)
    gkm,gain=match(gk,gj); outputs['05_GROOVE_S27J_then_S27K_ROOM_RMS_MATCHED.wav']=pair(gj,gkm,.5)
    dj=render(OLD,G,duration,False,seed=273103); dk=render(NEW,G,duration,False,seed=273103); dkm,dgain=match(dk,dj)
    outputs['06_GROOVE_S27J_then_S27K_DRY_RMS_MATCHED.wav']=pair(dj,dkm,.5)
    report=analyze_drummer_performance({'transport':{'bpm':BPM,'beats_per_bar':4},'tracks':[{'id':'drums','instrument':'drums','events':G}]})
    metrics['groove']={'events':len(G),'audible_hits':sum(e.get('event_type')=='drum' for e in G),'controls':sum(e.get('event_type')=='drum_control' for e in G),'raw_rms_s27j':rms(gj),'raw_rms_s27k':rms(gk),'rms_match_gain':gain,'dry_rms_match_gain':dgain,'drummer':report}
    for name,y in outputs.items(): write_wav(out/name,y)
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2))
    (out/'events.json').write_text(json.dumps(G,indent=2))
    (out/'README.md').write_text('''# S27-K Hi-Hat Foot Gesture / Chick–Splash Coupling Audition\n\n24 kHz / 116 BPM. Every A/B is S27-J first, then S27-K.\n\n1. `05_GROOVE...ROOM_RMS_MATCHED.wav` — primary perceptual gate.\n2. `01_FAST_CLOSE_CHICK...` — an explicitly authored fast pedal close should create a compact two-cymbal chick only in S27-K.\n3. `02_SLOW_CLOSE_NO_FAKE_CHICK...` — slow pressure change must preserve state damping without synthesizing an artificial foot transient.\n4. `03_FAST_CLOSE_REOPEN_SPLASH...` — explicit close/reopen motion should create a longer foot-splash release.\n5. `04_GROOVE...ROOM_RAW.wav` / `06_GROOVE...DRY_RMS_MATCHED.wav` — context checks.\n\nPass gate: chick/splash must sound like physical consequences of the authored left-foot motion rather than extra sequenced samples; slow motion must stay quiet; existing S27-J stick/pedal-state behavior and non-hi-hat voices must remain intact.\n''')
    print(json.dumps(metrics,indent=2))

if __name__=='__main__': main()
