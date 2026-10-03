#!/usr/bin/env python3
"""Cedar Rain, Afterlight — production solo acoustic-guitar composition.

One persistent steel-string acoustic guitar, ~3 minutes, through-composed.
The piece is original. Structural/idiomatic inspiration only: Mauro Giuliani,
12 Divertimenti per chitarra, Op.40, via a 2026 IMSLP typeset marked CC0.
No melody, bar, voicing sequence, or arrangement passage is copied.
"""
from __future__ import annotations

import argparse, hashlib, json, math, wave
from copy import deepcopy
from pathlib import Path
import numpy as np

from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files
from code_composer.execution.performance_score import performance_score_fingerprint

BPM=82
PRESET="acoustic_guitar.steel_stateful_performance"
OPEN={1:64,2:59,3:55,4:50,5:45,6:40}
INSPIRATION={
 "work":"12 Divertimenti per chitarra, Op.40","composer":"Mauro Giuliani",
 "source":"IMSLP","license":"Creative Commons Zero 1.0 (2026 typeset by Marieh)",
 "url":"https://imslp.org/wiki/12_Divertimenti_per_chitarra%2C_Op.40_%28Giuliani%2C_Mauro%29",
 "usage":"high-level guitar idiom/structure only; composition is original",
}
VOICINGS={
 "Em9":[(40,6,0),(47,5,2),(52,4,2),(55,3,0),(59,2,0),(66,1,2)],
 "Cmaj7":[(48,5,3),(52,4,2),(55,3,0),(59,2,0),(64,1,0)],
 "G6":[(43,6,3),(47,5,2),(50,4,0),(55,3,0),(59,2,0),(64,1,0)],
 "D/F#":[(42,6,2),(45,5,0),(50,4,0),(57,3,2),(62,2,3),(66,1,2)],
 "Em/G":[(43,6,3),(47,5,2),(52,4,2),(55,3,0),(59,2,0),(64,1,0)],
 "Am7":[(45,5,0),(52,4,2),(57,3,2),(60,2,1),(64,1,0)],
 "C/G":[(43,6,3),(48,5,3),(52,4,2),(55,3,0),(60,2,1),(64,1,0)],
 "Dsus2":[(45,5,0),(50,4,0),(57,3,2),(62,2,3),(64,1,0)],
 "Fmaj7#11":[(41,6,1),(48,5,3),(52,4,2),(57,3,2),(59,2,0),(64,1,0)],
 "B7":[(47,5,2),(54,4,4),(57,3,2),(63,2,4),(66,1,2)],
 "B7sus4":[(47,5,2),(54,4,4),(57,3,2),(64,2,5),(66,1,2)],
}
LOW={k:[p for p in v if p[1]>=3] for k,v in VOICINGS.items()}
SECTIONS=[("prelude",4),("theme",12),("development",12),("bridge",8),("percussive",12),("recap",8),("coda",4)]
START={}; _c=0
for _s,_n in SECTIONS: START[_s]=_c; _c+=_n
TOTAL_BARS=_c
HARMONY=(
 ["Em9","Cmaj7","G6","B7"]+
 ["Em9","Cmaj7","G6","D/F#","Em/G","Am7","Cmaj7","B7","Em9","G6","Fmaj7#11","B7"]+
 ["Em9","C/G","D/F#","G6","Cmaj7","Am7","Dsus2","B7","Em/G","Fmaj7#11","Cmaj7","B7"]+
 ["G6","D/F#","Em9","Cmaj7","Am7","C/G","B7sus4","B7"]+
 ["Em9","Em/G","Cmaj7","G6","D/F#","Am7","Cmaj7","B7","Em9","Fmaj7#11","Cmaj7","B7"]+
 ["Em9","Cmaj7","G6","D/F#","Em/G","Am7","B7","Em9"]+
 ["Cmaj7","B7sus4","B7","Em9"])
assert len(HARMONY)==TOTAL_BARS

