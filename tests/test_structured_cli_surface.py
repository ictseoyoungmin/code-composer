import json
from pathlib import Path
import pytest

from code_composer.ir import validate_ir
from code_composer.mix.mixer import MixGraphError

def run():
    root=Path(__file__).resolve().parents[1]
    ir=json.loads((root/"tests/fixtures/mix_ir.json").read_text(encoding="utf-8"))
    validate_ir(ir)
    bad=json.loads(json.dumps(ir))
    bad["mix"]["graph"]["buses"]["music"]["kind"]="invalid"
    try:
        validate_ir(bad)
    except MixGraphError:
        pass
    else:
        raise AssertionError("legacy validate_ir must still validate mix graph")

def test_regression():
    run()

if __name__=="__main__":
    run()
