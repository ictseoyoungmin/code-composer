import json
from pathlib import Path
from code_composer.app.composer_cli import main


def test_composer_cli_consumes_brief_json(tmp_path):
    root=Path(__file__).resolve().parents[1]
    seed=root/'tests/fixtures/topline_ir.json'
    brief=root/'tests/fixtures/composition_brief.json'
    out=tmp_path/'planned.json'
    plan=tmp_path/'plan.json'
    rc=main([str(seed),str(brief),str(out),str(plan)])
    assert rc==0
    ir=json.loads(out.read_text())
    p=json.loads(plan.read_text())
    assert ir['transport']['bpm']==90
    assert p['brief']['concept'].startswith('restrained night-road')
    assert ir['composer_plan']['source']=='agent_authored_composition_brief'
