#!/usr/bin/env python3
"""Section-tail production renderer for Cedar Rain, Afterlight R4."""
from __future__ import annotations

import argparse, hashlib, json
from copy import deepcopy
from pathlib import Path
import numpy as np
from scipy.io import wavfile

from code_composer.core.song import song_fingerprint
from code_composer.execution import render_song_score_to_files
from code_composer.execution.performance_score import performance_score_fingerprint

import compose_cedar_rain_afterlight_r4 as comp


def sha(path: Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def rms(x):
    a=np.asarray(x,dtype=np.float64)
    return float(np.sqrt(np.mean(a*a))) if a.size else 0.0


def master_gain(sr:int):
    return 0.58 if int(sr)>=44100 else 0.80


def song_for(section_id,bars,seed):
    return {
        "format":"code-composer-song/v1",
        "meta":{"title":f"Cedar Rain, Afterlight R4 — {section_id}","global_seed":int(seed),"revision":"SOLO-ACOUSTIC-PROD-R4"},
        "transport":{"bpm":comp.BPM,"meter":{"beats_per_bar":comp.METER_BEATS,"beat_unit":4}},
        "tonal":{"root":"E","scale":"natural_minor"},
        "sections":[{"id":section_id,"bars":int(bars),"name":section_id.title()}],
        "instruments":[{"id":"guitar","family":"acoustic_guitar","variant":"steel-string","render_lock":{"preset":comp.PRESET,"preset_version":"1.0.0"}}],
        "tracks":[{"id":"guitar","function":"solo-acoustic-guitar","instrument":"guitar"}],
        "materials":[{"id":"through-composed","kind":"motif","intervals":[0],"rhythm":[1]}],
        "parts":[{"id":f"{section_id}-part","section":section_id,"track":"guitar","material":"through-composed"}],
    }


def local_events(all_events,start_bar,bars):
    lo=float(start_bar*comp.METER_BEATS)
    hi=float((start_bar+bars)*comp.METER_BEATS)
    out=[]
    for src in all_events:
        st=float(src["start_beat"])
        if lo<=st<hi:
            e=deepcopy(src)
            e["start_beat"]=st-lo
            out.append(e)
    return out


def score_for(song,events,sr):
    return {
        "format":"code-composer-performance-score/v1",
        "source_song":{"format":"code-composer-song/v1","fingerprint":song_fingerprint(song)},
        "meta":{"title":song["meta"]["title"]},
        "tracks":[{"id":"guitar","events":deepcopy(events)}],
        "render":{"sample_rate":int(sr),"tail_seconds":3.2,"mix":{
            "tracks":[{"track":"guitar","gain":0.43,"pan":0.0,"reverb_send":0.0}],
            "music_bus_gain":1.0,"room_return_gain":0.0,"master_gain":master_gain(sr),
        }},
    }


def render_one(out,section_id,bars,start_bar,sr,seed,suffix=""):
    events=local_events(comp.build_events(),start_bar,bars)
    song=song_for(section_id,bars,seed)
    score=score_for(song,events,sr)
    stem=f"section_{start_bar+1:02d}_{section_id}{suffix}"
    wav=out/f"{stem}.wav"
    result=render_song_score_to_files(song,score,wav,plan_path=out/f"{stem}_execution_plan.json",render_ir_path=out/f"{stem}_render_ir.json")
    audio=np.asarray(result["audio"],dtype=np.float64)
    realized=result["render_ir"]["tracks"][0]["events"]
    if int(result["sr"])!=int(sr): raise SystemExit(f"{section_id}: sample-rate mismatch")
    if len(realized)!=len(events): raise SystemExit(f"{section_id}: event authority {len(events)}->{len(realized)}")
    if not np.isfinite(audio).all(): raise SystemExit(f"{section_id}: non-finite")
    peak=float(np.max(np.abs(audio))) if audio.size else 0.0
    clipped=float(np.mean(np.abs(audio)>=1.0)) if audio.size else 0.0
    if peak>=0.98 or clipped!=0.0: raise SystemExit(f"{section_id}: unsafe peak/clipping {peak}/{clipped}")
    return {"id":section_id,"bars":bars,"start_bar":start_bar,"event_count":len(events),"peak":peak,"rms":rms(audio),"audio":audio,"wav":wav,"wav_sha256":sha(wav),"song_fingerprint":song_fingerprint(song),"performance_score_fingerprint":performance_score_fingerprint(score)}


def write_float(path,sr,audio):
    x=np.asarray(audio,dtype=np.float64)
    if not np.isfinite(x).all(): raise SystemExit("master non-finite")
    wavfile.write(path,int(sr),np.asarray(x,dtype=np.float32))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    ap.add_argument("--sample-rate",type=int,default=48000)
    ap.add_argument("--determinism-check",action="store_true")
    args=ap.parse_args()
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    sr=int(args.sample_rate)
    all_events=comp.build_events()
    grammar=comp.validate_musical_grammar(all_events)

    section_results=[]
    start=0
    for idx,(sid,bars) in enumerate(comp.SECTIONS):
        section_results.append(render_one(out,sid,bars,start,sr,1919072+idx))
        start+=bars

    deterministic=None
    if args.determinism_check:
        sid="development"; start=comp.START[sid]; bars=dict(comp.SECTIONS)[sid]
        a=next(r for r in section_results if r["id"]==sid)
        b=render_one(out,sid,bars,start,sr,1919074,suffix="_repeat")
        deterministic=bool(np.array_equal(a["audio"],b["audio"]))
        if not deterministic: raise SystemExit("R4 development nondeterministic")

    beat_s=60.0/comp.BPM
    bar_samples=comp.METER_BEATS*beat_s*sr
    nominal=int(round(comp.TOTAL_BARS*bar_samples))
    final_len=nominal+int(round(3.2*sr))
    master=np.zeros((final_len,2),dtype=np.float64)
    for r in section_results:
        s=int(round(r["start_bar"]*bar_samples)); e=min(final_len,s+len(r["audio"]))
        master[s:e]+=r["audio"][:e-s]

    peak=float(np.max(np.abs(master))) if master.size else 0.0
    clipped=float(np.mean(np.abs(master)>=1.0)) if master.size else 0.0
    if peak>=0.98 or clipped!=0.0: raise SystemExit(f"master unsafe {peak}/{clipped}")
    duration=len(master)/sr
    if not 178.0<=duration<=183.5: raise SystemExit(f"duration outside 3-min target: {duration}")

    master_path=out/f"01_cedar_rain_afterlight_R4_master_{sr//1000}k_float32.wav"
    write_float(master_path,sr,master)
    cut_files=[]; cursor=0
    for i,(sid,bars) in enumerate(comp.SECTIONS,1):
        a=int(round(cursor*bar_samples)); z=int(round((cursor+bars)*bar_samples))
        p=out/f"{i+1:02d}_{sid}.wav"; write_float(p,sr,master[a:z]); cut_files.append(p.name); cursor+=bars

    notes=[e for e in all_events if e["type"]=="note"]
    acts=[e for e in all_events if e["type"]=="instrument_action"]
    methods={}; strum_notes=0; arp_notes=0; action_counts={}
    for e in notes:
        p=e["instrument_performance"]; m=p["right_hand"]["method"]; methods[m]=methods.get(m,0)+1
        if p.get("strum"): strum_notes+=1
        if p.get("arpeggio"): arp_notes+=1
    for e in acts: action_counts[e["action"]]=action_counts.get(e["action"],0)+1

    report={
        "schema":"code-composer-production-solo-acoustic-r4/v1",
        "title":"Cedar Rain, Afterlight",
        "revision":"SOLO-ACOUSTIC-PROD-R4",
        "sample_rate":sr,"bpm":comp.BPM,"meter":"3/4","bars":comp.TOTAL_BARS,
        "duration_seconds":duration,"instrument_family":"acoustic_guitar","preset":comp.PRESET,"other_instruments":0,
        "section_tail_overlap_only":True,"post_normalization":False,"post_eq":False,"post_compression":False,"synthetic_reverb":False,
        "fixed_master_gain":master_gain(sr),"peak":peak,"rms":rms(master),"clipped_sample_ratio":clipped,
        "authored_event_count":len(all_events),"pitched_note_count":len(notes),"instrument_action_count":len(acts),
        "right_hand_method_counts":methods,"strum_note_count":strum_notes,"arpeggio_note_count":arp_notes,"action_counts":action_counts,
        "musical_grammar":grammar,
        "sections":[{k:v for k,v in r.items() if k not in {"audio","wav"}} for r in section_results],
        "deterministic_exact":deterministic,
        "master_wav_sha256":sha(master_path),
        "harmonic_path":list(comp.HARMONY),"inspiration":comp.INSPIRATION,"listening_cuts":cut_files,
        "human_listening_required":True,"automatic_aesthetic_score":False,
    }
    (out/"metrics.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (out/"PROVENANCE.md").write_text(
        "# Cedar Rain, Afterlight R4 — provenance\n\n"
        "R4 is an original Code Composer solo steel-string acoustic-guitar composition.\n\n"
        "## Score-informed rewrite\n"
        "- Mauro Giuliani, Studio per la Chitarra, Op.1 (1812), public-domain score.\n"
        "- Mauro Giuliani, 12 Divertimenti per chitarra, Op.40 (1813); IMSLP 2026 Marieh typeset marked CC0.\n"
        "- Consulted concepts only: metrical bass+melody coordination, alternating bass under sustained melody, selective p-i-m-a-m-i arpeggiation, phrase/cadence density, and idiomatic right-hand distribution.\n"
        "- No source melody, bar, harmony sequence, voicing sequence, or arrangement passage is copied.\n\n"
        "## Production\n"
        "- Same Code Composer v1.19 stateful steel-string engine for every audible event.\n"
        "- No samples, other instruments, normalization, EQ, compression, resampling, or synthetic reverb.\n",
        encoding="utf-8",
    )
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=="__main__": main()
