import json
import sys
from pathlib import Path

from ..core.song import song_summary
from ..song_validation import validate_song_for_runtime


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2 or argv[0] != "validate":
        raise SystemExit("usage: code-composer-song validate <song.json>")

    path = Path(argv[1])
    song = json.loads(path.read_text(encoding="utf-8"))
    validate_song_for_runtime(song)

    out = song_summary(song)
    out["path"] = str(path)
    out["valid"] = True
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
