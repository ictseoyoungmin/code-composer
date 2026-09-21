from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path

import numpy as np

from code_composer.analysis.drummer_performance_analysis import analyze_drummer_performance
from code_composer.audio.drum_kit import integrate_drum_kit
from code_composer.audio.percussion import render_drum_event, apply_hi_hat_state_transitions
from code_composer.presets import materialize_preset

SR=24000
BPM=116.0
BEAT_S=60.0/BPM
SEED=270928
OLD='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated'
NEW='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_stateful_hihat'


def ev(kind, beat, vel=.8, dur=.08, section='hihat_state'):
    return {'event_type':'drum','drum':kind,'start_beat':float(beat),'duration_beats':float(dur),'velocity':float(vel),'section_id':section}


def groove_events():
    e=[]
    # Four bars. Open hats are intentionally closed by an explicit left-foot
    # pedal or a later more-closed authored stick articulation.
    hats={
        0:[(0,'hat_closed'),(.5,'hat_closed'),(1,'hat_closed'),(1.5,'hat_closed'),(2,'hat_closed'),(2.5,'hat_closed'),(3,'hat_half_open'),(3.5,'hat_open')],
        1:[(0.5,'hat_closed'),(1,'hat_closed'),(1.5,'hat_closed'),(2,'hat_half_open'),(2.5,'hat_half_open'),(3,'hat_half_open'),(3.5,'hat_open')],
        2:[(.5,'hat_closed'),(1,'hat_closed'),(1.5,'hat_closed'),(2,'hat_closed'),(2.5,'hat_open'),(3,'hat_closed'),(3.5,'hat_open')],
        3:[(.5,'hat_closed'),(1,'hat_closed'),(1.5,'hat_half_open'),(2,'hat_open'),(2.5,'hat_half_open'),(3,'hat_closed'),(3.5,'hat_open')],
    }
    for bar in range(4):
        base=bar*4.0
        for off,kind in hats[bar]:
            vel=.82 if kind=='hat_open' else (.76 if kind=='hat_half_open' else .71)
            e.append(ev(kind,base+off,vel,.14 if kind=='hat_open' else .09))
        # Left-foot closures at the next downbeat after bars 0/1 and final release.
        if bar in (1,2):
            e.append(ev('hat_pedal',base+.006,.62,.08,'pedal_close'))
        # pocket; two feet on some downbeats are legal.
        for off,vel in ((0,.91),(1.5,.78),(2,.86),(3.5,.74)):
            e.append(ev('kick',base+off,vel,.12,'groove'))
        e.append(ev('snare_center',base+1.012,.89,.11,'groove'))
        e.append(ev('snare_center',base+3.014,.91,.11,'groove'))
        e.append(ev('snare_ghost',base+2.744,.30,.07,'groove'))
    # Final left-foot choke after the final open hat.
    e.append(ev('hat_pedal',16.006,.64,.08,'pedal_close'))
    return sorted(e,key=lambda x:(x['start_beat'],x['drum']))


def isolated(kind='pedal'):
    if kind=='pedal':
        return [ev('hat_open',0,.88,.14),ev('hat_pedal',.75,.68,.08)]
    if kind=='closed':
        return [ev('hat_open',0,.88,.14),ev('hat_closed',.75,.76,.09)]
    if kind=='graded':
        return [ev('hat_open',0,.88,.14),ev('hat_half_open',.75,.75,.10),ev('hat_closed',1.35,.76,.09)]
    raise ValueError(kind)


def timeline(events, tail=1.6):
    last=max(x['start_beat']+x['duration_beats'] for x in events)
    return int((last*BEAT_S+tail)*SR)


def render(events,preset,room=True):
    patch=materialize_preset(preset,role='drums')
    n=timeline(events)
    dry=np.zeros((n,2),dtype=np.float64)
    for i,x in enumerate(events):
        start=int(x['start_beat']*BEAT_S*SR)
        hit=render_drum_event(x['drum'],x['duration_beats']*BEAT_S,SR,x['velocity'],seed=SEED+i*7919,patch=patch)
        hit=apply_hi_hat_state_transitions(hit,SR,x['drum'],i,events,BEAT_S,patch)
        end=min(n,start+len(hit))
        if end>start: dry[start:end]+=hit[:end-start]
    if not room:
        return dry
    cfg=patch['drum_graph'].get('kit_integration',{})
    wet,_=integrate_drum_kit(dry,SR,events,BEAT_S,cfg)
    return wet


