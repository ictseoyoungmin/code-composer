import json
from pathlib import Path
from code_composer.resolve import resolve_ir

def run():
    root = Path(__file__).resolve().parents[1]
    ir = json.loads((root/"tests/fixtures/high_level_ir.json").read_text(encoding="utf-8"))
    a = resolve_ir(ir)
    b = resolve_ir(ir)
    assert a == b
    assert all(t["source"]["type"] == "resolved" for t in a["tracks"])
    assert all(len(t["events"]) > 0 for t in a["tracks"])
    print("test_resolve: OK")

if __name__ == "__main__":
    run()


def test_regression():
    run()
