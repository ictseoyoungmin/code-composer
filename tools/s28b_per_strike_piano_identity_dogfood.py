from pathlib import Path
import copy, json, wave
import numpy as np

from code_composer.render import render
from code_composer.presets import materialize_preset
from code_composer.audio.piano_design import resolve_piano_design

SR=24000
BPM=92.0
BEAT_S=60.0/BPM
OUT=Path('/mnt/data/s28b_piano_identity_audition')
OUT.mkdir(parents=True,exist_ok=True)

NATURAL=resolve_piano_design(materialize_preset('piano.concert_grand_natural', role='piano'))
STATIC=copy.deepcopy(NATURAL)
for key in list(STATIC['piano_graph']['strike_identity']):
    STATIC['piano_graph']['strike_identity'][key]=0.0

# Same authored pitch, duration and velocity. Only physical strike identity differs.
EVENTS=[]
for i in range(8):
    EVENTS.append({'midi':60,'start_beat':i*0.75,'duration_beats':0.42,'velocity':0.72})

# A second phrase gives a musically plausible repeated-note context rather than only lab impulses.
PHRASE=[]
for i,(midi,vel) in enumerate([(60,.66),(60,.70),(60,.73),(62,.72),(60,.69),(60,.75),(64,.76),(60,.68)]):
    PHRASE.append({'midi':midi,'start_beat':i*0.5,'duration_beats':0.31,'velocity':vel})

def make_ir(patch, events, seed=2812):
    return {
        'meta':{'global_seed':seed,'sample_rate':SR},
        'transport':{'bpm':BPM,'beats_per_bar':4},
        'tonal':{'root':'C','scale':'major'},
        'form':[{'id':'study','start_bar':0,'bars':2}],
        'materials':{'motifs':{},'progressions':{},'rhythms':{}},
        'instruments':{'piano':patch},
        'tracks':[{'id':'piano','instrument':'piano','source':{'type':'resolved'},'events':copy.deepcopy(events),'gain':.92}],
        'mix':{'tail_seconds':1.1,'drive':1.05,'ceiling':.95},
    }

def wavcat(paths,out_path,gap_s=.55):
    arrays=[]
    for path in paths:
        with wave.open(str(path),'rb') as wf:
            sr=wf.getframerate(); ch=wf.getnchannels(); n=wf.getnframes()
            a=np.frombuffer(wf.readframes(n),dtype=np.int16).reshape(-1,ch)
        arrays += [a,np.zeros((int(gap_s*sr),ch),dtype=np.int16)]
    data=np.concatenate(arrays[:-1],axis=0)
    with wave.open(str(out_path),'wb') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(data.tobytes())

def attack_segments(x, starts, seconds=.08):
    n=int(seconds*SR)
    return [np.asarray(x[s:s+n],dtype=np.float64).reshape(-1) for s in starts]

def corr(a,b):
    a=a-np.mean(a); b=b-np.mean(b)
    den=np.sqrt(np.sum(a*a)*np.sum(b*b))+1e-30
    return float(np.sum(a*b)/den)

static_path=OUT/'01_STATIC_IDENTITY_REPEATED_C4.wav'
natural_path=OUT/'02_S28B_PER_STRIKE_REPEATED_C4.wav'
static,_,_=render(make_ir(STATIC,EVENTS),static_path)
natural,_,_=render(make_ir(NATURAL,EVENTS),natural_path)
render(make_ir(STATIC,PHRASE),OUT/'03_STATIC_IDENTITY_PHRASE.wav')
render(make_ir(NATURAL,PHRASE),OUT/'04_S28B_PER_STRIKE_PHRASE.wav')
wavcat([static_path,natural_path],OUT/'05_STATIC_then_S28B_REPEATED_C4_AB.wav')
wavcat([OUT/'03_STATIC_IDENTITY_PHRASE.wav',OUT/'04_S28B_PER_STRIKE_PHRASE.wav'],OUT/'06_STATIC_then_S28B_PHRASE_AB.wav')

starts=[int(i*.75*BEAT_S*SR) for i in range(8)]
sa=attack_segments(static,starts); sb=attack_segments(natural,starts)
static_corrs=[corr(sa[0],sa[i]) for i in range(1,len(sa))]
natural_corrs=[corr(sb[0],sb[i]) for i in range(1,len(sb))]
metrics={
    'sample_rate':SR,'bpm':BPM,'seed':2812,
    'static_first_vs_later_attack_corr_mean':float(np.mean(static_corrs)),
    's28b_first_vs_later_attack_corr_mean':float(np.mean(natural_corrs)),
    'static_attack_corrs':static_corrs,
    's28b_attack_corrs':natural_corrs,
    'same_authored_pitch_velocity_duration':True,
    'deterministic_replay_expected':True,
}
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
(OUT/'README.md').write_text('''# S28-B Per-strike Piano Identity Audition\n\n01/02: same C4 repeated 8 times, same timing/duration/velocity and same natural piano patch. 01 disables strike variation; 02 enables deterministic per-strike hammer/string initial-condition variation.\n03/04: short repeated-note phrase under the same comparison.\n05/06: A/B concatenations.\n\nNo random humanize, pitch change, onset jitter, or gate change is used in this slice.\n''',encoding='utf-8')
print(json.dumps(metrics,indent=2))
