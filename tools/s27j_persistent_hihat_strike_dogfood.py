from __future__ import annotations
import argparse, copy, json, wave
from pathlib import Path
import numpy as np

from code_composer.presets import materialize_preset
from code_composer.render import _render_dry_track
from code_composer.analysis.drummer_performance_analysis import analyze_drummer_performance

SR=24000; BPM=116.0; BEAT_S=60.0/BPM
OLD='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_continuous_hihat'
NEW='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_persistent_hihat'


def ev(kind,beat,vel=.82,dur=.12):
    return {'event_type':'drum','drum':kind,'start_beat':float(beat),'duration_beats':float(dur),'velocity':float(vel)}

def ctrl(start,duration,points):
    return {'event_type':'drum_control','control':'hi_hat_pedal_openness','start_beat':float(start),'duration_beats':float(duration),'points':[{'offset_beats':float(x),'openness':float(y)} for x,y in points]}

def rms(x):
    x=np.asarray(x,dtype=np.float64); return float(np.sqrt(np.mean(x*x)+1e-18)) if len(x) else 0.0

def render(preset,events,seconds,room,seed=272700):
    patch=materialize_preset(preset,role='drums')
    if not room:
        patch=copy.deepcopy(patch); patch['drum_graph']['kit_integration']['enabled']=False
    ir={'meta':{'global_seed':seed},'instruments':{'drums':patch}}
    tr={'id':'drums','instrument':'drums','events':events}
    return _render_dry_track(ir,tr,int(seconds*SR),SR,BEAT_S,graph_mode=True)