# Motif-development cells. Later sections rotate/invert/re-register these rather
# than repeating a fixed arpeggio loop.
PITCH_CELLS=[
 [64,67,66,64],[62,64,67,71],[69,67,64,62],[66,67,69,66],
 [64,71,69,67],[72,71,67,64],[66,69,67,66],[63,66,69,71],
 [64,67,71,76],[74,71,67,66],[72,71,69,67],[66,63,59,63],
]
RHYTHM_CELLS=[
 [.50,1.50,2.25,3.05],[.25,1.00,1.85,2.75],[.35,1.20,2.00,3.00],
 [.50,1.35,2.10,3.10],[.20,1.05,2.15,3.05],[.45,1.30,2.15,3.15],
 [.20,1.10,2.20,3.10],[.35,1.25,2.05,3.05],[.20,1.00,1.75,2.60],
 [.45,1.35,2.25,3.10],[.20,1.10,2.05,3.00],[.40,1.30,2.25,3.25],
]
ACC=[
 [(0.,0,1.18),(.55,2,.42),(1.05,1,.58),(1.62,3,.42),(2.10,0,.88),(2.72,2,.44),(3.28,1,.54)],
 [(0.,0,1.10),(.72,1,.48),(1.22,3,.40),(1.82,2,.48),(2.35,0,.82),(3.00,1,.48),(3.55,3,.32)],
 [(0.,0,1.22),(.48,2,.42),(1.18,3,.42),(1.78,1,.52),(2.40,0,.82),(2.92,2,.42),(3.46,3,.34)],
 [(0.,0,1.04),(.62,3,.40),(1.10,1,.50),(1.92,2,.42),(2.28,0,.86),(2.84,3,.40),(3.42,1,.38)],
]
ENERGY={"prelude":.49,"theme":.65,"development":.75,"bridge":.86,"percussive":.80,"recap":.69,"coda":.52}

def check(p):
 m,s,f=p
 if m!=OPEN[s]+f or not 0<=f<=20: raise ValueError(p)
for vv in VOICINGS.values():
 for pp in vv: check(pp)

def top_pos(midi,alt=False):
 opts=[]
 for s in (1,2):
  f=midi-OPEN[s]
  if 0<=f<=20: opts.append((midi,s,f))
 if not opts: raise ValueError(f"unplayable top note {midi}")
 if alt and len(opts)>1: return opts[-1]
 if midi<=67 and len(opts)>1: return opts[-1]
 return opts[0]

def note(eid,start,dur,p,vel,method="finger",left=None,pluck=None,angle=None):
 check(p); m,s,f=p
 strength=max(.28,min(.90,.42+.38*vel))
 if pluck is None: pluck=.16 if method in {"finger","thumb"} else .135
 if angle is None: angle=32. if method=="thumb" else (43. if method=="nail" else (36. if method=="pick" else 38.))
 perf={"string":s,"fret":f,"right_hand":{"method":method,"pluck_position":pluck,"attack_angle_deg":angle,"strength":strength}}
 if left: perf["left_hand"]=deepcopy(left)
 return {"id":eid,"type":"note","start_beat":float(start),"duration_beats":float(dur),"midi":m,"velocity":float(max(.18,min(.94,vel))),"instrument_performance":perf}

def action(eid,kind,start,strength,location=None):
 p={"strength":float(strength)}
 if location: p["location"]=location
 return {"id":eid,"type":"instrument_action","start_beat":float(start),"duration_beats":.08,"action":kind,"parameters":p}

