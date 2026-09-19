from __future__ import annotations
import argparse, json
from ..presets import list_presets, get_preset, materialize_preset, PresetError

def main(argv=None):
    p=argparse.ArgumentParser(prog="code-composer-presets")
    sub=p.add_subparsers(dest="cmd",required=True)
    q=sub.add_parser("list"); q.add_argument("--engine"); q.add_argument("--family"); q.add_argument("--role")
    q=sub.add_parser("show"); q.add_argument("preset_id"); q.add_argument("--version")
    q=sub.add_parser("materialize"); q.add_argument("preset_id"); q.add_argument("--version"); q.add_argument("--overrides"); q.add_argument("--role",default="lead")
    a=p.parse_args(argv)
    try:
        if a.cmd=="list": out=list_presets(engine=a.engine,family=a.family,role=a.role)
        elif a.cmd=="show":
            out=get_preset(a.preset_id,a.version); out.pop("patch",None)
        else:
            overrides=json.loads(a.overrides) if a.overrides else None
            out=materialize_preset(a.preset_id,version=a.version,patch_overrides=overrides,role=a.role)
    except (PresetError,json.JSONDecodeError) as exc:
        p.error(str(exc))
    print(json.dumps(out,indent=2,ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())
