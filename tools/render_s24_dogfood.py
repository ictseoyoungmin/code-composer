from pathlib import Path
import json, wave, zipfile
import numpy as np
from code_composer.presets import materialize_preset
from code_composer.percussion import render_drum_event
from code_composer.drum_analysis import analyze_drum_hit

ROOT=Path('/mnt/data')
OUT=ROOT/'S24_CYMBAL_PRESENCE_AUDITION'
OUT.mkdir(exist_ok=True)
SR=24000; BPM=96; BEAT=60/BPM; BARS=8; TOTAL_BEATS=BARS*4
P23=materialize_preset('drums.acoustic_kit_modeled_expressive',role='drums')
P24=materialize_preset('drums.acoustic_kit_modeled_cymbal_presence',role='drums')

def write_wav(path,y):
    y=np.asarray(y,dtype=np.float64); y=np.clip(y,-1,1); pcm=(y*32767).astype('<i2')
    with wave.open(str(path),'wb') as w:
        w.setnchannels(2 if pcm.ndim==2 else 1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

def cat(a,b,gap=.75):
    return np.vstack([a,np.zeros((int(gap*SR),2)),b])

def controls(kind,art,beat,vel):
    phase=(beat%4)/4; force=.38+.48*vel; pos=.30
    if kind=='snare': force=.32 if vel<.65 else .86; pos=.28 if phase<.5 else .62
    elif kind.startswith('tom_'): force=.72; pos=.18 if art=='center' else .86
    elif kind=='kick': force=.78; pos=.35
    elif kind=='hat': force=.38+.34*vel; pos=.58 if art in ('half_open','open') else .44
    elif kind=='ride': force=.60 if art=='bow' else .78; pos=.34 if art=='bell' else .55
    elif kind=='crash': force=.80; pos=.86
    return float(np.clip(force,0,1)),float(np.clip(pos,0,1))

def hit(patch,kind,art,force,pos,vel=.82,seed=17,dur=.10):
    return render_drum_event(kind,dur,SR,vel,seed=seed,patch=patch,articulation=art,strike_force=force,strike_position=pos)

def band_ratio(y,lo,hi):
    x=np.asarray(y).mean(axis=1); p=np.abs(np.fft.rfft(x*np.hanning(len(x))))**2+1e-20
    f=np.fft.rfftfreq(len(x),1/SR); den=p[(f>=500)&(f<=11500)].sum()
    return float(p[(f>=lo)&(f<hi)].sum()/max(den,1e-20))

def pair(name,kind,art,force,pos,vel=.82,seed=17,dur=.10):
    a=hit(P23,kind,art,force,pos,vel,seed,dur); b=hit(P24,kind,art,force,pos,vel,seed,dur)
    write_wav(OUT/name,cat(a,b)); return a,b

pairs={}
pairs['hat_open']=pair('01_open_hat_S23_then_S24_24k.wav','hat','open',.72,.65,.78,17,.10)
pairs['ride_bow']=pair('02_ride_bow_S23_then_S24_24k.wav','ride','bow',.72,.55,.82,19,.10)
pairs['ride_bell']=pair('03_ride_bell_S23_then_S24_24k.wav','ride','bell',.80,.32,.84,23,.10)
pairs['crash']=pair('04_crash_S23_then_S24_24k.wav','crash','crash',.86,.84,.86,29,.10)
# Non-cymbal guard audibly demonstrates no change.
pairs['snare_guard']=pair('05_snare_guard_S23_then_S24_24k.wav','snare','center',.86,.45,.82,31,.10)

# Same 114 events as S23 dogfood.
events=[]
for bar in range(BARS):
    b=bar*4
    for i in range(8):
        events.append((b+i*.5,'hat','closed' if bar<3 else ('half_open' if bar<6 else 'open'),.10,.48+(.08 if i in (0,4) else 0)))
    for off in (0,2): events.append((b+off,'kick',None,.10,.78 if off==0 else .68))
    for off in (1,3): events.append((b+off,'snare','center',.10,.78))
events += [
(0,'crash','crash',.10,.72),(4,'ride','bow',.10,.62),(6,'ride','bell',.10,.66),(8,'tom_high','center',.10,.64),
(8.5,'tom_mid','center',.10,.66),(9,'tom_floor','center',.10,.70),(12,'crash','crash',.10,.74),(14,'ride','bow',.10,.64),
(16,'ride','bell',.10,.68),(18,'tom_high','edge',.10,.66),(18.5,'tom_mid','edge',.10,.68),(19,'tom_floor','edge',.10,.72),
(20,'crash','crash',.10,.78),(24,'ride','bow',.10,.66),(26,'ride','bell',.10,.70),(28,'tom_high','center',.10,.68),
(29,'tom_mid','center',.10,.72),(30,'tom_floor','center',.10,.76)]
assert len(events)==114
n=int((TOTAL_BEATS*BEAT+3.0)*SR); y23=np.zeros((n,2)); y24=np.zeros((n,2))
for idx,(beat,kind,art,dur,vel) in enumerate(sorted(events,key=lambda x:x[0])):
    start=int(beat*BEAT*SR); seed=101+idx*7919; f,p=controls(kind,art,beat,vel)
    for target,patch in ((y23,P23),(y24,P24)):
        h=render_drum_event(kind,dur,SR,vel,seed=seed,patch=patch,articulation=art,strike_force=f,strike_position=p)
        stop=min(n,start+len(h)); target[start:stop]+=h[:stop-start]
peak=max(float(np.max(np.abs(y23))),float(np.max(np.abs(y24)))); scale=min(1.0,.94/max(peak,1e-12)); y23*=scale; y24*=scale
write_wav(OUT/'09_matched_8bar_groove_S23_24k.wav',y23)
write_wav(OUT/'10_matched_8bar_groove_S24_24k.wav',y24)
write_wav(OUT/'00_matched_groove_S23_then_S24_24k.wav',cat(y23,y24,1.0))

metrics={'sample_rate':SR,'bpm':BPM,'bars':BARS,'explicit_events':114,'control_preset':'drums.acoustic_kit_modeled_expressive@1.0.0','treatment_preset':'drums.acoustic_kit_modeled_cymbal_presence@1.0.0','shared_scale':scale,'pairs':{},'groove':{}}
for key,(a,b) in pairs.items():
    metrics['pairs'][key]={
      's23_rms':float(np.sqrt(np.mean(a*a))),'s24_rms':float(np.sqrt(np.mean(b*b))),
      'rms_ratio':float(np.sqrt(np.mean(b*b))/max(np.sqrt(np.mean(a*a)),1e-12)),
      's23_body_1p8_8k':band_ratio(a,1800,8000),'s24_body_1p8_8k':band_ratio(b,1800,8000),
      's23_hiss_9_11p5k':band_ratio(a,9000,11500),'s24_hiss_9_11p5k':band_ratio(b,9000,11500),
      's23_analysis':analyze_drum_hit(a,SR),'s24_analysis':analyze_drum_hit(b,SR),
    }
metrics['groove']={'s23_peak':float(np.max(np.abs(y23))),'s24_peak':float(np.max(np.abs(y24))),'s23_rms':float(np.sqrt(np.mean(y23*y23))),'s24_rms':float(np.sqrt(np.mean(y24*y24))),'clipping':int(np.sum(np.abs(y24)>=1.0))}
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
(OUT/'README.md').write_text('# S24 Cymbal Presence & Excitation Audition\n\n24 kHz native dry-source A/B. Every S23→S24 pair uses the same event, seed, velocity, articulation, strike_force, and strike_position. S24 changes only the opt-in cymbal presence/excitation block: metallic modal/body energy is reinforced, broadband wash is colored and amplitude-coupled to plate motion, and cymbal output is rebalanced against kick/snare/tom. No room/reverb/mic coloration or stateful choke is added.\n\nStart with `00_matched_groove_S23_then_S24_24k.wav`, then 01–04. File 05 is a non-cymbal byte-stability listening guard.\n')
zip_path=ROOT/'S24_CYMBAL_PRESENCE_EXCITATION_DOGFOOD.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    for f in sorted(OUT.iterdir()): z.write(f,Path(OUT.name)/f.name)
print(json.dumps(metrics,indent=2))
print(zip_path)
