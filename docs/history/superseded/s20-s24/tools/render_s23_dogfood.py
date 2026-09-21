from pathlib import Path
import json, wave, zipfile
import numpy as np
from code_composer.presets import materialize_preset
from code_composer.percussion import render_drum_event
from code_composer.drum_analysis import analyze_drum_hit

ROOT=Path('/mnt/data')
OUT=ROOT/'S23_DRUM_PERFORMANCE_TO_TIMBRE_AUDITION'
OUT.mkdir(exist_ok=True)
SR=24000; BPM=96; BEAT=60/BPM; BARS=8; TOTAL_BEATS=BARS*4
P=materialize_preset('drums.acoustic_kit_modeled_expressive',role='drums')

def write_wav(path,y):
    y=np.asarray(y,dtype=np.float64)
    y=np.clip(y,-1,1)
    pcm=(y*32767).astype('<i2')
    with wave.open(str(path),'wb') as w:
        w.setnchannels(2 if pcm.ndim==2 else 1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

def cat_with_gap(a,b,gap=.75):
    z=np.zeros((int(gap*SR),2),dtype=np.float64)
    return np.vstack([a,z,b])

def hit(kind,art=None,force=None,pos=None,vel=.82,seed=17,dur=.10):
    return render_drum_event(kind,dur,SR,vel,seed=seed,patch=P,articulation=art,strike_force=force,strike_position=pos)

# Isolated semantic checks.
iso={}
iso['01_snare_soft_then_hard_same_velocity_24k.wav']=cat_with_gap(hit('snare','center',.18,.35),hit('snare','center',.90,.35))
iso['02_snare_center_then_edge_same_force_24k.wav']=cat_with_gap(hit('snare','center',.62,.10,seed=19),hit('snare','center',.62,.90,seed=19))
iso['03_tom_mid_center_then_edge_same_force_24k.wav']=cat_with_gap(hit('tom_mid','center',.62,.10,seed=23),hit('tom_mid','center',.62,.90,seed=23))
iso['04_ride_bow_soft_then_hard_same_velocity_24k.wav']=cat_with_gap(hit('ride','bow',.18,.40,seed=29),hit('ride','bow',.90,.40,seed=29))
iso['05_crash_centerward_then_edgeward_same_force_24k.wav']=cat_with_gap(hit('crash','crash',.72,.12,seed=31),hit('crash','crash',.72,.92,seed=31))
for name,y in iso.items(): write_wav(OUT/name,y)

# 114 explicit events: 64 hats + 16 kicks + 16 snares + 18 feature events.
events=[]
for bar in range(BARS):
    b=bar*4
    for i in range(8):
        events.append((b+i*.5,'hat','closed' if bar<3 else ('half_open' if bar<6 else 'open'),.10,.48+(.08 if i in (0,4) else 0)))
    for off in (0,2): events.append((b+off,'kick',None,.10,.78 if off==0 else .68))
    for off in (1,3): events.append((b+off,'snare','center',.10,.78))
# 18 extra explicit events.
extras=[
(0,'crash','crash',.10,.72),(4,'ride','bow',.10,.62),(6,'ride','bell',.10,.66),(8,'tom_high','center',.10,.64),
(8.5,'tom_mid','center',.10,.66),(9,'tom_floor','center',.10,.70),(12,'crash','crash',.10,.74),(14,'ride','bow',.10,.64),
(16,'ride','bell',.10,.68),(18,'tom_high','edge',.10,.66),(18.5,'tom_mid','edge',.10,.68),(19,'tom_floor','edge',.10,.72),
(20,'crash','crash',.10,.78),(24,'ride','bow',.10,.66),(26,'ride','bell',.10,.70),(28,'tom_high','center',.10,.68),
(29,'tom_mid','center',.10,.72),(30,'tom_floor','center',.10,.76)]
events += extras
assert len(events)==114, len(events)

def controls(kind,art,beat,vel):
    # Authored, deterministic performance intent. No random humanization.
    phase=(beat%4)/4
    force=.38+.48*vel
    pos=.30
    if kind=='snare':
        force=.32 if vel<.65 else .86
        pos=.28 if phase<.5 else .62
    elif kind.startswith('tom_'):
        force=.72; pos=.18 if art=='center' else .86
    elif kind=='kick':
        force=.78; pos=.35
    elif kind=='hat':
        force=.38+.34*vel; pos=.58 if art in ('half_open','open') else .44
    elif kind=='ride':
        force=.60 if art=='bow' else .78; pos=.34 if art=='bell' else .55
    elif kind=='crash':
        force=.80; pos=.86
    return float(np.clip(force,0,1)),float(np.clip(pos,0,1))

n=int((TOTAL_BEATS*BEAT+3.0)*SR)
control=np.zeros((n,2),dtype=np.float64); treatment=np.zeros_like(control)
for idx,(beat,kind,art,dur,vel) in enumerate(sorted(events,key=lambda x:x[0])):
    start=int(beat*BEAT*SR); seed=101+idx*7919
    a=render_drum_event(kind,dur,SR,vel,seed=seed,patch=P,articulation=art)
    f,p=controls(kind,art,beat,vel)
    b=render_drum_event(kind,dur,SR,vel,seed=seed,patch=P,articulation=art,strike_force=f,strike_position=p)
    control[start:min(n,start+len(a))]+=a[:max(0,min(n-start,len(a)))]
    treatment[start:min(n,start+len(b))]+=b[:max(0,min(n-start,len(b)))]
peak=max(float(np.max(np.abs(control))),float(np.max(np.abs(treatment))))
scale=min(1.0,.94/max(peak,1e-12))
control*=scale; treatment*=scale
write_wav(OUT/'09_matched_8bar_groove_S22_semantics_control_24k.wav',control)
write_wav(OUT/'10_matched_8bar_groove_S23_performance_treatment_24k.wav',treatment)
write_wav(OUT/'00_matched_groove_control_then_S23_treatment_24k.wav',cat_with_gap(control,treatment,1.0))

metrics={
 'sample_rate':SR,'bpm':BPM,'bars':BARS,'explicit_events':len(events),
 'preset':'drums.acoustic_kit_modeled_expressive@1.0.0',
 'control_semantics':'same S23 preset with strike_force/strike_position omitted; byte-identical S22 hit path',
 'snare_force':{
   'soft':analyze_drum_hit(hit('snare','center',.18,.35),SR),
   'hard':analyze_drum_hit(hit('snare','center',.90,.35),SR)},
 'snare_position':{
   'center':analyze_drum_hit(hit('snare','center',.62,.10,seed=19),SR),
   'edge':analyze_drum_hit(hit('snare','center',.62,.90,seed=19),SR)},
 'tom_mid_position':{
   'center':analyze_drum_hit(hit('tom_mid','center',.62,.10,seed=23),SR),
   'edge':analyze_drum_hit(hit('tom_mid','center',.62,.90,seed=23),SR)},
 'ride_force':{
   'soft':analyze_drum_hit(hit('ride','bow',.18,.40,seed=29),SR),
   'hard':analyze_drum_hit(hit('ride','bow',.90,.40,seed=29),SR)},
 'crash_position':{
   'centerward':analyze_drum_hit(hit('crash','crash',.72,.12,seed=31),SR),
   'edgeward':analyze_drum_hit(hit('crash','crash',.72,.92,seed=31),SR)},
 'groove':{'shared_scale':scale,'control_peak':float(np.max(np.abs(control))),'control_rms':float(np.sqrt(np.mean(control*control))),'treatment_peak':float(np.max(np.abs(treatment))),'treatment_rms':float(np.sqrt(np.mean(treatment*treatment)))},
 'scope':'dry source only; same notes/articulations/velocities/timing; only explicit S23 strike controls differ'
}
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
(OUT/'README.md').write_text('# S23 Drum Performance-to-Timbre Audition\n\n24 kHz native dry-source audition. The full-groove control and treatment use the same 114 explicit drum events, timing, velocity, articulation and expressive preset. The control omits S23 strike controls, so it follows the byte-identical S22 hit path; the treatment explicitly authors `strike_force` and `strike_position`. No room/reverb/master coloration or random humanization is added.\n\nStart with `00_...wav`, then use files 01–05 for isolated control meaning.\n')
zip_path=ROOT/'S23_DRUM_PERFORMANCE_TO_TIMBRE_DOGFOOD.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    for f in sorted(OUT.iterdir()): z.write(f,Path(OUT.name)/f.name)
print(json.dumps(metrics,indent=2))
print(zip_path)
