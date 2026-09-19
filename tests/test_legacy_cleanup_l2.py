import importlib.util
import json
from pathlib import Path
from _paths import SOURCE_ROOT

import pytest

from code_composer.analysis.transition_material_analysis import analyze_transition_material
from code_composer.pipeline.validation import validate_ir
from code_composer.core.ir import IRValidationError


ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("module",[
    "code_composer.composition.transition_material",
    "code_composer.composition.pre_hook_build",
    "code_composer.mix.transition_automation",
    "code_composer.composition.section_calibration",
    "code_composer.transition_material",
    "code_composer.pre_hook_build",
    "code_composer.transition_automation",
    "code_composer.section_calibration",
])
def test_superseded_analyzer_driven_mutation_modules_are_absent(module):
    assert importlib.util.find_spec(module) is None


@pytest.mark.parametrize("field",[
    "transition_analysis",
    "transition_material",
    "pre_hook_build",
    "pre_hook_analysis",
])
def test_removed_runtime_control_fields_are_rejected(field):
    ir=json.loads((ROOT/"examples/basic/demo_ir.json").read_text())
    ir[field]={}
    with pytest.raises(IRValidationError,match="removed analyzer-driven mutation"):
        validate_ir(ir)


def test_arranger_no_longer_contains_legacy_analysis_to_music_branch():
    text=(SOURCE_ROOT/"composition/arrange.py").read_text()
    for token in (
        "generate_transition_material",
        "add_pre_hook_build_material",
        'ir.get("transition_analysis")',
        'ir.get("pre_hook_build")',
        'ir.get("pre_hook_analysis")',
    ):
        assert token not in text


def test_transition_material_analysis_is_retained_for_canonical_e5_provenance():
    resolved=json.loads((
        ROOT/"examples/v1.16/final_closure/B_rhythm_centered/resolved_after.json"
    ).read_text())
    report=analyze_transition_material(resolved)
    assert report["total_events"]>0
    assert report["by_type"]["pickup"]>0
    assert report["by_type"]["harmonic_anticipation"]>0
    assert report["by_type"]["bass_approach"]>0
    assert report["by_type"]["rhythm_fill"]>0


def test_flat_transition_material_analysis_compatibility_surface_remains():
    from code_composer.transition_material_analysis import analyze_transition_material as flat
    assert flat is analyze_transition_material
