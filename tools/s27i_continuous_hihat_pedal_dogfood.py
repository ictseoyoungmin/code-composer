from __future__ import annotations

import argparse
import copy
import json
import wave
from pathlib import Path

import numpy as np

from code_composer.analysis.drummer_performance_analysis import analyze_drummer_performance
from code_composer.presets import materialize_preset
from code_composer.render import _render_dry_track
from code_composer.validation_contracts import validate_drum_control_events

SR=24000
BPM=116.0
BEAT_S=60.0/BPM
SEED=271002
OLD='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_stateful_hihat'
NEW='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_continuous_hihat'


def ev(kind, beat, vel=.8, dur=.10, section='s27i'):
    return {'event_type':'drum','drum':kind,'start_beat':float(beat),'duration_beats':float(dur),'velocity':float(vel),'section_id':section}


def ctrl(start,duration,points,section='pedal_curve'):
    return {
        'event_type':'drum_control','control':'hi_hat_pedal_openness',
        'start_beat':float(start),'duration_beats':float(duration),'section_id':section,
        'points':[{'offset_beats':float(x),'openness':float(y)} for x,y in points],
    }


def isolated(name):
    if name=='gradual_close':
        return [ev('hat_open',0,.88,.14),ctrl(0,.90,[(0,1),(.22,1),(.50,.62),(.72,.25),(.90,0)])], .22
    if name=='partial_reopen':
        return [ev('hat_open',0,.88,.14),ctrl(0,1.15,[(0,1),(.18,1),(.48,.18),(.72,.18),(1.15,1)])], .18
    if name=='half_hold':
        return [ev('hat_open',0,.88,.14),ctrl(0,1.0,[(0,1),(.20,1),(.55,.55),(1.0,.55)])], .20
    raise ValueError(name)


def groove_events():
    out=[]
    curves={
        0:[(0,1),(.20,1),(.45,.70),(.75,.34),(1.0,.10)],
        1:[(0,1),(.18,1),(.48,.52),(.72,.52),(1.0,.90)],
        2:[(0,1),(.22,1),(.42,.30),(.65,.12),(1.0,.12)],
        3:[(0,1),(.20,1),(.45,.58),(.72,.26),(1.0,0)],
    }
    for bar in range(4):
        base=bar*4.0
        # Closed timekeeping first, then one open hit whose residual is shaped by
        # a separately authored left-foot curve over one beat.
        for off in (0,.5,1,1.5):
            out.append(ev('hat_closed',base+off,.70,.08,'timekeeping'))
        out.append(ev('hat_open',base+2.0,.84,.14,'open_phrase'))
        out.append(ctrl(base+2.0,1.0,curves[bar]))
        out.append(ev('hat_closed',base+3.5,.72,.08,'timekeeping'))
        for off,vel in ((0,.91),(1.5,.77),(2,.86),(3.5,.75)):
            out.append(ev('kick',base+off,vel,.12,'groove'))
        out.append(ev('snare_center',base+1.012,.89,.11,'groove'))
        out.append(ev('snare_center',base+3.014,.91,.11,'groove'))
        out.append(ev('snare_ghost',base+2.74,.30,.07,'groove'))
    return sorted(out,key=lambda x:(float(x['start_beat']),0 if x['event_type']=='drum_control' else 1,str(x.get('drum',''))))


def render(events,preset,room=True,n_s=None):
    patch=materialize_preset(preset,role='drums')
    if not room:
        patch=copy.deepcopy(patch)
        patch['drum_graph']['kit_integration']['enabled']=False
    if n_s is None:
        last=max(float(x['start_beat'])+float(x['duration_beats']) for x in events)
        n_s=last*BEAT_S+1.6
    ir={'meta':{'global_seed':SEED},'instruments':{'drums':patch}}
    track={'id':'drums','instrument':'drums','events':list(events)}
    return _render_dry_track(ir,track,int(n_s*SR),SR,BEAT_S,graph_mode=True)


def rms(x):
    x=np.asarray(x,dtype=np.float64)
    return float(np.sqrt(np.mean(x*x)+1e-18)) if len(x) else 0.0


def peak(x):
    return float(np.max(np.abs(x))) if len(x) else 0.0


def rms_match(x,target):
    return np.asarray(x,dtype=np.float64)*(rms(target)/max(rms(x),1e-12))


def silence(sec=.65):
    return np.zeros((int(sec*SR),2),dtype=np.float64)


def write(path,x):
    x=np.asarray(x,dtype=np.float64)
    scale=min(1.0,.98/max(peak(x),1e-12))
    pcm=(np.clip(x*scale,-1,1)*32767).astype(np.int16)
    with wave.open(str(path),'wb') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(pcm.tobytes())