def melody(bar0,local,section):
 base=PITCH_CELLS[local%12][:]
 rhythm=RHYTHM_CELLS[(local+(1 if section=="development" else 0))%12][:]
 if section=="development":
  # Phrase development: selective octave displacement + contour reversal.
  if local%3==1: base=list(reversed(base))
  if local in {2,3,8}: base=[min(78,x+12 if x<66 else x) for x in base]
  if local%4==2: rhythm=[max(.10,min(3.55,x-.15 if i%2==0 else x+.10)) for i,x in enumerate(rhythm)]
 elif section=="percussive":
  rhythm=[max(.10,min(3.55,x-.18 if i in {0,2} else x+.05)) for i,x in enumerate(rhythm)]
  if local%4==0: base=base[1:]+base[:1]
 elif section=="recap":
  if local in {1,2,4}: base=[min(76,x+12 if x<=64 else x) for x in base]
 # Cadential bars explicitly lean into D# over B7 instead of generic diatonic looping.
 if HARMONY[bar0] in {"B7","B7sus4"}: base=[66,63,59,63]
 durs=[.52,.48,.50,.70]
 return [(rhythm[i],base[i],durs[i]) for i in range(4)]

def finger_bar(bar0,local,section,percussive=False):
 chord=HARMONY[bar0]; low=LOW[chord]; e=ENERGY[section]+.025*math.sin((local+1)*.67)
 out=[]; patt=ACC[(local+(2 if percussive else 0))%4]
 for i,(off,idx,dur) in enumerate(patt):
  p=low[idx%len(low)]; method="thumb" if p[1]>=5 else "finger"
  contour=(.04,-.05,-.02,.00,.05,-.03,-.06)[i]
  out.append(note(f"b{bar0+1:02d}-a{i}",bar0*4+off,dur,p,e+contour,method))
 for j,(off,m,dur) in enumerate(melody(bar0,local,section)):
  p=top_pos(m,alt=((local+j)%7==0 and section in {"development","recap"}))
  method="nail" if (bar0+j)%13==0 else "finger"
  out.append(note(f"b{bar0+1:02d}-m{j}",bar0*4+off,dur,p,e+.05+(j==3)*.025,method,pluck=.145 if method=="nail" else .17))
 if percussive:
  if local%2==0:
   out += [action(f"b{bar0+1:02d}-tap","body_tap",bar0*4+1.50,.44,"lower_bout"),action(f"b{bar0+1:02d}-slap","top_slap",bar0*4+3.00,.47,"soundboard")]
  else:
   out += [action(f"b{bar0+1:02d}-slap","top_slap",bar0*4+1.50,.43,"soundboard"),action(f"b{bar0+1:02d}-ss","string_slap",bar0*4+3.25,.46)]
 return out

def strum_cfg(sid,direction,idx,energy,muted=False,rake=False):
 down=direction=="down"; strong=idx in {0,3}
 return {"stroke_id":sid,"direction":direction,"traversal_ms":76. if rake else (34. if down else 25.),"entry_strength":min(.90,energy+(.08 if strong else -.05)),"acceleration":.14 if down else -.09,"pick_depth":.62 if down else .47,"attack_angle_deg":41. if down else 34.,"follow_through":.78 if down else .60,"accent_position":.60 if down else .40,"accent_amount":.30 if strong else .08,"from_string":6 if down else 1,"to_string":1 if down else 6,"state":"muted" if muted else "sounding"}
