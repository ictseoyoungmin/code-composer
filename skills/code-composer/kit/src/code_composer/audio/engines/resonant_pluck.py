from __future__ import annotations

from .base import EngineCapabilities, InstrumentEngine, InstrumentEngineValidationError


def _num(v, name, lo, hi):
    try:
        x = float(v)
    except Exception as exc:
        raise InstrumentEngineValidationError(f"{name} must be numeric") from exc
    if not lo <= x <= hi:
        raise InstrumentEngineValidationError(f"{name} outside [{lo},{hi}]")
    return x


class ResonantPluckEngine(InstrumentEngine):
    name = "resonant_pluck"
    aliases = ("plucked_zither", "resonant-pluck")

    def render_note(self, midi, duration_s, sr, patch, *, velocity=1.0, performance=None):
        from ..resonant_pluck import render_resonant_pluck_note
        return render_resonant_pluck_note(
            midi, duration_s, sr, patch, velocity=velocity, performance=performance
        )

    def tail_seconds(self, patch):
        graph = patch.get("resonant_pluck_graph", {}) if isinstance(patch, dict) else {}
        return max(0.0, float(graph.get("natural_tail_s", .70)))

    def _validate(self, subject, patch):
        if not isinstance(patch, dict):
            raise InstrumentEngineValidationError(f"instrument {subject}: patch must be object")
        graph = patch.get("resonant_pluck_graph")
        if not isinstance(graph, dict):
            raise InstrumentEngineValidationError(
                f"instrument {subject}: resonant_pluck_graph must be object"
            )
        for key, lo, hi in (
            ("max_partials", 1, 32),
            ("pluck_position", .03, .49),
            ("partial_rolloff", .25, 3.0),
            ("inharmonicity", 0, .004),
            ("base_decay_s", .03, 8.0),
            ("frequency_damping", 0, 2.0),
            ("natural_tail_s", 0, 4.0),
            ("post_gate_decay_s", .015, 3.0),
            ("end_fade_s", .002, .2),
            ("attack_s", .0003, .2),
            ("pluck_noise_gain", 0, .25),
            ("pluck_noise_lowpass_hz", 200, 18000),
            ("pluck_noise_decay_s", .002, .2),
            ("body_mix", 0, 1),
            ("lowpass_hz", 200, 18000),
            ("drive", .05, 5.0),
            ("output_gain", 0, 2.0),
            ("stereo_width", 0, .75),
        ):
            if key in graph:
                value = _num(graph[key], f"{subject}.resonant_pluck.{key}", lo, hi)
                if key == "max_partials" and int(value) != value:
                    raise InstrumentEngineValidationError(
                        f"{subject}.resonant_pluck.max_partials must be integer"
                    )

        freqs = graph.get("body_resonances_hz", [])
        gains = graph.get("body_gains", [])
        decays = graph.get("body_decay_s", [])
        for name, values in (
            ("body_resonances_hz", freqs),
            ("body_gains", gains),
            ("body_decay_s", decays),
        ):
            if not isinstance(values, list) or len(values) > 8:
                raise InstrumentEngineValidationError(
                    f"{subject}.resonant_pluck.{name} must be array of at most 8 values"
                )
        if not (len(freqs) == len(gains) == len(decays)):
            raise InstrumentEngineValidationError(
                f"{subject}.resonant_pluck body mode arrays must have equal length"
            )
        for i, value in enumerate(freqs):
            _num(value, f"{subject}.resonant_pluck.body_resonances_hz[{i}]", 20, 18000)
        for i, value in enumerate(gains):
            _num(value, f"{subject}.resonant_pluck.body_gains[{i}]", 0, .5)
        for i, value in enumerate(decays):
            _num(value, f"{subject}.resonant_pluck.body_decay_s[{i}]", .01, 4.0)

    def validate_ir_patch(self, subject, patch):
        self._validate(subject, patch)

    def validate_authoring_patch(self, role, patch):
        self._validate(role, patch)

    def capabilities(self):
        return EngineCapabilities(
            name=self.name,
            extended_tail=True,
            instrument_expression=(
                "pitch_start_cents",
                "pitch_end_cents",
                "pitch_time_s",
                "vibrato_depth_cents",
                "vibrato_rate_hz",
                "vibrato_onset_s",
                "vibrato_fade_s",
                "release_damping",
            ),
        )
