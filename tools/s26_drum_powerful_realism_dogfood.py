from __future__ import annotations
import copy, json, wave
from pathlib import Path
import numpy as np

from code_composer.presets import materialize_preset
from code_composer.audio.percussion import render_drum_event
from code_composer.audio.engines import engine_for_patch

SR=24000
BPM=118.0
BEAT_S=60.0/BPM
BARS=4
TAIL_S=1.8
N=int((BARS*4*BEAT_S+TAIL_S)*SR)
SEED=26092026


def ev(drum, beat, vel, dur=.12, pan=0.0):
    return {'event_type':'drum','drum':drum,'start_beat':float(beat),'duration_beats':float(dur),'velocity':float(vel),'pan':float(pan)}


def events():
    e=[]
    # Bar 1: assertive close-hat pocket. Crash replaces the downbeat hat.
    b=0.0
    e += [ev('crash',b,1.00,.30), ev('kick',b,1.00,.13)]
    for i,v in enumerate([.58,.46,.62,.48,.60,.47,.66]):
        pos=b+.5*(i+1) + (0.006 if i%2==0 else -0.004)
        e.append(ev('hat',pos,v,.08))
    e += [ev('snare',b+1.012,.96,.12), ev('snare',b+3.014,1.00,.12)]
    e += [ev('kick',b+1.50,.88,.13), ev('kick',b+2.53,.92,.13), ev('kick',b+3.50,.86,.13)]

    # Bar 2: same pocket, dynamic lift into the transition.
    b=4.0
    for i,v in enumerate([.62,.47,.64,.49,.66,.50,.70,.54]):
        pos=b+.5*i + (0.005 if i%2==0 else -0.005)
        e.append(ev('hat',pos,v,.08))
    e += [ev('snare',b+1.010,.97,.12), ev('snare',b+3.016,1.00,.12)]
    e += [ev('kick',b-.006, .96,.13), ev('kick',b+.75,.75,.13), ev('kick',b+2.0,.91,.13), ev('kick',b+2.75,.82,.13), ev('kick',b+3.50,.88,.13)]

    # Bar 3: section lift. Crash replaces ride on beat 1; ride resumes on 1&.
    b=8.0
    e += [ev('crash',b,1.00,.30), ev('kick',b,1.00,.13)]
    for i,v in enumerate([.64,.56,.70,.58,.68,.57,.76]):
        pos=b+.5*(i+1) + (0.004 if i%2==0 else -0.003)
        e.append(ev('ride',pos,v,.12))
    e += [ev('snare',b+1.014,.98,.12), ev('snare',b+3.015,1.00,.12)]
    e += [ev('kick',b+1.50,.90,.13), ev('kick',b+2.47,.94,.13), ev('kick',b+3.50,.89,.13)]

    # Bar 4: strong ride bar and a final crash/kick punctuation. No ride overlaps it.
    b=12.0
    for i,v in enumerate([.72,.58,.76,.61,.74,.60]):
        pos=b+.5*i + (0.004 if i%2==0 else -0.003)
        e.append(ev('ride',pos,v,.12))
    e += [ev('snare',b+1.013,.99,.12), ev('snare',b+3.014,1.00,.12)]
    e += [ev('kick',b, .98,.13), ev('kick',b+.75,.80,.13), ev('kick',b+2.0,.95,.13)]
    e += [ev('crash',b+3.0,1.00,.30), ev('kick',b+3.0,1.00,.13)]
    return sorted(e,key=lambda x:(x['start_beat'], {'kick':0,'snare':1,'hat':2,'ride':3,'crash':4}.get(x['drum'],9)))


def render_track(patch):
    out=np.zeros((N,2),dtype=np.float64)
    ee=events()
    for i,x in enumerate(ee):
        start=int(x['start_beat']*BEAT_S*SR)
        hit=render_drum_event(x['drum'],x['duration_beats']*BEAT_S,SR,x['velocity'],seed=SEED+i*7919,pan=x.get('pan',0.0),patch=patch)
        end=min(N,start+len(hit))
        if end>start: out[start:end]+=hit[:end-start]
    return out,ee


def rms(x): return float(np.sqrt(np.mean(np.asarray(x)**2)))
def peak(x): return float(np.max(np.abs(x)))
def crest(x): return peak(x)/max(rms(x),1e-12)

def band_ratio(x,lo,hi):
    mono=.5*(x[:,0]+x[:,1])
    w=np.hanning(len(mono)); sp=np.abs(np.fft.rfft(mono*w))**2
    f=np.fft.rfftfreq(len(mono),1/SR); total=sp.sum()+1e-18
    return float(sp[(f>=lo)&(f<hi)].sum()/total)

def write_wav(path,x):
    y=np.asarray(x)
    # Export safeguard only; metrics use the unscaled in-memory candidate.
    p=peak(y); scale=.98/max(.98,p) if p>.98 else 1.0
    pcm=(np.clip(y*scale,-1,1)*32767).astype(np.int16)
    with wave.open(str(path),'wb') as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(pcm.tobytes())
    return scale


