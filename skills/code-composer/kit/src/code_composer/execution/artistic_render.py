"""CR03 end-to-end artistic render path for Composer-first Song + Performance Score."""
from __future__ import annotations

import json
from pathlib import Path

from ..pipeline.service import render_to_files
from .lowering import lower_song_to_execution_plan
from .performance_score import performance_score_fingerprint
from .plan import execution_plan_fingerprint
from .render_bridge import (
    compile_performance_score_to_render_ir,
    realize_instrument_mechanics,
)


def render_song_score_to_files(
    song: dict,
    score: dict,
    wav_path,
    *,
    plan_path=None,
    render_ir_path=None,
    resolved_path=None,
    analysis_path=None,
):
    plan = lower_song_to_execution_plan(song)
    render_ir = compile_performance_score_to_render_ir(plan, score)
    realized_ir = realize_instrument_mechanics(render_ir, plan)

    if plan_path is not None:
        Path(plan_path).write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if render_ir_path is not None:
        Path(render_ir_path).write_text(
            json.dumps(realized_ir, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    result = render_to_files(
        realized_ir,
        wav_path,
        resolved_path=resolved_path,
        analysis_path=analysis_path,
    )
    return {
        **result,
        "plan": plan,
        "render_ir": realized_ir,
        "execution_plan_fingerprint": execution_plan_fingerprint(plan),
        "performance_score_fingerprint": performance_score_fingerprint(score),
        "violin_performance_report": realized_ir.get("violin_performance_report"),
    }


__all__ = ["render_song_score_to_files"]
