#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
import argparse, hashlib, json, wave
from pathlib import Path
import numpy as np

from code_composer.audio.instrument import synth_patch_note
from code_composer.core.song import song_fingerprint
from code_composer.execution import (
    compile_performance_score_to_render_ir,
    lower_song_to_execution_plan,
    realize_instrument_mechanics,
)
from code_composer.presets import materialize_preset
from code_composer.render import render


ROOT=Path(__file__).resolve().parents[1]
CASE=ROOT/"examples/cr08/silk_afterimage"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def _write_wav(path,audio,sr):
    audio=np.asarray(audio,dtype=np.float64)
    if audio.ndim==1:
        audio=np.stack([audio,audio],axis=1)
    pcm=(np.clip(audio,-1.0,1.0)*32767).astype(np.int16)
    with wave.open(str(path),"wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(int(sr)); w.writeframes(pcm.tobytes())


def _rms(x):
    x=np.asarray(x,dtype=np.float64)
    return float(np.sqrt(np.mean(x*x))) if x.size else 0.0


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)

    song=_load(CASE/"song.json")
    score=_load(CASE/"performance_score.json")
    fp=song_fingerprint(song)
    if score["source_song"]["fingerprint"]!=fp:
        raise SystemExit("Performance Score fingerprint does not bind Song")

    plan=lower_song_to_execution_plan(song)
    ir=realize_instrument_mechanics(compile_performance_score_to_render_ir(plan,score),plan)

    resonant_ir=deepcopy(ir)
    gate_cut_ir=deepcopy(ir)
    zither_patch=gate_cut_ir["instruments"]["zither"]
    if zither_patch.get("engine")!="resonant_pluck":
        raise SystemExit("CR08 dogfood did not resolve resonant_pluck engine")
    zither_patch["resonant_pluck_graph"]["natural_tail_s"]=0.0

    after,sr,_=render(resonant_ir,out/"phrase_resonant.wav")
    before,sr0,_=render(gate_cut_ir,out/"phrase_gate_cut.wav")
    if sr!=24000 or sr0!=24000:
        raise SystemExit("CR08 dogfood must render at 24 kHz")
    if not np.isfinite(after).all() or not np.isfinite(before).all():
        raise SystemExit("non-finite audio")
    if float(np.mean(np.abs(after)>=1.0))!=0.0 or float(np.mean(np.abs(before)>=1.0))!=0.0:
        raise SystemExit("clipping")

    patch=materialize_preset("resonant_pluck.zither_bright",role="cr08-probe")
    probe_gate=.18
    probe_after=synth_patch_note(66,probe_gate,24000,patch,velocity=.70)
    cut=deepcopy(patch); cut["resonant_pluck_graph"]["natural_tail_s"]=0.0
    probe_before=synth_patch_note(66,probe_gate,24000,cut,velocity=.70)
    padded=np.zeros_like(probe_after); padded[:len(probe_before)]=probe_before
    _write_wav(out/"probe_gate_cut.wav",padded,24000)
    _write_wav(out/"probe_resonant.wav",probe_after,24000)

    start=int(probe_gate*24000)
    early=probe_after[start:start+int(.20*24000)]
    late=probe_after[start+int(.45*24000):start+int(.62*24000)]
    before_early=padded[start:start+int(.20*24000)]
    evidence={
        "schema":"code-composer-cr08-resonant-release-dogfood/v1",
        "title":song["meta"]["title"],
        "song_fingerprint":fp,
        "source_problem_evidence":{
            "uploaded_before_after_ir_sha256":"2fc42e79fa75e7a9b72ce51348f48554bb90615e6f34e87833fdf47a73d2f508",
            "authored_ir_changed":False,
            "old_renderer_extra_tail_seconds":.12,
            "sustain_fix_tail_range_seconds":[.42,.85],
            "assessment":"audible fix existed only in piece-specific renderer code"
        },
        "contract":{
            "authored_gate_separate_from_resonator_lifetime":True,
            "song_specific_ornament_tail_table":False,
            "legacy_engines_modified":False,
            "engine":"resonant_pluck",
            "preset":"resonant_pluck.zither_bright",
            "engine_tail_seconds":float(patch["resonant_pluck_graph"]["natural_tail_s"])
        },
        "probe":{
            "gate_seconds":probe_gate,
            "gate_cut_samples":int(len(probe_before)),
            "resonant_samples":int(len(probe_after)),
            "post_gate_rms_gate_cut":_rms(before_early),
            "post_gate_rms_resonant":_rms(early),
            "late_tail_rms_resonant":_rms(late)
        },
        "phrase":{
            "sample_rate":sr,
            "gate_cut_seconds":round(len(before)/sr,6),
            "resonant_seconds":round(len(after)/sr,6),
            "gate_cut_peak":float(np.max(np.abs(before))),
            "resonant_peak":float(np.max(np.abs(after))),
            "gate_cut_clipped_sample_ratio":float(np.mean(np.abs(before)>=1.0)),
            "resonant_clipped_sample_ratio":float(np.mean(np.abs(after)>=1.0))
        },
        "perceptual_gate":{"required":True,"status":"PENDING","automatic_aesthetic_score":False}
    }
    if evidence["probe"]["post_gate_rms_resonant"] <= evidence["probe"]["post_gate_rms_gate_cut"]+.001:
        raise SystemExit("resonant probe did not preserve post-gate energy")
    if evidence["probe"]["late_tail_rms_resonant"] >= evidence["probe"]["post_gate_rms_resonant"]*.70:
        raise SystemExit("resonant tail did not decay")

    (out/"evidence.json").write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8")
    (out/"song.json").write_text(json.dumps(song,indent=2)+"\n",encoding="utf-8")
    (out/"performance_score.json").write_text(json.dumps(score,indent=2)+"\n",encoding="utf-8")
    files=sorted(p for p in out.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt")
    (out/"SHA256SUMS.txt").write_text("".join(f"{_sha(p)}  {p.name}\n" for p in files),encoding="utf-8")
    print(json.dumps(evidence,sort_keys=True))


if __name__=="__main__":
    main()