def silence(seconds): return np.zeros((int(seconds*SR),2),dtype=np.float64)


def main(out_dir):
    out_dir=Path(out_dir); out_dir.mkdir(parents=True,exist_ok=True)
    dry_patch=materialize_preset('drums.s19_core_cymbal_extension',role='drums')
    wet_patch=materialize_preset('drums.s19_core_powerful_room',role='drums')
    dry,ee=render_track(dry_patch)
    source,ee2=render_track(wet_patch)
    assert np.array_equal(dry,source)  # source blocks are intentionally identical
    wet=engine_for_patch(wet_patch).post_process_track(source,SR,wet_patch,ee2,BEAT_S)

    # RMS-matched wet comparison isolates spatial/integration quality from loudness.
    match=rms(dry)/max(rms(wet),1e-12)
    wet_match=wet*match
    gap=silence(.75)
    ab=np.concatenate([dry,gap,wet_match],axis=0)

    # Switchback focuses on the two section-lift bars (bars 3-4).
    st=int(8*BEAT_S*SR); en=int((16*BEAT_S+1.3)*SR)
    d2=dry[st:en]; w2=wet_match[st:en]
    switch=np.concatenate([d2,gap,w2,gap,d2,gap,w2],axis=0)

    # Final crash window exposes room tail and bus recovery.
    c=int((15.0*BEAT_S)*SR); tail=int((15.0*BEAT_S+1.55)*SR)
    crash=np.concatenate([dry[c:tail],gap,wet_match[c:tail]],axis=0)

    scales={
        '00_DRY_R5_4BAR_24k.wav':write_wav(out_dir/'00_DRY_R5_4BAR_24k.wav',dry),
        '01_S26_POWERFUL_ROOM_4BAR_24k.wav':write_wav(out_dir/'01_S26_POWERFUL_ROOM_4BAR_24k.wav',wet),
        '02_DRY_then_S26_RMS_MATCHED_4BAR_24k.wav':write_wav(out_dir/'02_DRY_then_S26_RMS_MATCHED_4BAR_24k.wav',ab),
        '03_SECTION_LIFT_SWITCHBACK_DRY_S26_DRY_S26_24k.wav':write_wav(out_dir/'03_SECTION_LIFT_SWITCHBACK_DRY_S26_DRY_S26_24k.wav',switch),
        '04_FINAL_CRASH_DRY_then_S26_RMS_MATCHED_24k.wav':write_wav(out_dir/'04_FINAL_CRASH_DRY_then_S26_RMS_MATCHED_24k.wav',crash),
    }

    # Metrics by whole groove and selected transient/tail windows.
    kick0=int(0*BEAT_S*SR); snare0=int(1.012*BEAT_S*SR); crash0=kick0
    def wr(x,start,a,b):
        aa=start+int(a*SR); bb=min(len(x),start+int(b*SR));
        return rms(x[aa:bb])
    metrics={
        'sample_rate':SR,'bpm':BPM,'bars':BARS,'events':len(ee),'rms_match_gain':match,
        'dry':{'rms':rms(dry),'peak':peak(dry),'crest':crest(dry),'presence_2_6k':band_ratio(dry,2000,6000),'air_6_11k':band_ratio(dry,6000,11000)},
        's26':{'rms':rms(wet),'peak':peak(wet),'crest':crest(wet),'presence_2_6k':band_ratio(wet,2000,6000),'air_6_11k':band_ratio(wet,6000,11000)},
        'matched':{'rms':rms(wet_match),'peak':peak(wet_match),'crest':crest(wet_match)},
        'kick0':{'dry_0_20ms':wr(dry,kick0,0,.020),'s26_0_20ms':wr(wet_match,kick0,0,.020),'dry_30_120ms':wr(dry,kick0,.030,.120),'s26_30_120ms':wr(wet_match,kick0,.030,.120)},
        'snare1':{'dry_0_20ms':wr(dry,snare0,0,.020),'s26_0_20ms':wr(wet_match,snare0,0,.020),'dry_30_160ms':wr(dry,snare0,.030,.160),'s26_30_160ms':wr(wet_match,snare0,.030,.160)},
        'final_crash':{
            'dry_0_30ms':wr(dry,c,0,.030),'s26_0_30ms':wr(wet_match,c,0,.030),
            'dry_80_250ms':wr(dry,c,.080,.250),'s26_80_250ms':wr(wet_match,c,.080,.250),
            'dry_350_900ms':wr(dry,c,.350,.900),'s26_350_900ms':wr(wet_match,c,.350,.900),
        },
        'export_scales':scales,
    }
    (out_dir/'metrics.json').write_text(json.dumps(metrics,indent=2)+"\n")
    (out_dir/'events.json').write_text(json.dumps(ee,indent=2)+"\n")
    print(json.dumps(metrics,indent=2))

if __name__=='__main__':
    import sys
    main(sys.argv[1] if len(sys.argv)>1 else '/mnt/data/s26_powerful_realism_audition')
