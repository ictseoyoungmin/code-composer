from pathlib import Path
import copy, json, wave
import numpy as np
from code_composer.render import render
from code_composer.presets import materialize_preset
from code_composer.audio.piano_design import resolve_piano_design

SR=24000; BPM=92.0; BEAT_S=60/BPM
OUT=Path('/mnt/data/s28c_piano_hand_attack_audition'); OUT.mkdir(parents=True,exist_ok=True)
PATCH=resolve_piano_design(materialize_preset('piano.concert_grand_natural', role='piano'))
MIDIS=[38,50,57,62,64,74]
OFFSETS=[0,4,8,11,13,15]

def events(rolled):
    out=[]
    for bar,root in enumerate([0.0,4.0,8.0]):
        for i,m in enumerate(MIDIS):
            perf={}
            if rolled: perf['piano_attack_offset_ms']=OFFSETS[i]
            out.append({'midi':m,'start_beat':root,'duration_beats':3.2,'velocity':min(.86,.58+.04*i),'performance':perf})
    return out

def ir(rolled):
    return {'meta':{'global_seed':2813,'sample_rate':SR},'transport':{'bpm':BPM,'beats_per_bar':4},
      'tonal':{'root':'D','scale':'minor'},'form':[{'id':'study','start_bar':0,'bars':3}],
      'materials':{'motifs':{},'progressions':{},'rhythms':{}},'instruments':{'piano':PATCH},
      'tracks':[{'id':'piano','instrument':'piano','source':{'type':'resolved'},'events':events(rolled),'gain':.92}],
      'mix':{'tail_seconds':1.2,'drive':1.05,'ceiling':.95}}

def wavcat(a,b,out,gap=.55):
    arr=[]
    for p in (a,b):
        with wave.open(str(p),'rb') as wf:
            x=np.frombuffer(wf.readframes(wf.getnframes()),dtype=np.int16).reshape(-1,wf.getnchannels()); sr=wf.getframerate()
        arr += [x,np.zeros((int(gap*sr),2),dtype=np.int16)]
    y=np.concatenate(arr[:-1])
    with wave.open(str(out),'wb') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(y.tobytes())

a_path=OUT/'01_SIMULTANEOUS_WIDE_CHORD.wav'; b_path=OUT/'02_S28C_AUTHORED_HAND_ROLL.wav'
a,_,_=render(ir(False),a_path); b,_,_=render(ir(True),b_path)
wavcat(a_path,b_path,OUT/'03_SIMULTANEOUS_then_S28C_AB.wav')
# first chord only concentration
first_a=copy.deepcopy(ir(False)); first_a['tracks'][0]['events']=[e for e in first_a['tracks'][0]['events'] if e['start_beat']==0]
first_b=copy.deepcopy(ir(True)); first_b['tracks'][0]['events']=[e for e in first_b['tracks'][0]['events'] if e['start_beat']==0]
render(first_a,OUT/'04_FIRST_CHORD_SIMULTANEOUS.wav'); render(first_b,OUT/'05_FIRST_CHORD_S28C_ROLL.wav')
wavcat(OUT/'04_FIRST_CHORD_SIMULTANEOUS.wav',OUT/'05_FIRST_CHORD_S28C_ROLL.wav',OUT/'06_FIRST_CHORD_AB.wav',gap=.35)

def peak(x,ms):
    n=int(ms*.001*SR); return float(np.max(np.abs(np.asarray(x[:n],dtype=np.float64))))
metrics={'sample_rate':SR,'bpm':BPM,'offsets_ms':OFFSETS,'same_score_onset':True,
         'simultaneous_first_30ms_peak':peak(a,30),'rolled_first_30ms_peak':peak(b,30)}
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
(OUT/'README.md').write_text('''# S28-C Authored Piano Hand Attack\n\n01: six-note wide chord with exact simultaneous onset.\n02: same score/onsets/velocities, but Composer-authored performance offsets [0,4,8,11,13,15] ms from low to high.\n03: 01 then 02. 04/05/06 isolate the first chord.\n\nThis is not random humanization and does not infer arpeggiation.\n''',encoding='utf-8')
print(json.dumps(metrics,indent=2))