def match(x,ref):
    g=rms(ref)/max(1e-12,rms(x)); return x*g

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
    # Bar 1: pedal closes early, later open-labelled stick hits should retain the closed/half state.
    E += [ctrl(0,.75,[(0,1),(.35,.55),(.75,.24)])]
    for b in [0,1,2,3]: E.append(ev('kick',b,.90 if b in (0,2) else .78))
    for b in [1,3]: E.append(ev('snare_center',b,.90,.10))
    for b in [.5,1.5,2.5,3.5]: E.append(ev('hat_open',b,.80))
    # Bar 2: reopen, then hold half-open before two later strikes.
    E += [ctrl(4,.75,[(0,.24),(.75,.82)]),ctrl(5.0,.5,[(0,.82),(.5,.50)])]
    for b in [4,5,6,7]: E.append(ev('kick',b,.88))
    for b in [5,7]: E.append(ev('snare_rimshot',b,.94,.10))
    for b in [4.5,5.5,6.5,7.5]: E.append(ev('hat_open',b,.81))
    # Bar 3: ride + left-foot change; later hat returns under persistent near-closed state.
    E += [ctrl(8,.5,[(0,.50),(.5,.15)])]
    for b in [8,9,10,11]: E.append(ev('kick',b,.86))
    for b in [9,11]: E.append(ev('snare_center',b,.88,.10))
    for b in [8,9,10,11]: E.append(ev('ride',b,.73,.12))
    E += [ev('hat_open',10.5,.78),ev('hat_open',11.5,.78)]
    # Bar 4: reopen into open hits, then tom fill.
    E += [ctrl(12,.75,[(0,.15),(.75,.95)])]
    for b in [12,13,14]: E.append(ev('kick',b,.90))
    E += [ev('snare_rimshot',13,.96,.10),ev('hat_open',12.5,.82),ev('hat_open',13.5,.84),ev('hat_open',14.5,.86)]
    E += [ev('tom_high',15,.84,.10),ev('tom_mid',15.25,.87,.10),ev('tom_floor',15.5,.91,.12),ev('crash',15.75,.96,.12)]
    return sorted(E,key=lambda x:(float(x.get('start_beat',0)),0 if x.get('event_type')=='drum_control' else 1))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    outputs={}; metrics={}
    # Isolated completed-curve persistence.
    iso=[ctrl(0,.5,[(0,1),(.5,.22)]),ev('hat_open',1,.88)]
    oi=render(OLD,iso,1.8,False); nj=render(NEW,iso,1.8,False)
    outputs['01_PERSISTENT_HALF_CLOSED_S27I_then_S27J_DRY.wav']=pair(oi,nj)
    onset=.0+1*BEAT_S
    metrics['persistent_hit']={'s27i_late_rms':rms(window(oi,onset+.16,onset+.38)),'s27j_late_rms':rms(window(nj,onset+.16,onset+.38)),'ratio':rms(window(nj,onset+.16,onset+.38))/max(1e-12,rms(window(oi,onset+.16,onset+.38)))}
    # Same open-labelled hit under three persistent pedal states.
    seq=[]; cursor=0.0
    rendered=[]
    for val in (.90,.50,.12):
        e=[ctrl(0,.5,[(0,1),(.5,val)]),ev('hat_open',1,.88)]
        rendered.append(render(NEW,e,1.6,False,seed=272701))
    outputs['02_PEDAL_STATE_STRIKE_LADDER_OPEN_HALF_CLOSED_DRY.wav']=np.concatenate([rendered[0],np.zeros((int(.25*SR),2)),rendered[1],np.zeros((int(.25*SR),2)),rendered[2]],axis=0)
    # Close, strike, reopen, strike again.
    trans=[ctrl(0,.5,[(0,1),(.5,.18)]),ev('hat_open',1,.86),ctrl(2,.5,[(0,.18),(.5,.88)]),ev('hat_open',3,.86)]
    outputs['03_CLOSE_STRIKE_REOPEN_STRIKE_S27I_then_S27J_DRY.wav']=pair(render(OLD,trans,2.4,False),render(NEW,trans,2.4,False))
    # Full groove.
    G=groove(); duration=(16.5*BEAT_S)+1.8
    gi=render(OLD,G,duration,True,seed=272702); gj=render(NEW,G,duration,True,seed=272702)
    outputs['04_GROOVE_S27I_then_S27J_ROOM_RAW.wav']=pair(gi,gj,.5)
    gjm=match(gj,gi); outputs['05_GROOVE_S27I_then_S27J_ROOM_RMS_MATCHED.wav']=pair(gi,gjm,.5)
    gdi=render(OLD,G,duration,False,seed=272702); gdj=render(NEW,G,duration,False,seed=272702); gdjm=match(gdj,gdi)
    outputs['06_GROOVE_S27I_then_S27J_DRY_RMS_MATCHED.wav']=pair(gdi,gdjm,.5)
    report=analyze_drummer_performance({'transport':{'bpm':BPM,'beats_per_bar':4},'tracks':[{'id':'drums','instrument':'drums','events':G}]})
    metrics['groove']={'events':len(G),'audible_hits':sum(e.get('event_type')=='drum' for e in G),'controls':sum(e.get('event_type')=='drum_control' for e in G),'raw_rms_s27i':rms(gi),'raw_rms_s27j':rms(gj),'rms_match_gain':rms(gi)/max(1e-12,rms(gj)),'drummer':report}
    for name,y in outputs.items(): write_wav(out/name,y)
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2))
    (out/'events.json').write_text(json.dumps(G,indent=2))
    (out/'README.md').write_text('''# S27-J Persistent Hi-Hat Pedal State / Strike Coupling Audition\n\n24 kHz / 116 BPM. Every A/B is S27-I first, then S27-J.\n\n1. `05_GROOVE...ROOM_RMS_MATCHED.wav` — primary perceptual gate.\n2. `01_PERSISTENT_HALF_CLOSED...` — a pedal curve finishes before the later stick hit; S27-J must remember it.\n3. `02_PEDAL_STATE_STRIKE_LADDER...` — same authored `hat_open` strike under open / half / near-closed persistent pedal states.\n4. `03_CLOSE_STRIKE_REOPEN_STRIKE...` — persistent state changes subsequent strikes without resurrecting earlier energy.\n5. `04_GROOVE...ROOM_RAW.wav` and `06_GROOVE...DRY_RMS_MATCHED.wav` — context checks.\n\nPass gate: later stick hits must inherit the authored pedal position, state changes should alter contact/decay rather than behave like a post-hit fader, no-control S27-I sound must remain exact, and pedal control must not change unrelated drum RNG identity or duck other voices.\n''')
    print(json.dumps(metrics,indent=2))

if __name__=='__main__': main()
