import json
import sys
from pathlib import Path

from ..core.song import song_summary
from ..execution import execution_plan_fingerprint, lower_song_to_execution_plan
from ..song_validation import validate_song_for_runtime


def _validate(path: Path) -> dict:
    song = json.loads(path.read_text(encoding="utf-8"))
    validate_song_for_runtime(song)
    out = song_summary(song)
    out["path"] = str(path)
    out["valid"] = True
    return out


def _lower(song_path: Path, plan_path: Path) -> dict:
    song = json.loads(song_path.read_text(encoding="utf-8"))
    plan = lower_song_to_execution_plan(song)
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "source_song": str(song_path),
        "execution_plan": str(plan_path),
        "source_fingerprint": plan["source_song"]["fingerprint"],
        "plan_fingerprint": execution_plan_fingerprint(plan),
        "sections": len(plan["sections"]),
        "instruments": len(plan["instruments"]),
        "tracks": len(plan["tracks"]),
        "part_instances": len(plan["part_instances"]),
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) == 2 and argv[0] == "validate":
        out = _validate(Path(argv[1]))
    elif len(argv) == 3 and argv[0] == "lower":
        out = _lower(Path(argv[1]), Path(argv[2]))
    else:
        raise SystemExit(
            "usage: code-composer-song validate <song.json>\n"
            "   or: code-composer-song lower <song.json> <execution-plan.json>"
        )

    print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
