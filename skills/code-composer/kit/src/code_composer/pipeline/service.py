import json
from pathlib import Path

from ..render import render
from ..analysis.analysis import analyze_audio
from ..analysis.section_analysis import analyze_sections
from ..analysis.register_analysis import analyze_register_collisions
from ..analysis.expressive_qa import analyze_expressive_qa

def render_to_files(ir: dict, wav_path, resolved_path=None, analysis_path=None):
    wav_path = Path(wav_path)
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    audio, sr, resolved = render(ir, str(wav_path))
    metrics = analyze_audio(audio, sr)
    analysis = analyze_sections(audio, sr, resolved) if analysis_path is not None else None
    if analysis is not None and resolved.get("performance_ir"):
        analysis["register_collisions"] = analyze_register_collisions(resolved)
        analysis["expressive_qa"] = analyze_expressive_qa(resolved, analysis)
        for issue in analysis["expressive_qa"].get("issues",[]):
            tagged=dict(issue)
            tagged.setdefault("source","expressive_qa")
            analysis["issues"].append(tagged)
    if resolved_path is not None:
        Path(resolved_path).write_text(json.dumps(resolved, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    if analysis_path is not None:
        Path(analysis_path).write_text(json.dumps(analysis, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return {"audio":audio, "sr":sr, "resolved":resolved, "analysis":analysis, "metrics":metrics, "wav_path":wav_path}

def render_state(ir: dict, workdir: Path, stem: str):
    workdir=Path(workdir); workdir.mkdir(parents=True, exist_ok=True)
    ir_path=workdir/f"{stem}.json"
    wav_path=workdir/f"{stem}.wav"
    resolved_path=workdir/f"{stem}_resolved.json"
    analysis_path=workdir/f"{stem}_analysis.json"
    ir_path.write_text(json.dumps(ir, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    result=render_to_files(ir,wav_path,resolved_path,analysis_path)
    return {"ir":ir,"ir_path":ir_path,"wav_path":wav_path,"resolved_path":resolved_path,"analysis_path":analysis_path,"resolved":result["resolved"],"analysis":result["analysis"],"metrics":result["metrics"]}