def band_rms(x,low,high):
    mono=np.mean(np.asarray(x,dtype=np.float64),axis=1)
    if not len(mono): return 0.0
    spec=np.fft.rfft(mono)
    freq=np.fft.rfftfreq(len(mono),1/SR)
    sel=(freq>=low)&(freq<high)
    if not np.any(sel): return 0.0
    return float(np.sqrt(np.mean(np.abs(spec[sel])**2)+1e-18))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    metrics={}
    for idx,name in enumerate(('gradual_close','partial_reopen','half_hold'),1):
        events,contact_beat=isolated(name)
        probe={'instruments':{'drums':materialize_preset(NEW,role='drums')},'tracks':[{'id':'drums','instrument':'drums','events':events}]}
        validate_drum_control_events(probe)
        old=render(events,OLD,room=False,n_s=1.25); new=render(events,NEW,room=False,n_s=1.25)
        contact_s=contact_beat*BEAT_S
        pre=max(0,int((contact_s-.006)*SR))
        late=(int(.40*SR),int(.72*SR))
        metrics[name]={
            'precontact_max_abs_diff':float(np.max(np.abs(old[:pre]-new[:pre]))) if pre else 0.0,
            'old_late_rms':rms(old[late[0]:late[1]]),'new_late_rms':rms(new[late[0]:late[1]]),
            'new_over_old_late_rms':rms(new[late[0]:late[1]])/max(rms(old[late[0]:late[1]]),1e-12),
            'old_late_6_11k_rms':band_rms(old[late[0]:late[1]],6000,11000),
            'new_late_6_11k_rms':band_rms(new[late[0]:late[1]],6000,11000),
        }
        write(out/f'{idx:02d}_{name}_S27H_then_S27I_DRY.wav',np.vstack([old,silence(),new]))

    events=groove_events()
    probe={'instruments':{'drums':materialize_preset(NEW,role='drums')},'tracks':[{'id':'drums','instrument':'drums','events':events}]}
    validate_drum_control_events(probe)
    report=analyze_drummer_performance({'transport':{'bpm':BPM,'beats_per_bar':4},'tracks':[{'id':'drums','instrument':'drums','events':events}]})
    old=render(events,OLD,room=True); new=render(events,NEW,room=True)
    write(out/'04_GROOVE_S27H_then_S27I_ROOM_RAW.wav',np.vstack([old,silence(.9),new]))
    write(out/'05_GROOVE_S27H_then_S27I_ROOM_RMS_MATCHED.wav',np.vstack([rms_match(old,new),silence(.9),new]))
    dry_old=render(events,OLD,room=False); dry_new=render(events,NEW,room=False)
    write(out/'06_GROOVE_S27H_then_S27I_DRY_RMS_MATCHED.wav',np.vstack([rms_match(dry_old,dry_new),silence(.9),dry_new]))

    # Discrete S27-H behavior should remain a byte-exact control in S27-I when no
    # continuous trajectory is authored.
    discrete=[ev('hat_open',0,.88,.14),ev('hat_pedal',.75,.68,.08)]
    d_old=render(discrete,OLD,room=False,n_s=1.2); d_new=render(discrete,NEW,room=False,n_s=1.2)
    metrics['discrete_compatibility']={'max_abs_diff':float(np.max(np.abs(d_old-d_new)))}
    metrics['groove']={
        'events_total':len(events),
        'audible_drum_events':sum(x['event_type']=='drum' for x in events),
        'control_events':sum(x['event_type']=='drum_control' for x in events),
        'old_room_rms':rms(old),'new_room_rms':rms(new),'old_room_peak':peak(old),'new_room_peak':peak(new),
        'limb_counts':report.get('limb_event_counts'),'playable':report.get('playable'),'strained':report.get('strained'),
        'issue_counts':report.get('issue_counts'),
    }
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    (out/'events.json').write_text(json.dumps(events,indent=2)+'\n')
    (out/'drummer_performance.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'README.md').write_text(
        '# S27-I Continuous Hi-Hat Pedal Openness Audition\n\n'
        'Each A/B is **S27-H discrete-only baseline first, then S27-I explicit continuous pedal control**.\n\n'
        '- `01_gradual_close...`: open plate held free, then progressively closed without a new audible pedal hit.\n'
        '- `02_partial_reopen...`: strong contact followed by re-opening; lost energy must not return.\n'
        '- `03_half_hold...`: continuous move to half-open and hold.\n'
        '- `04_GROOVE...RAW`: four-bar full-kit performance with four explicit left-foot openness curves.\n'
        '- `05_GROOVE...RMS_MATCHED`: primary musical-context comparison.\n'
        '- `06_GROOVE...DRY_RMS_MATCHED`: source-state comparison without room.\n\n'
        'Pass gate: the plate should progressively shorten/darken as pedal contact increases, with no click, no unrelated-kit ducking, no energy resurrection after re-opening, and no hidden auto-generated foot gesture.\n'
    )
    print(json.dumps(metrics,indent=2))

if __name__=='__main__': main()
