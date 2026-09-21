from pathlib import Path
import json, wave
import numpy as np
from code_composer.audio.dsp import duck
from code_composer.presets import materialize_preset
from code_composer.render import _render_dry_track, _timeline_size

SR=24000
BPM=92.0
BEAT=60.0/BPM
OUT=Path('/mnt/data/s28f_piano_phrase_safe_ducking_audition')
OUT.mkdir(parents=True,exist_ok=True)
PIANO=Path('/mnt/data/s28_piano_naturalism_flagship/02_S28A_TO_D_NATURALISM_TREATMENT.wav')
DRUM_PRESET='drums.s19_core_powerful_room_authentic_strike_v2_hihat_snare_toms_integrated_foot_gesture_metal_hihat'

def readwav(path):
    with wave.open(str(path),'rb') as w:
        assert w.getframerate()==SR and w.getnchannels()==2 and w.getsampwidth()==2
        x=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float64)/32768.0
    return x.reshape(-1,2)

def writewav(path,x):
    q=(np.clip(np.asarray(x,float),-1,1)*32767).astype(np.int16)
    with wave.open(str(path),'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(q.tobytes())

def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x,float)**2)+1e-18))

def cat(paths,out,gap=.45):
    z=[]
    for i,p in enumerate(paths):
        z.append(readwav(p))
        if i+1<len(paths): z.append(np.zeros((int(gap*SR),2)))
    writewav(out,np.concatenate(z))

piano=readwav(PIANO)
events=[]
for bar in range(5):
    for off,vel in ((0.0,.86),(2.0,.78)):
        events.append({'event_type':'drum','drum':'kick','start_beat':bar*4+off,'duration_beats':.12,'velocity':vel})
ir={
 'meta':{'global_seed':280100,'sample_rate':SR,'title':'S28-F phrase-safe ducking audit'},
 'transport':{'bpm':BPM,'beats_per_bar':4},
 'tonal':{'root':'D','scale':'natural_minor'},
 'form':[{'id':'audit','start_bar':0,'bars':5,'energy':.7}],
 'materials':{'motifs':{},'progressions':{},'rhythms':{}},
 'instruments':{'drums':materialize_preset(DRUM_PRESET,role='drums')},
 'tracks':[{'id':'drums','role':'drums','instrument':'drums','events':events}],
 'mix':{'tail_seconds':2.0},
}
n=max(len(piano),_timeline_size(ir,SR,BEAT))
kick=_render_dry_track(ir,ir['tracks'][0],n,SR,BEAT,graph_mode=False)
if len(piano)<n:
    piano=np.pad(piano,((0,n-len(piano)),(0,0)))
else:
    kick=np.pad(kick,((0,max(0,len(piano)-len(kick))),(0,0)))[:len(piano)]

# Keep the sidechain detector independent from audible kick level.
audible_kick=kick*.22
settings={
 'no_duck':None,
 'current_1p8dB_8ms_150ms':dict(threshold_db=-28.0,amount_db=1.8,attack_s=.008,release_s=.150),
 'light_0p7dB_10ms_80ms':dict(threshold_db=-26.0,amount_db=.7,attack_s=.010,release_s=.080),
}
metrics={'sample_rate':SR,'bpm':BPM,'source_piano':'exact S28-D treatment / user-selected A baseline','settings':{},'kick_count':len(events)}
outputs={}
for name,cfg in settings.items():
    if cfg is None:
        processed=piano.copy(); gain=np.ones(len(piano))
    else:
        processed,gain=duck(piano,kick,SR,**cfg)
    mix=np.clip(processed+audible_kick,-1,1)
    path=OUT/f'{len(outputs)+1:02d}_{name}.wav'
    writewav(path,mix); outputs[name]=path
    db=20*np.log10(np.maximum(gain,1e-12)); active=gain<.999999
    metrics['settings'][name]={
      'config':cfg,
      'piano_rms_ratio':rms(processed)/rms(piano),
      'min_gain_db':float(db.min()),
      'gain_reduction_active_fraction':float(np.mean(active)),
      'mean_gain_db_when_active':float(db[active].mean()) if np.any(active) else 0.0,
    }

cat([outputs['no_duck'],outputs['current_1p8dB_8ms_150ms']],OUT/'04_NO_DUCK_then_CURRENT_AB.wav')
cat([outputs['current_1p8dB_8ms_150ms'],outputs['light_0p7dB_10ms_80ms']],OUT/'05_CURRENT_then_LIGHT_AB.wav')
cat([outputs['no_duck'],outputs['light_0p7dB_10ms_80ms']],OUT/'06_NO_DUCK_then_LIGHT_AB.wav')
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
(OUT/'README.md').write_text('''# S28-F Piano Phrase-Safe Ducking Audit\n\nA is the exact user-selected S28-D treatment baseline (S28-A R2 + S28-B/C/D; no S28-E). The musical content is unchanged. A modeled kick sidechain is used only to compare production ducking settings.\n\n- no_duck: no music-bus gain modulation\n- current: 1.8 dB / 8 ms / 150 ms / -28 dB threshold\n- light: 0.7 dB / 10 ms / 80 ms / -26 dB threshold\n\nThis slice does not change duck() or add automatic genre heuristics. The Composer/mix plan remains explicit.\n''',encoding='utf-8')
print(json.dumps(metrics,indent=2))
