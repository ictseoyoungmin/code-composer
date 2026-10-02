#!/usr/bin/env python3
"""AG09 D5 — one persistent guitar integrating all accepted techniques."""
from __future__ import annotations

import argparse, hashlib, json
from copy import deepcopy
from pathlib import Path
import numpy as np

from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files
from code_composer.execution.performance_score import performance_score_fingerprint

SR=24000; BPM=96; PRESET="acoustic_guitar.steel_stateful_performance"
OPEN={1:64,2:59,3:55,4:50,5:45,6:40}
VOICINGS={
 "Em":[(40,6,0),(47,5,2),(52,4,2),(55,3,0),(59,2,0),(64,1,0)],
 "Cmaj7":[(48,5,3),(52,4,2),(55,3,0),(59,2,0),(64,1,0)],
 "G6":[(43,6,3),(47,5,2),(50,4,0),(55,3,0),(59,2,0),(64,1,0)],
 "D/F#":[(42,6,2),(45,5,0),(50,4,0),(57,3,2),(62,2,3),(66,1,2)],
 "Am7":[(45,5,0),(52,4,2),(55,3,0),(60,2,1),(64,1,0)],
 "B7":[(47,5,2),(54,4,4),(57,3,2),(63,2,4),(66,1,2)],
 "Em/G":[(43,6,3),(47,5,2),(52,4,2),(55,3,0),(59,2,0),(64,1,0)],
}
PCS={"Em":{4,7,11},"Cmaj7":{0,4,7,11},"G6":{2,4,7,11},"D/F#":{2,6,9},"Am7":{0,4,7,9},"B7":{3,6,9,11},"Em/G":{4,7,11}}
BAR_CHORDS=["Em","Cmaj7","G6","D/F#","Em","Cmaj7","Am7","B7","Em","G6","Cmaj7","B7","Em/G","Cmaj7","B7","Em"]
FULL=(0.0,.5,1.0,1.5,2.0,2.5,3.0,3.5); HALF=(0.0,.5,1.0,1.5)


def build_song():
 return {"format":"code-composer-song/v1","meta":{"title":"One Wood, Four Hands","global_seed":1919006,"revision":"AG09-D5-R0"},
  "transport":{"bpm":BPM,"meter":{"beats_per_bar":4,"beat_unit":4}},"tonal":{"root":"E","scale":"natural_minor"},
  "sections":[{"id":"integration","bars":16,"name":"Integrated Acoustic Guitar"}],
  "instruments":[{"id":"guitar","family":"acoustic_guitar","variant":"steel-string","render_lock":{"preset":PRESET,"preset_version":"1.0.0"}}],
  "tracks":[{"id":"guitar","function":"integrated-acoustic-performance","instrument":"guitar"}],
  "materials":[{"id":"flow","kind":"motif","intervals":[0],"rhythm":[1]}],
  "parts":[{"id":"part","section":"integration","track":"guitar","material":"flow"}]}


def _voice(s):
 return "bass" if s>=5 else ("inner" if s>=3 else "treble")

def _player(s):
 return "thumb" if s>=5 else ("index" if s>=3 else ("middle" if s==2 else "ring"))


def _note(eid,start,dur,pitch,technique,gesture,seq,vel):
 midi,s,fret=pitch
 if midi!=OPEN[s]+fret: raise ValueError(f"{eid}: midi/string/fret mismatch")
 if technique=="pick":
  player="pick"; rh={"method":"pick","pluck_position":.12+.006*(seq%4),"attack_angle_deg":36.+3.*(seq%3),"strength":.58+.04*(seq%2)}
 else:
  player=_player(s); rh={"method":"thumb" if player=="thumb" else "finger"}
 return {"id":eid,"type":"note","start_beat":float(start),"duration_beats":float(dur),"midi":int(midi),"velocity":float(vel),
  "instrument_performance":{"string":s,"fret":fret,"right_hand":rh,"arpeggio":{"gesture_id":gesture,"player":player,"voice":_voice(s),"sequence_index":seq}}}


def _pattern(v): return (v[0],v[-1],v[2],v[-2],v[1],v[-1],v[2],v[-2])


def _arp(bar,chord,technique,offsets=FULL,seq0=0,tag="arp"):
 base=bar*4.; pat=_pattern(VOICINGS[chord])
 pat=pat[:4] if len(offsets)==4 and offsets[0]<2 else (pat[4:] if len(offsets)==4 else pat)
 out=[]
 for j,(off,p) in enumerate(zip(offsets,pat)):
  seq=seq0+j; vel=(.67,.56,.49,.54,.61,.58,.48,.53)[seq%8]; dur=(1.28,.78,.72,.66,1.05,.72,.68,.40)[seq%8]
  out.append(_note(f"b{bar+1:02d}-{tag}-{seq}",base+off,dur,p,technique,f"b{bar+1:02d}-{tag}",seq,vel))
 return out