def rms(x):
    x=np.asarray(x,dtype=np.float64)
    return float(np.sqrt(np.mean(x*x)+1e-18))


def peak(x):
    return float(np.max(np.abs(x))) if len(x) else 0.0


def rms_match(x,target):
    return np.asarray(x,dtype=np.float64)*(rms(target)/max(rms(x),1e-12))


def silence(sec=.65): return np.zeros((int(sec*SR),2),dtype=np.float64)


def write(path,x):
    x=np.asarray(x,dtype=np.float64)
    scale=min(1.0,.98/max(peak(x),1e-12))
    pcm=(np.clip(x*scale,-1,1)*32767).astype(np.int16)
    with wave.open(str(path),'wb') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(pcm.tobytes())


def tail_rms(x,close_beat,a=.07,b=.25):
    s=close_beat*BEAT_S
    return rms(x[int((s+a)*SR):int((s+b)*SR)])


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); a=ap.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)

    metrics={}
    for label,events,close in [
        ('pedal',isolated('pedal'),.75),('closed',isolated('closed'),.75),('graded',isolated('graded'),.75)
    ]:
        old=render(events,OLD,room=False); new=render(events,NEW,room=False)
        metrics[label]={
            'old_tail_rms':tail_rms(old,close),
            'new_tail_rms':tail_rms(new,close),
            'new_over_old':tail_rms(new,close)/max(tail_rms(old,close),1e-12),
            'preclosure_max_abs_diff':float(np.max(np.abs(old[:int((close*BEAT_S-.01)*SR)]-new[:int((close*BEAT_S-.01)*SR)]))),
        }
        idx={'pedal':'01','closed':'02','graded':'03'}[label]
        write(out/f'{idx}_{label}_S27G_then_S27H_DRY.wav',np.vstack([old,silence(),new]))

    events=groove_events()
    report=analyze_drummer_performance({'transport':{'bpm':BPM,'beats_per_bar':4},'tracks':[{'id':'drums','instrument':'drums','events':events}]})
    old=render(events,OLD,room=True); new=render(events,NEW,room=True)
    oldm=rms_match(old,new)
    write(out/'04_GROOVE_S27G_then_S27H_ROOM_RAW.wav',np.vstack([old,silence(.9),new]))
    write(out/'05_GROOVE_S27G_then_S27H_ROOM_RMS_MATCHED.wav',np.vstack([oldm,silence(.9),new]))
    dry_old=render(events,OLD,room=False); dry_new=render(events,NEW,room=False)
    write(out/'06_GROOVE_S27G_then_S27H_DRY_RMS_MATCHED.wav',np.vstack([rms_match(dry_old,dry_new),silence(.9),dry_new]))

    metrics['groove']={
        'events':len(events),'old_room_rms':rms(old),'new_room_rms':rms(new),
        'old_room_peak':peak(old),'new_room_peak':peak(new),
        'limb_counts':report.get('limb_event_counts'), 'playable':report.get('playable'),
        'strained':report.get('strained'),'issue_counts':report.get('issue_counts'),
    }
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2)+"\n")
    (out/'events.json').write_text(json.dumps(events,indent=2)+"\n")
    (out/'drummer_performance.json').write_text(json.dumps(report,indent=2)+"\n")
    (out/'README.md').write_text(
        '# S27-H Stateful Hi-Hat Closure Audition\n\n'
        'Listen to each A/B as **S27-G static tail first, then S27-H stateful closure**.\n\n'
        '- `01_pedal...`: open hat -> authored foot pedal closure.\n'
        '- `02_closed...`: open hat -> later closed stick articulation.\n'
        '- `03_graded...`: open -> half-open -> closed staged damping.\n'
        '- `04_GROOVE...RAW`: actual four-bar kit performance with shared room.\n'
        '- `05_GROOVE...RMS_MATCHED`: primary musical-context comparison.\n'
        '- `06_GROOVE...DRY_RMS_MATCHED`: source-state comparison without room.\n\n'
        'Pass gate: closure must sound like two physical cymbals being brought into contact, not a volume automation; the pedal/closed hit itself and other kit voices must remain intact.\n'
    )
    print(json.dumps(metrics,indent=2))

if __name__=='__main__': main()