STRUM=[
 [(0.,"down",0),(.65,"up",0),(1.5,"down",1),(2.,"down",0),(2.75,"up",0),(3.5,"down",0)],
 [(0.,"down",0),(.75,"up",0),(1.25,"down",0),(2.,"down",0),(2.5,"up",1),(3.25,"up",0)],
 [(0.,"down",0),(.5,"up",1),(1.5,"down",0),(2.25,"up",0),(3.,"down",0),(3.55,"up",0)],
 [(0.,"down",0),(.70,"up",0),(1.45,"down",0),(2.,"down",1),(2.85,"up",0),(3.45,"down",0)],
]
def strum_bar(bar0,local,final_rake=False):
 chord=HARMONY[bar0]; energy=ENERGY["bridge"]-.02*(local//4); out=[]; patt=STRUM[local%4]
 for i,(off,direction,muted) in enumerate(patt):
  sid=f"b{bar0+1:02d}-s{i}"; cfg=strum_cfg(sid,direction,i,energy,bool(muted),bool(final_rake and i==len(patt)-1))
  for n,(m,s,f) in enumerate(VOICINGS[chord]):
   perf={"string":s,"fret":f,"right_hand":{"method":"pick","pluck_position":.116 if direction=="down" else .138,"attack_angle_deg":cfg["attack_angle_deg"],"strength":cfg["entry_strength"]},"strum":deepcopy(cfg)}
   if muted: perf["left_hand"]={"technique":"dead_note"}
   out.append({"id":f"{sid}n{n}","type":"note","start_beat":bar0*4+off,"duration_beats":.16 if muted else .52,"midi":m,"velocity":min(.94,energy+(.08 if i in {0,3} else -.05)),"instrument_performance":perf})
 return out

def harmonic_bar(bar0,local,final=False):
 chord=HARMONY[bar0]; low=LOW[chord]; e=ENERGY["coda" if bar0>=START["coda"] else "prelude"]-.025*local; out=[]
 for i,(off,idx) in enumerate(((0.,0),(1.35,2),(2.45,1))):
  p=low[idx%len(low)]; out.append(note(f"b{bar0+1:02d}-l{i}",bar0*4+off,.85 if i else 1.30,p,e-.03,"thumb" if p[1]>=5 else "finger"))
 hs=[(76,1,12),(71,2,12)]
 for j,p in enumerate(hs[:1 if final else 2]): out.append(note(f"b{bar0+1:02d}-h{j}",bar0*4+.65+1.55*j,.72,p,e+.04,"finger",left={"technique":"natural_harmonic"},pluck=.19))
 return out

def build_events():
 ev=[]
 for l in range(4): ev+=harmonic_bar(l,l)
 for l in range(12):
  b=START["theme"]+l; ev+=finger_bar(b,l,"theme")
 for l in range(12):
  b=START["development"]+l; ev+=finger_bar(b,l,"development")
 for l in range(8):
  b=START["bridge"]+l; ev+=strum_bar(b,l,final_rake=l in {3,7})
 for l in range(12):
  b=START["percussive"]+l; ev+=finger_bar(b,l,"percussive",True)
 for l in range(8):
  b=START["recap"]+l; ev+=finger_bar(b,l,"recap")
 for l in range(3):
  b=START["coda"]+l; ev+=harmonic_bar(b,l,final=l==2)
 b=START["coda"]+3
 ev.append(note("final-bass",b*4,2.35,(40,6,0),.46,"thumb"))
 # One final slow rake, deliberately not a repeated full bridge pattern.
 sid="final-rake"; cfg=strum_cfg(sid,"down",0,.54,False,True)
 for n,(m,s,f) in enumerate(VOICINGS["Em9"]):
  perf={"string":s,"fret":f,"right_hand":{"method":"pick","pluck_position":.12,"attack_angle_deg":cfg["attack_angle_deg"],"strength":cfg["entry_strength"]},"strum":deepcopy(cfg)}
  ev.append({"id":f"{sid}-{n}","type":"note","start_beat":b*4+2.,"duration_beats":1.35,"midi":m,"velocity":.56,"instrument_performance":perf})
 return sorted(ev,key=lambda x:(float(x["start_beat"]),0 if x["type"]=="note" else 1,x["id"]))

def build_song():
 return {"format":"code-composer-song/v1","meta":{"title":"Cedar Rain, Afterlight","global_seed":1919060,"revision":"SOLO-ACOUSTIC-PROD-R0","provenance":INSPIRATION},"transport":{"bpm":BPM,"meter":{"beats_per_bar":4,"beat_unit":4}},"tonal":{"root":"E","scale":"natural_minor"},"sections":[{"id":s,"bars":n,"name":s.replace('_',' ').title()} for s,n in SECTIONS],"instruments":[{"id":"guitar","family":"acoustic_guitar","variant":"steel-string","render_lock":{"preset":PRESET,"preset_version":"1.0.0"}}],"tracks":[{"id":"guitar","function":"solo-acoustic-guitar","instrument":"guitar"}],"materials":[{"id":"through-composed","kind":"motif","intervals":[0],"rhythm":[1]}],"parts":[{"id":f"{s}-part","section":s,"track":"guitar","material":"through-composed"} for s,_ in SECTIONS]}

def build_score(song,sr):
 return {"format":"code-composer-performance-score/v1","source_song":{"format":"code-composer-song/v1","fingerprint":song_fingerprint(song)},"meta":{"title":"Cedar Rain, Afterlight — production solo acoustic"},"tracks":[{"id":"guitar","events":deepcopy(build_events())}],"render":{"sample_rate":sr,"tail_seconds":3.2,"mix":{"tracks":[{"track":"guitar","gain":.43,"pan":0.,"reverb_send":0.}],"music_bus_gain":1.,"room_return_gain":0.,"master_gain":.80}}}

def rms(x):
 x=np.asarray(x,dtype=np.float64); return float(np.sqrt(np.mean(x*x))) if x.size else 0.
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
 return h.hexdigest()
def bar_sigs(events):
 out=[]
 for b in range(TOTAL_BARS):
  row=[]
  for e in events:
   st=float(e["start_beat"])
   if b*4<=st<(b+1)*4:
    if e["type"]=="note":
     p=e["instrument_performance"]; row.append(("n",round(st-b*4,3),e["midi"],round(e["duration_beats"],3),round(e["velocity"],3),p["string"],p["fret"],p["right_hand"]["method"],(p.get("left_hand") or {}).get("technique"),(p.get("strum") or {}).get("direction"),(p.get("strum") or {}).get("state")))
    else: row.append(("a",round(st-b*4,3),e["action"],round(e["parameters"]["strength"],3)))
  out.append(tuple(row))
 return out
def section_rms(audio,sr):
 secbar=4*60./BPM; d={}; cur=0
 for s,n in SECTIONS:
  a=int(round(cur*secbar*sr)); z=int(round((cur+n)*secbar*sr)); d[s]=rms(audio[a:min(z,len(audio))]); cur+=n
 return d
def cut(src,dst,sr,start_bar,bars):
 secbar=4*60./BPM
 with wave.open(str(src),"rb") as w:
  start=int(round(start_bar*secbar*sr)); count=int(round(bars*secbar*sr)); start=min(start,w.getnframes()); w.setpos(start); data=w.readframes(min(count,w.getnframes()-start)); params=w.getparams()
 with wave.open(str(dst),"wb") as o: o.setparams(params); o.writeframes(data)
def qa(events,result,audio,sr):
 realized=result["render_ir"]["tracks"][0]["events"]
 if len(realized)!=len(events): raise SystemExit(f"event authority {len(events)}->{len(realized)}")
 if not np.isfinite(audio).all(): raise SystemExit("non-finite")
 peak=float(np.max(np.abs(audio))); clipped=float(np.mean(np.abs(audio)>=1.)); dur=len(audio)/sr
 if peak>=.98 or clipped: raise SystemExit(f"unsafe peak/clipping {peak}/{clipped}")
 if not 176.0<=dur<=183.5: raise SystemExit(f"duration {dur} not ~3min")
 sig=bar_sigs(events); unique=len(set(sig)); windows=[tuple(sig[i:i+4]) for i in range(TOTAL_BARS-3)]
 if unique<50: raise SystemExit(f"simple repetition gate: {unique}/60 unique bars")
 if len(windows)!=len(set(windows)): raise SystemExit("identical 4-bar block detected")
 notes=[e for e in events if e["type"]=="note"]; acts=[e for e in events if e["type"]=="instrument_action"]
 methods={}; left={}; strum_notes=0; actions={}
 for e in notes:
  p=e["instrument_performance"]; m=p["right_hand"]["method"]; methods[m]=methods.get(m,0)+1
  lh=(p.get("left_hand") or {}).get("technique")
  if lh: left[lh]=left.get(lh,0)+1
  if p.get("strum"): strum_notes+=1
 for e in acts: actions[e["action"]]=actions.get(e["action"],0)+1
 if not {"finger","thumb","nail","pick"}.issubset(methods): raise SystemExit(methods)
 if strum_notes<100 or len(acts)<20: raise SystemExit(f"coverage strum={strum_notes} actions={len(acts)}")
 return {"duration_seconds":dur,"peak":peak,"rms":rms(audio),"clipped_sample_ratio":clipped,"unique_bar_signatures":unique,"identical_four_bar_windows":0,"authored_event_count":len(events),"render_ir_event_count":len(realized),"pitched_note_count":len(notes),"instrument_action_count":len(acts),"right_hand_method_counts":methods,"left_hand_technique_counts":left,"strum_note_count":strum_notes,"action_counts":actions,"section_rms":section_rms(audio,sr)}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--output",required=True); ap.add_argument("--sample-rate",type=int,default=48000); ap.add_argument("--repeat",action="store_true"); args=ap.parse_args()
 out=Path(args.output); out.mkdir(parents=True,exist_ok=True); sr=args.sample_rate
 song=build_song(); events=build_events(); score=build_score(song,sr); wav=out/f"01_cedar_rain_afterlight_{sr//1000}k.wav"
 r=render_song_score_to_files(song,score,wav,plan_path=out/"execution_plan.json",render_ir_path=out/"render_ir.json",resolved_path=out/"resolved_ir.json",analysis_path=out/"audio_analysis.json")
 audio=np.asarray(r["audio"],dtype=np.float64)
 if int(r["sr"])!=sr: raise SystemExit("sample-rate mismatch")
 metrics=qa(events,r,audio,sr); det=None; rsha=None
 if args.repeat:
  rp=out/f"02_cedar_rain_afterlight_{sr//1000}k_repeat.wav"; rr=render_song_score_to_files(song,score,rp); b=np.asarray(rr["audio"],dtype=np.float64); det=bool(np.array_equal(audio,b))
  if not det: raise SystemExit("nondeterministic repeat")
  rsha=sha(rp)
 cur=0; cuts=[]
 for i,(s,n) in enumerate(SECTIONS,1):
  p=out/f"{i+2:02d}_{s}.wav"; cut(wav,p,sr,cur,n); cuts.append(p.name); cur+=n
 report={"schema":"code-composer-production-solo-acoustic/v1","title":song["meta"]["title"],"revision":song["meta"]["revision"],"sample_rate":sr,"bpm":BPM,"bars":TOTAL_BARS,"sections":[{"id":s,"bars":n} for s,n in SECTIONS],"harmonic_path":list(HARMONY),"single_persistent_track":True,"instrument_family":"acoustic_guitar","preset":PRESET,"no_audio_splice":True,"no_other_instrument":True,"automatic_aesthetic_score":False,"human_listening_required":True,"deterministic_exact":det,"main_wav_sha256":sha(wav),"repeat_wav_sha256":rsha,"song_fingerprint":song_fingerprint(song),"performance_score_fingerprint":performance_score_fingerprint(score),"inspiration":INSPIRATION,"section_cut_files":cuts,**metrics}
 (out/"metrics.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 (out/"song.json").write_text(json.dumps(song,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 (out/"performance_score.json").write_text(json.dumps(score,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 (out/"PROVENANCE.md").write_text("# Cedar Rain, Afterlight — provenance\n\nOriginal Code Composer composition for one steel-string acoustic guitar.\n\n## External score consulted\n- Mauro Giuliani — *12 Divertimenti per chitarra, Op.40*\n- IMSLP 2026 typeset by Marieh, marked Creative Commons Zero 1.0\n- Used only for high-level guitar idiom/structure (alternating bass, voice-leading, cadential variation).\n- No melody, bar, chord sequence, voicing sequence, or arrangement passage was copied.\n\n## Render\n- One persistent acoustic-guitar track; no other instrument, samples, audio splice, normalization, EQ, or compressor added by this script.\n",encoding="utf-8")
 print(json.dumps(report,indent=2,ensure_ascii=False))
if __name__=="__main__": main()