def _stroke_cfg(sid,direction,idx):
 down=direction=="down"; strong=idx in {0,4}; secondary=idx in {2,6}
 return {"stroke_id":sid,"direction":direction,"traversal_ms":31. if down else 24.,"entry_strength":.68 if strong else (.58 if secondary else .50),
  "acceleration":.12 if down else -.08,"pick_depth":.60 if down else .48,"attack_angle_deg":40. if down else 34.,
  "follow_through":.76 if down else .61,"accent_position":.58 if down else .42,"accent_amount":.34 if strong else (.16 if secondary else .06),
  "from_string":6 if down else 1,"to_string":1 if down else 6}


def _strum(bar,chord,indices):
 base=bar*4.; out=[]
 for idx in indices:
  direction="down" if idx%2==0 else "up"; muted=idx in {3,7}; sid=f"b{bar+1:02d}-strum-{idx}"; cfg=_stroke_cfg(sid,direction,idx)
  for n,(midi,s,fret) in enumerate(VOICINGS[chord]):
   perf={"string":s,"fret":fret,"right_hand":{"method":"pick","pluck_position":.115 if direction=="down" else .135,"attack_angle_deg":cfg["attack_angle_deg"],"strength":cfg["entry_strength"]},"strum":{**cfg,"state":"muted" if muted else "sounding"}}
   if muted: perf["left_hand"]={"technique":"dead_note"}
   out.append({"id":f"{sid}n{n}","type":"note","start_beat":base+.5*idx,"duration_beats":.18 if muted else .42,"midi":midi,"velocity":.72 if idx in {0,4} else .52,"instrument_performance":perf})
 return out


def _action(eid,action,start,strength,location=None):
 p={"strength":strength}
 if location is not None: p["location"]=location
 return {"id":eid,"type":"instrument_action","start_beat":float(start),"duration_beats":.08,"action":action,"parameters":p}


def _perc(bar,chord,offsets=FULL):
 out=_arp(bar,chord,"finger",offsets,4 if len(offsets)==4 and offsets[0]>=2 else 0,"perc"); base=bar*4.
 wanted=[]
 if 1.5 in offsets: wanted.append((1.5,"top_slap"))
 if len(offsets)==4 and 2.5 in offsets: wanted.append((2.5,"top_slap"))
 if 3.0 in offsets: wanted.append((3.0,"body_tap"))
 if 3.5 in offsets: wanted.append((3.5,"string_slap"))
 for i,(off,a) in enumerate(wanted):
  loc="soundboard" if a=="top_slap" else ("lower_bout" if a=="body_tap" else None)
  out.append(_action(f"b{bar+1:02d}-action-{i}-{a}",a,base+off,.46+.03*i,loc))
 return out


def build_events():
 ev=[]; tech={}
 for b,chord in enumerate(BAR_CHORDS):
  bar=b+1
  if bar<=3:
   tech[bar]="fingerstyle"; ev+=_arp(b,chord,"finger",tag="finger")
  elif bar==4:
   tech[bar]="fingerstyle->picked"; ev+=_arp(b,chord,"finger",HALF,0,"finger"); ev+=_arp(b,chord,"pick",(2.,2.5,3.,3.5),4,"pick")
  elif bar<=7:
   tech[bar]="picked-arpeggio"; ev+=_arp(b,chord,"pick",tag="pick")
  elif bar==8:
   tech[bar]="picked->strum"; ev+=_arp(b,chord,"pick",HALF,0,"pick"); ev+=_strum(b,chord,(4,5,6,7))
  elif bar<=11:
   tech[bar]="strumming"; ev+=_strum(b,chord,tuple(range(8)))
  elif bar==12:
   tech[bar]="strum->percussive"; ev+=_strum(b,chord,(0,1,2,3)); ev+=_perc(b,chord,(2.,2.5,3.,3.5))
  else:
   tech[bar]="percussive-fingerstyle"; ev+=_perc(b,chord)
 return sorted(ev,key=lambda e:(float(e["start_beat"]),0 if e["type"]=="note" else 1,e["id"])),tech


def harmonic_certificate(events):
 notes=[e for e in events if e["type"]=="note"]; rows=[]
 for b,chord in enumerate(BAR_CHORDS):
  pcs={int(e["midi"])%12 for e in notes if b*4.<=float(e["start_beat"])<(b+1)*4.}
  if not pcs.issubset(PCS[chord]): raise ValueError(f"bar {b+1}: non-chord pitch classes {sorted(pcs-PCS[chord])}")
  rows.append({"bar":b+1,"chord":chord,"pitch_classes":sorted(pcs)})
 return {"valid":True,"bars":rows,"undeclared_non_chord_tone_count":0}


def build_score(song):
 events,_=build_events()
 return {"format":"code-composer-performance-score/v1","source_song":{"format":"code-composer-song/v1","fingerprint":song_fingerprint(song)},"meta":{"title":"One Wood, Four Hands — AG09 D5 R0"},
  "tracks":[{"id":"guitar","events":deepcopy(events)}],"render":{"sample_rate":SR,"tail_seconds":2.6,"mix":{"tracks":[{"track":"guitar","gain":.42,"pan":0.,"reverb_send":0.}],"music_bus_gain":1.,"room_return_gain":0.,"master_gain":.80}}}


