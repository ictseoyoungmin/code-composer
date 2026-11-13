#!/usr/bin/env python3
"""Render original audition material through the canonical acoustic-piano chain.

Developer evidence only: this music is outside the installable Skill. Presets
supply sound, never notes. Requires the normal package plus FFmpeg for optional
static loudness matching. No recorded audio, SoundFont or network is used.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

import numpy as np
from scipy.io import wavfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/code-composer/kit/src'))
from code_composer.audio.piano import render_piano_track_with_controls, apply_piano_soundboard
from code_composer.audio.piano_design import resolve_piano_design
from code_composer.presets import materialize_preset

PRESETS=('piano.concert_grand_natural','piano.concert_grand_focused')


def audition_events(kind='phrase'):
    """Explicit original notes for this listening comparison, not a style template."""
    events=[]
    def note(at,midi,duration,velocity):
        ordinal=sum('midi' in e for e in events)
        events.append({'midi':midi,'start_beat':at,'duration_beats':duration,
            'velocity':velocity,'performance':{'piano_strike_seed':2820+ordinal*7919,
                                              'piano_strike_ordinal':ordinal}})
    if kind=='phrase':
        melody=[(0,74,.7,.64),(.75,78,.35,.68),(1.25,81,.7,.74),(2.25,78,.55,.69),(3,76,.65,.60),
         (4,74,.9,.65),(5,73,.4,.60),(5.5,71,.6,.57),(6.5,74,.9,.64),(7.5,78,.35,.68),
         (8,79,.7,.68),(8.75,78,.35,.62),(9.25,76,.7,.63),(10.25,74,.55,.58),(11,71,.7,.54),
         (12,73,.7,.64),(12.75,76,.35,.69),(13.25,81,.6,.73),(14,83,.45,.77),(14.75,85,.75,.80),
         (16,86,1.05,.78),(17.25,85,.35,.67),(17.75,83,.65,.66),(18.75,81,.45,.64),(19.35,78,.45,.58),
         (20,76,.5,.59),(20.75,78,.4,.62),(21.5,74,2.1,.63)]
        for values in melody:note(*values)
        for bar,(root,fifth,third) in enumerate([(50,57,66),(47,54,62),(43,50,59),(45,52,61),(47,54,62),(50,57,66)]):
            note(bar*4,root,1.1,.27);note(bar*4+1.5,fifth,.65,.25);note(bar*4+2.5,third,.70,.29)
            events.append({'event_type':'piano_control','control':'sustain_pedal','start_beat':bar*4.,
                'duration_beats':4.,'points':[{'offset_beats':0.,'position':0.},
                {'offset_beats':.1,'position':1.},{'offset_beats':3.5,'position':1.},
                {'offset_beats':3.8,'position':0.},{'offset_beats':4.,'position':0.}]})
        beat_s=.6;total_s=16.8
    elif kind=='touch':
        for i,v in enumerate([.3,.5,.75,.95]):note(i*1.4,76,.7,v)
        for i in range(6):note(6.+i*.28,78,.18,.68)
        note(8.5,84,1.4,.72)
        events.append({'event_type':'piano_control','control':'sustain_pedal','start_beat':0.,
            'duration_beats':10.,'points':[{'offset_beats':0.,'position':0.},{'offset_beats':10.,'position':0.}]})
        beat_s=1.;total_s=12.
    elif kind=='sustain':
        for i,m in enumerate([72,76,84,88]):
            note(i*4.,m,2.5,.75)
        events.append({'event_type':'piano_control','control':'sustain_pedal','start_beat':0.,
            'duration_beats':16.,'points':[{'offset_beats':0.,'position':0.},{'offset_beats':16.,'position':0.}]})
        beat_s=1.;total_s=16.5
    else:
        raise ValueError(f'unknown audition: {kind}')
    return events,beat_s,total_s


def render_preset(preset,events,beat_s,total_s,sr,*,alignment=None):
    patch=resolve_piano_design(materialize_preset(preset,role='piano'))
    if alignment is not None:
        patch['piano_graph']['strings']['hammer_phase_alignment']=float(alignment)
    snapshot=deepcopy((events,patch));n=int(round(total_s*sr))
    dry=render_piano_track_with_controls(events,n,sr,patch,beat_s)
    if dry is None:raise RuntimeError('explicit acoustic control path not used')
    audio=apply_piano_soundboard(dry,sr,patch,events,beat_s)
    if snapshot!=(events,patch):raise RuntimeError('render mutated its authored inputs')
    if audio.shape!=(n,2) or not np.isfinite(audio).all():raise RuntimeError('invalid acoustic output')
    return audio,patch


def measure_loudness(path):
    result=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(path),
        '-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True,check=True)
    summary=result.stderr.rsplit('Summary:',1)[-1]
    integrated=re.search(r'I:\s*([-\d.]+)\s*LUFS',summary)
    peak=re.search(r'Peak:\s*([-\d.]+)\s*dBFS',summary)
    if integrated is None or peak is None:raise RuntimeError('FFmpeg measurement unavailable')
    return float(integrated.group(1)),float(peak.group(1))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--sample-rate',type=int,default=48000,choices=(24000,48000))
    parser.add_argument('--kinds',nargs='+',choices=('phrase','touch','sustain'),default=['phrase','touch','sustain'])
    parser.add_argument('--no-match',action='store_true',help='Keep raw float WAVs without FFmpeg matching')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    manifest={'format':'piano-focus-audition/v1','sample_rate':args.sample_rate,
        'pipeline':'materialize_preset -> resolve_piano_design -> explicit acoustic track -> shared soundboard',
        'master_effects':False,'samples_or_external_audio':False,'listening_acceptance':'OPEN',
        'versions':{'python':sys.version,'numpy':np.__version__},'auditions':{}}
    for kind in args.kinds:
        events,beat_s,total_s=audition_events(kind)
        inputs={'events':events,'beat_seconds':beat_s,'total_seconds':total_s}
        encoded=json.dumps(inputs,sort_keys=True,separators=(',',':')).encode()
        (args.out/f'{kind}_events.json').write_text(json.dumps(inputs,indent=2)+'\n')
        item={'events_sha256':hashlib.sha256(encoded).hexdigest(),'variants':[]}
        for label,preset in zip(('previous','focused'),PRESETS):
            started=time.perf_counter();audio,patch=render_preset(preset,events,beat_s,total_s,args.sample_rate)
            elapsed=time.perf_counter()-started;raw=args.out/f'{kind}_{label}_raw.wav'
            wavfile.write(raw,args.sample_rate,audio.astype(np.float32))
            (args.out/f'{label}_resolved_patch.json').write_text(json.dumps(patch,indent=2)+'\n')
            row={'label':label,'preset':preset,'render_seconds':elapsed,'raw_file':raw.name,
                'raw_peak':float(np.max(np.abs(audio))),'raw_rms':float(np.sqrt(np.mean(audio*audio)))}}
            if not args.no_match:row['raw_lufs'],row['raw_true_peak_dbfs']=measure_loudness(raw)
            item['variants'].append(row)
        if not args.no_match:
            # One constant gain per complete clip; never per note or time-varying.
            target=min(-22.,*(r['raw_lufs']-2.0-r['raw_true_peak_dbfs'] for r in item['variants']))
            item['matched_target_lufs']=target
            for row in item['variants']:
                sr,audio=wavfile.read(args.out/row['raw_file']);gain_db=target-row['raw_lufs']
                audio=audio.astype(np.float64)*10**(gain_db/20.)
                if np.max(np.abs(audio))>=1.:raise RuntimeError('matching would clip')
                output=args.out/f'{kind}_{row["label"]}.wav'
                wavfile.write(output,sr,np.rint(audio*32767).astype(np.int16))
                row.update({'static_gain_db':gain_db,'matched_file':output.name,
                    'sha256':hashlib.sha256(output.read_bytes()).hexdigest()})
                row['matched_lufs'],row['matched_true_peak_dbfs']=measure_loudness(output)
        manifest['auditions'][kind]=item
        print(kind,json.dumps(item),flush=True)
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return 0

if __name__=='__main__':raise SystemExit(main())
