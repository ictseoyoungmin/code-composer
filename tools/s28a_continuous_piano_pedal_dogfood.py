from pathlib import Path
import json, wave
import numpy as np

from code_composer.render import render
from code_composer.audio.piano_design import resolve_piano_design

SR=24000
BPM=92.0
BEAT_S=60.0/BPM
OUT=Path('/mnt/data/s28a_piano_pedal_audition')
OUT.mkdir(parents=True,exist_ok=True)

PATCH=resolve_piano_design({
    'kind':'piano',
    'piano_design':{
        'family':'acoustic',
        'categories':{
            'body':'concert_grand','hammer':'medium_felt','stringing':'concert',
            'soundboard':'open_board','perspective':'player',
        },
        'controls':{},
    },
})

CHORDS=[
    (0.0,3.45,[38,50,57,62,64,74]),
    (4.0,3.50,[34,46,53,58,62,69]),
    (8.0,3.60,[31,43,50,55,59,67]),
    (12.0,3.35,[36,48,55,60,64,72]),
]

def notes(legacy_pedal):
    out=[]
    for bi,(start,dur,midis) in enumerate(CHORDS):
        for i,midi in enumerate(midis):
            vel=.58+.035*i + (.025 if i==len(midis)-1 else 0)
            out.append({
                'midi':midi,'start_beat':start,'duration_beats':dur,
                'velocity':min(.86,vel),
                'performance':{'pedal':bool(legacy_pedal)},
            })
    return out

def controls():
    out=[]
    for bar in range(4):
        start=bar*4.0
        # A short authored lift at the harmony boundary, then immediate repedal.
        if bar==0:
            pts=[(0.0,1.0),(3.86,1.0),(3.94,0.0),(4.0,0.0)]
        else:
            pts=[(0.0,0.0),(0.04,1.0),(3.86,1.0),(3.94,0.0),(4.0,0.0)]
        out.append({
            'event_type':'piano_control','control':'sustain_pedal',
            'start_beat':start,'duration_beats':4.0,
            'points':[{'offset_beats':x,'position':y} for x,y in pts],
        })
    return out

def ir(explicit):
    ev=notes(True)
    if explicit:
        ev+=controls()
    ev=sorted(ev,key=lambda x:(x['start_beat'],0 if x.get('event_type')=='piano_control' else 1,x.get('midi',0)))
    return {
        'meta':{'global_seed':2801,'sample_rate':SR},
        'transport':{'bpm':BPM,'beats_per_bar':4},
        'tonal':{'root':'D','scale':'minor'},
        'form':[{'id':'intro','start_bar':0,'bars':4}],
        'materials':{'motifs':{},'progressions':{},'rhythms':{}},
        'instruments':{'piano':PATCH},
        'tracks':[{'id':'piano','instrument':'piano','source':{'type':'resolved'},'events':ev,'gain':.92}],
        'mix':{'tail_seconds':2.0,'drive':1.15,'ceiling':.95},
    }

def wavcat(paths,out_path,gap_s=.5):
    arrays=[]
    for path in paths:
        with wave.open(str(path),'rb') as wf:
            sr=wf.getframerate(); n=wf.getnframes(); ch=wf.getnchannels()
            a=np.frombuffer(wf.readframes(n),dtype=np.int16).reshape(-1,ch)
        arrays.append(a)
        arrays.append(np.zeros((int(gap_s*sr),ch),dtype=np.int16))
    data=np.concatenate(arrays[:-1],axis=0)
    with wave.open(str(out_path),'wb') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(data.tobytes())

def rms(x): return float(np.sqrt(np.mean(np.asarray(x,dtype=np.float64)**2)+1e-30))

legacy_path=OUT/'01_LEGACY_NOTE_LOCAL_PEDAL.wav'
explicit_path=OUT/'02_S28A_CONTINUOUS_PEDAL.wav'
legacy,sr,_=render(ir(False),legacy_path)
explicit,sr,_=render(ir(True),explicit_path)
wavcat([legacy_path,explicit_path],OUT/'03_LEGACY_then_S28A_AB.wav')

# Isolate the first harmony without later chords so cross-boundary residue is measurable.
legacy_ir=ir(False); legacy_ir['tracks'][0]['events']=[e for e in legacy_ir['tracks'][0]['events'] if e['start_beat']==0]
explicit_ir=ir(True); explicit_ir['tracks'][0]['events']=[e for e in explicit_ir['tracks'][0]['events'] if e.get('event_type')=='piano_control' or e.get('start_beat')==0]
legacy_iso,_,_=render(legacy_ir,OUT/'04_FIRST_CHORD_LEGACY_PEDAL.wav')
explicit_iso,_,_=render(explicit_ir,OUT/'05_FIRST_CHORD_S28A_PEDAL_UP.wav')
wavcat([OUT/'04_FIRST_CHORD_LEGACY_PEDAL.wav',OUT/'05_FIRST_CHORD_S28A_PEDAL_UP.wav'],OUT/'06_FIRST_CHORD_TAIL_AB.wav')

boundary_s=4*BEAT_S
win=(boundary_s+.30,boundary_s+1.20)
def wrms(x,a,b):
    i=int(a*SR); j=min(len(x),int(b*SR)); return rms(x[i:j]) if j>i else 0.0
metrics={
    'sample_rate':SR,'bpm':BPM,'bars':4,
    'bar_seconds':4*BEAT_S,
    'legacy_first_chord_residual_rms_300_1200ms_after_next_bar':wrms(legacy_iso,*win),
    's28a_first_chord_residual_rms_300_1200ms_after_pedal_up':wrms(explicit_iso,*win),
    'residual_ratio_s28a_over_legacy':wrms(explicit_iso,*win)/max(1e-30,wrms(legacy_iso,*win)),
    'full_legacy_rms':rms(legacy),'full_s28a_rms':rms(explicit),
}
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
(OUT/'README.md').write_text('''# S28-A Continuous Piano Pedal Audition\n\n- 01: historical note-local pedal=True semantics\n- 02: explicit piano_control sustain_pedal down/up/repedal timeline\n- 03: 01 then 02 A/B\n- 04/05/06: first-chord-only tail diagnostic around the next harmony boundary\n\nThe musical notes/velocities are identical. Only sustain-pedal semantics differ.\n''',encoding='utf-8')
print(json.dumps(metrics,indent=2))
