import json
import sys
from pathlib import Path

from ..agent.composition_brief import brief_from_dict
from ..agent.composer_planner import compile_brief, apply_composer_plan, plan_to_dict


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if len(argv) not in (3,4):
        raise SystemExit(
            'usage: python -m code_composer.composer_cli '
            '<seed_ir.json> <composition_brief.json> <output_ir.json> [plan.json]'
        )

    seed_path=Path(argv[0])
    brief_path=Path(argv[1])
    out_ir=Path(argv[2])
    plan_path=Path(argv[3]) if len(argv)==4 else out_ir.with_name(out_ir.stem+'_plan.json')

    seed=json.loads(seed_path.read_text(encoding='utf-8'))
    brief=brief_from_dict(json.loads(brief_path.read_text(encoding='utf-8')))
    plan=compile_brief(seed,brief)
    planned=apply_composer_plan(seed,plan)

    out_ir.parent.mkdir(parents=True,exist_ok=True)
    plan_path.parent.mkdir(parents=True,exist_ok=True)
    out_ir.write_text(json.dumps(planned,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    plan_path.write_text(json.dumps(plan_to_dict(plan),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    print(json.dumps({
        'output_ir':str(out_ir),
        'plan':str(plan_path),
        'brief':str(brief_path),
        'bpm':planned['transport']['bpm'],
        'tonal':planned['tonal'],
        'source':'agent_authored_composition_brief',
    },ensure_ascii=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
