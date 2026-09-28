import numpy as np

from code_composer.audio.acoustic_guitar import render_acoustic_guitar_note
from code_composer.audio.engines import engine_for_patch
from code_composer.presets import materialize_preset


PITCHES = (40, 52, 64)  # E2, E3, E4
VELOCITIES = (0.35, 0.65, 0.92)


def _baseline(**overrides):
    return materialize_preset(
        "acoustic_guitar.steel_single_string_baseline",
        version="1.0.0",
        patch_overrides={"acoustic_guitar_graph": overrides} if overrides else None,
    )


def test_ag01_baseline_and_foundation_remain_distinct_available_paths():
    foundation = materialize_preset("acoustic_guitar.steel_foundation", version="1.0.0")
    baseline = _baseline()
    assert foundation["acoustic_guitar_graph"].get("physical_model") is None
    assert baseline["acoustic_guitar_graph"]["physical_model"] == "ag01_modal_bridge_body_v1"
    assert engine_for_patch(baseline).name == "acoustic_guitar"


def test_ag01_baseline_is_deterministic_across_e2_e4_and_velocities():
    patch = _baseline()
    for midi in PITCHES:
        for velocity in VELOCITIES:
            a = render_acoustic_guitar_note(
                midi, 0.45, 24000, patch, velocity=velocity
            )
            b = render_acoustic_guitar_note(
                midi, 0.45, 24000, patch, velocity=velocity
            )
            assert a.shape == b.shape
            assert np.array_equal(a, b)
            assert np.isfinite(a).all()
            assert float(np.max(np.abs(a))) > 0.0
            assert float(np.max(np.abs(a))) <= 1.0


def test_ag01_gate_is_not_resonator_lifetime():
    patch = _baseline()
    audio = render_acoustic_guitar_note(52, 0.20, 24000, patch, velocity=0.70)
    expected_min = int((0.20 + 2.0) * 24000)
    assert len(audio) >= expected_min
    tail = audio[int(0.20 * 24000):]
    assert float(np.sqrt(np.mean(tail * tail))) > 1e-5


def test_ag01_baseline_is_not_the_ag00_foundation_signal():
    foundation = materialize_preset("acoustic_guitar.steel_foundation", version="1.0.0")
    baseline = _baseline()
    a = render_acoustic_guitar_note(52, 0.45, 24000, foundation, velocity=0.65)
    b = render_acoustic_guitar_note(52, 0.45, 24000, baseline, velocity=0.65)
    n = min(len(a), len(b))
    assert not np.allclose(a[:n], b[:n], rtol=0.0, atol=1e-10)


def test_ag01_body_stage_is_causally_audible_not_metadata_only():
    full = _baseline()
    no_body = _baseline(body_modal_mix=0.0, air_mode_mix=0.0)
    a = render_acoustic_guitar_note(52, 0.45, 24000, full, velocity=0.65)
    b = render_acoustic_guitar_note(52, 0.45, 24000, no_body, velocity=0.65)
    assert a.shape == b.shape
    delta = float(np.sqrt(np.mean((a - b) ** 2)))
    assert delta > 1e-4


def test_ag01_patch_level_fret_contact_changes_decay_without_claiming_ag02_authority():
    open_diag = _baseline(fret_contact=0.0)
    fretted_diag = _baseline(fret_contact=0.72)
    a = render_acoustic_guitar_note(52, 0.45, 24000, open_diag, velocity=0.65)
    b = render_acoustic_guitar_note(52, 0.45, 24000, fretted_diag, velocity=0.65)
    assert a.shape == b.shape
    assert not np.allclose(a, b, rtol=0.0, atol=1e-10)


def test_ag01_velocity_increases_rms_for_same_note():
    patch = _baseline()
    rms = []
    for velocity in VELOCITIES:
        audio = render_acoustic_guitar_note(52, 0.45, 24000, patch, velocity=velocity)
        rms.append(float(np.sqrt(np.mean(audio * audio))))
    assert rms[0] < rms[1] < rms[2]


def test_ag01_e2_e4_level_does_not_collapse_with_pitch():
    patch = _baseline()
    rms = []
    for midi in PITCHES:
        audio = render_acoustic_guitar_note(52 if midi == 52 else midi, 0.45, 24000, patch, velocity=0.65)
        rms.append(float(np.sqrt(np.mean(audio * audio))))
    assert max(rms) / min(rms) < 1.35
