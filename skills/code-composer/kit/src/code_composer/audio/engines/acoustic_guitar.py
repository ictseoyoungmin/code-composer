from __future__ import annotations

from .base import EngineCapabilities, InstrumentEngine, InstrumentEngineValidationError


def _num(value, name, lo, hi):
    try:
        x = float(value)
    except Exception as exc:
        raise InstrumentEngineValidationError(f"{name} must be numeric") from exc
    if not lo <= x <= hi:
        raise InstrumentEngineValidationError(f"{name} outside [{lo},{hi}]")
    return x


class AcousticGuitarEngine(InstrumentEngine):
    """AG00 acoustic-guitar engine boundary.

    AG01+ owns physical-fidelity expansion. Instrument-scoped note mechanics and
    action events remain intentionally unsupported until their dedicated slices.
    """

    name = "acoustic_guitar"
    aliases = ("steel_string_guitar", "acoustic-guitar")

    def render_note(self, midi, duration_s, sr, patch, *, velocity=1.0, performance=None):
        from ..acoustic_guitar import render_acoustic_guitar_note
        return render_acoustic_guitar_note(
            midi, duration_s, sr, patch, velocity=velocity, performance=performance
        )

    def tail_seconds(self, patch):
        graph = patch.get("acoustic_guitar_graph", {}) if isinstance(patch, dict) else {}
        return max(0.0, float(graph.get("natural_tail_s", 0.45)))

    def _validate(self, subject, patch):
        if not isinstance(patch, dict):
            raise InstrumentEngineValidationError(f"{subject}: patch must be object")
        if patch.get("kind") not in {"acoustic_guitar", None}:
            raise InstrumentEngineValidationError(f"{subject}: acoustic-guitar patch kind must be acoustic_guitar")
        graph = patch.get("acoustic_guitar_graph")
        if not isinstance(graph, dict):
            raise InstrumentEngineValidationError(f"{subject}: acoustic_guitar_graph must be an object")
        for key, lo, hi in (
            ("max_partials", 1, 32),
            ("pluck_position", 0.03, 0.49),
            ("partial_rolloff", 0.5, 3.0),
            ("base_decay_s", 0.05, 6.0),
            ("frequency_damping", 0.0, 2.0),
            ("natural_tail_s", 0.0, 4.0),
            ("post_gate_decay_s", 0.015, 3.0),
            ("attack_s", 0.0003, 0.2),
            ("pluck_noise_gain", 0.0, 0.25),
            ("pluck_noise_decay_s", 0.002, 0.2),
            ("end_fade_s", 0.002, 0.2),
            ("output_gain", 0.0, 2.0),
        ):
            if key in graph:
                value = _num(graph[key], f"{subject}.acoustic_guitar.{key}", lo, hi)
                if key == "max_partials" and int(value) != value:
                    raise InstrumentEngineValidationError(
                        f"{subject}.acoustic_guitar.max_partials must be integer"
                    )
        if "seed" in graph and not isinstance(graph["seed"], int):
            raise InstrumentEngineValidationError(f"{subject}.acoustic_guitar.seed must be integer")

    def validate_ir_patch(self, subject, patch): self._validate(subject, patch)
    def validate_runtime_patch(self, subject, patch): self._validate(subject, patch)
    def validate_authoring_patch(self, role, patch): self._validate(role, patch)

    def capabilities(self):
        return EngineCapabilities(name=self.name, extended_tail=True)


__all__ = ["AcousticGuitarEngine"]