def _sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
 return h.hexdigest()

def _rms(x):
 x=np.asarray(x,dtype=np.float64); return float(np.sqrt(np.mean(x*x))) if x.size else 0.


def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--output",required=True); args=ap.parse_args(); out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
 song=build_song(); score=build_score(song); authored,tech=build_events(); harmony=harmonic_certificate(authored)
 a_path=out/"01_one_wood_four_hands_R0.wav"; b_path=out/"02_one_wood_four_hands_R0_repeat.wav"
 ra=render_song_score_to_files(song,score,a_path,plan_path=out/"execution_plan.json",render_ir_path=out/"render_ir.json",resolved_path=out/"resolved_ir.json",analysis_path=out/"audio_analysis.json")
 rb=render_song_score_to_files(song,score,b_path)
 a=np.asarray(ra["audio"],dtype=np.float64); b=np.asarray(rb["audio"],dtype=np.float64); realized=ra["render_ir"]["tracks"][0]["events"]
 if int(ra["sr"])!=SR: raise SystemExit("sample-rate mismatch")
 if not np.array_equal(a,b): raise SystemExit("D5 render is not deterministic")
 if not np.isfinite(a).all(): raise SystemExit("D5 non-finite samples")
 peak=float(np.max(np.abs(a))) if a.size else 0.; clipped=float(np.mean(np.abs(a)>=1.)) if a.size else 0.
 if peak>=.98 or clipped!=0.: raise SystemExit(f"unsafe output peak={peak} clipped={clipped}")
 if len(realized)!=len(authored): raise SystemExit(f"event authority changed {len(authored)}->{len(realized)}")
 an=[e for e in authored if e["type"]=="note"]; rn=[e for e in realized if "midi" in e]; aa=[e for e in authored if e["type"]=="instrument_action"]; ra_actions=[e for e in realized if e.get("event_type")=="instrument_action"]
 if len(an)!=len(rn) or len(aa)!=len(ra_actions): raise SystemExit("note/action authority split changed")
 if [(e["midi"],e["start_beat"],e["duration_beats"]) for e in an] != [(e["midi"],e["start_beat"],e["duration_beats"]) for e in rn]: raise SystemExit("pitched note authority changed")
 report=ra["render_ir"].get("guitar_performance_report",{}); tr=(report.get("tracks") or {}).get("guitar",{}); strokes=tr.get("strum_strokes") or {}; arps=tr.get("arpeggio_gestures") or {}
 actions={"top_slap":0,"body_tap":0,"string_slap":0}
 for e in ra_actions:
  if e["action"] in actions: actions[e["action"]]+=1
 transition={4:"fingerstyle->picked",8:"picked->strum",12:"strum->percussive"}
 if any(tech[k]!=v for k,v in transition.items()): raise SystemExit("transition contract lost")
 onsets={round(float(e["start_beat"]),9) for e in an}; simultaneous=sum(round(float(e["start_beat"]),9) in onsets for e in aa)
 metrics={"schema":"code-composer-ag09-integration-dogfood/v1","title":song["meta"]["title"],"revision":song["meta"]["revision"],"sample_rate":SR,"bpm":BPM,"bars":16,"duration_seconds":len(a)/SR,
  "harmonic_path":BAR_CHORDS,"harmonic_certificate":harmony,"technique_bars":tech,"transition_bars":transition,"authored_event_count":len(authored),"render_ir_event_count":len(realized),"pitched_note_count":len(an),"instrument_action_count":len(aa),"action_counts":actions,"simultaneous_note_action_onsets":simultaneous,"arpeggio_gesture_count":len(arps),"strum_stroke_count":len(strokes),"single_persistent_track":True,"preset":PRESET,"no_audio_splice":True,"no_drum_track_substitution":True,"deterministic":True,"finite":True,"peak":peak,"rms":_rms(a),"clipped_sample_ratio":clipped,"sha256":_sha(a_path),"sha256_repeat":_sha(b_path),"song_fingerprint":song_fingerprint(song),"performance_score_fingerprint":performance_score_fingerprint(score),"automatic_aesthetic_score":False,"human_listening_required":True}
 (out/"song.json").write_text(json.dumps(song,indent=2)+"\n",encoding="utf-8"); (out/"performance_score.json").write_text(json.dumps(score,indent=2)+"\n",encoding="utf-8"); (out/"metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
 (out/"README.md").write_text("# AG09 D5 — One Wood, Four Hands\n\n16 bars / 96 BPM / 24 kHz. One persistent modeled steel-string guitar. Bars 4, 8 and 12 switch techniques inside the bar; this is not an audio splice.\n",encoding="utf-8")
 files=sorted(p for p in out.rglob("*") if p.is_file() and p.name!="SHA256SUMS.txt"); (out/"SHA256SUMS.txt").write_text("".join(f"{_sha(p)}  {p.relative_to(out).as_posix()}\n" for p in files),encoding="utf-8")
 print(json.dumps(metrics,indent=2,sort_keys=True))

if __name__=="__main__": main()
