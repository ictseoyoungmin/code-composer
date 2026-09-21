import hashlib

import numpy as np
import pytest

from code_composer.audio.engines import engine_for_patch
from code_composer.drum_analysis import analyze_drum_hit
from code_composer.export.midi import _midi_note_for_event
from code_composer.percussion import render_drum_event, supported_articulations
from code_composer.presets import PresetError, materialize_preset

SR = 24000


def _preset():
    return materialize_preset("drums.acoustic_kit_modeled", role="drums")


def _hash(x):
    return hashlib.sha256(x.tobytes()).hexdigest()


def _norm(x):
    return x / (float(np.sqrt(np.mean(x * x))) + 1e-12)


def test_s20_factory_preset_exposes_explicit_articulation_foundation():
    patch = _preset()
    block = patch["drum_graph"]["articulation_foundation"]
    assert block["enabled"] is True
    assert supported_articulations() == {
        "kick": ("default",),
        "snare": ("center", "ghost", "rimshot", "cross_stick"),
        "hat": ("closed", "half_open", "open", "pedal", "choke"),
        "ride": ("bow", "bell", "choke"),
        "crash": ("crash", "choke"),
        "tom_high": ("center", "edge"),
        "tom_mid": ("center", "edge"),
        "tom_floor": ("center", "edge"),
    }
    assert engine_for_patch(patch).tail_seconds(patch) >= 2.25


def test_s20_existing_modeled_kick_snare_closed_hat_are_byte_identical_to_s19():
    patch = _preset()
    expected = {
        "kick": "380e698edfe82884757e23a81f8318a61d973968ba8c4c11e8a99d450a034df6",
        "snare": "aaf1e8e3e15d2e64d746a6d635716a0db3e71c122a25c86cc79ae8382686ecaf",
        "hat": "7b6b0613fdbc8af958d7a1c57f0faeb3c3693ec2ca0f5c1d7b168b23e06cd558",
    }
    for kind in ("kick", "snare", "hat"):
        implicit = render_drum_event(kind, .1, SR, .8, seed=17, patch=patch)
        explicit = render_drum_event(
            kind, .1, SR, .8, seed=17, patch=patch,
            articulation={"kick": "default", "snare": "center", "hat": "closed"}[kind],
        )
        assert _hash(implicit) == expected[kind]
        assert np.array_equal(implicit, explicit)


def test_s20_snare_articulations_are_deterministic_and_acoustically_distinct():
    patch = _preset()
    arts = ("center", "ghost", "rimshot", "cross_stick")
    rendered = {}
    for art in arts:
        a = render_drum_event("snare", .08, SR, .78, seed=29, patch=patch, articulation=art)
        b = render_drum_event("snare", .08, SR, .78, seed=29, patch=patch, articulation=art)
        assert np.array_equal(a, b)
        assert float(np.max(np.abs(a))) < 1.0
        rendered[art] = a
    assert analyze_drum_hit(rendered["ghost"], SR)["decay_time_s"] < analyze_drum_hit(rendered["center"], SR)["decay_time_s"]
    assert float(np.mean(np.abs(_norm(rendered["rimshot"])[:3000] - _norm(rendered["cross_stick"])[:3000]))) > .18


def test_s20_hat_closed_half_open_open_have_ordered_decay():
    patch = _preset()
    values = {}
    for art in ("closed", "half_open", "open"):
        y = render_drum_event("hat", .06, SR, .76, seed=31, patch=patch, articulation=art)
        values[art] = analyze_drum_hit(y, SR)["decay_time_s"]
    assert values["closed"] < values["half_open"] < values["open"]
    assert values["open"] > .8


def test_s20_hat_pedal_and_choke_are_short_explicit_contact_articulations():
    patch = _preset()
    pedal = render_drum_event("hat", .05, SR, .72, seed=7, patch=patch, articulation="pedal")
    choke = render_drum_event("hat", .05, SR, .72, seed=7, patch=patch, articulation="choke")
    pa, ch = analyze_drum_hit(pedal, SR), analyze_drum_hit(choke, SR)
    assert pa["decay_time_s"] < .10
    assert ch["decay_time_s"] < .08
    assert not np.array_equal(pedal[:len(choke)], choke)


def test_s20_ride_bell_is_brighter_and_more_focused_than_ride_bow():
    patch = _preset()
    bow = render_drum_event("ride", .08, SR, .80, seed=19, patch=patch, articulation="bow")
    bell = render_drum_event("ride", .08, SR, .80, seed=19, patch=patch, articulation="bell")
    a, b = analyze_drum_hit(bow, SR), analyze_drum_hit(bell, SR)
    assert b["centroid_hz"] > a["centroid_hz"] + 500
    assert b["decay_time_s"] < a["decay_time_s"]


def test_s20_crash_has_long_wash_and_explicit_short_choke_contact():
    patch = _preset()
    crash = render_drum_event("crash", .08, SR, .86, seed=23, patch=patch, articulation="crash")
    choke = render_drum_event("crash", .08, SR, .86, seed=23, patch=patch, articulation="choke")
    a, b = analyze_drum_hit(crash, SR), analyze_drum_hit(choke, SR)
    assert a["decay_time_s"] > 1.5
    assert b["decay_time_s"] < .10
    assert a["air_ratio_7k_16k"] > .20


def test_s20_tom_family_is_tuned_high_to_mid_to_floor_and_edge_changes_mode_balance():
    patch = _preset()
    centers = {}
    for kind in ("tom_high", "tom_mid", "tom_floor"):
        center = render_drum_event(kind, .10, SR, .82, seed=13, patch=patch, articulation="center")
        edge = render_drum_event(kind, .10, SR, .82, seed=13, patch=patch, articulation="edge")
        centers[kind] = analyze_drum_hit(center, SR)["centroid_hz"]
        assert analyze_drum_hit(edge, SR)["centroid_hz"] > centers[kind] * 1.12
    assert centers["tom_high"] > centers["tom_mid"] > centers["tom_floor"]


def test_s20_articulation_aliases_are_canonical_and_invalid_values_fail_loudly():
    patch = _preset()
    a = render_drum_event("hat", .06, SR, .7, seed=5, patch=patch, articulation="half-open")
    b = render_drum_event("hat", .06, SR, .7, seed=5, patch=patch, articulation="half_open")
    assert np.array_equal(a, b)
    with pytest.raises(ValueError):
        render_drum_event("snare", .06, SR, .7, seed=5, patch=patch, articulation="brush_sweep")


def test_s20_midi_export_maps_new_kit_elements_and_key_articulations():
    assert _midi_note_for_event({"event_type":"drum","drum":"hat","articulation":"pedal"}) == 44
    assert _midi_note_for_event({"event_type":"drum","drum":"hat","articulation":"open"}) == 46
    assert _midi_note_for_event({"event_type":"drum","drum":"snare","articulation":"cross_stick"}) == 37
    assert _midi_note_for_event({"event_type":"drum","drum":"ride","articulation":"bell"}) == 53
    assert _midi_note_for_event({"event_type":"drum","drum":"crash"}) == 49
    assert _midi_note_for_event({"event_type":"drum","drum":"tom_floor"}) == 43


def test_s20_articulation_patch_validation_rejects_unbounded_open_hat_tail():
    with pytest.raises(PresetError):
        materialize_preset(
            "drums.acoustic_kit_modeled",
            role="drums",
            patch_overrides={"drum_graph":{"articulation_foundation":{"hat_open_tail_s":9.0}}},
        )
