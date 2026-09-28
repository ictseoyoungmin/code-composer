from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class InstrumentEngineValidationError(ValueError):
    """Engine-local patch validation failure."""


@dataclass(frozen=True)
class EngineCapabilities:
    name: str
    note_rendering: bool = True
    track_rendering: bool = False
    track_post_process: bool = False
    extended_tail: bool = False
    instrument_expression: tuple[str, ...] = ()
    instrument_performance: bool = False
    instrument_actions: bool = False
    mechanics_realization: bool = False


class InstrumentEngine:
    """Narrow deterministic rendering/validation boundary for pitched instruments."""

    name = "base"
    aliases: tuple[str, ...] = ()
    mechanics_realizer: str | None = None

    def render_note(
        self,
        midi: int,
        duration_s: float,
        sr: int,
        patch: dict,
        *,
        velocity: float = 1.0,
        performance: dict | None = None,
    ):
        """Render one authored note event.

        duration_s is the authored gate/excitation duration, not a mandatory
        sample-buffer length. Resonant engines may return samples beyond note-off
        and must report their maximum extra lifetime via tail_seconds(patch) so
        the track timeline is allocated safely. Engines that do not opt in retain
        the historical duration-bounded behavior.
        """
        raise NotImplementedError

    def render_track(
        self,
        events,
        n: int,
        sr: int,
        patch: dict,
        beat_s: float,
        *,
        gain: float = 1.0,
        pan: float = 0.0,
    ):
        """Optional stateful whole-track renderer. Return ``None`` to use note rendering."""
        return None

    def tail_seconds(self, patch: dict) -> float:
        return 0.0

    def post_process_track(
        self,
        stereo,
        sr: int,
        patch: dict,
        events: list[dict] | tuple[dict, ...],
        beat_s: float,
    ):
        return stereo

    def validate_note_performance(self, subject: str, payload: dict | None) -> None:
        """Validate engine-scoped authored note mechanics.

        The canonical Performance Score owns the payload, but only the resolved
        instrument engine may assign meaning to its keys. Engines that do not opt
        in reject the payload instead of silently ignoring musical intent.
        """
        if payload is not None:
            raise InstrumentEngineValidationError(
                f"{subject}: engine {self.name!r} does not support instrument_performance"
            )

    def validate_note_performance_for_patch(
        self, subject: str, payload: dict | None, patch: dict
    ) -> None:
        """Patch-aware note-mechanics validation with backward-compatible default."""
        self.validate_note_performance(subject, payload)

    def validate_action_event(self, subject: str, event: dict) -> None:
        """Validate an authored non-note instrument action.

        Stateful engines may opt in for actions such as future guitar-body taps.
        Unsupported actions are hard errors so the renderer never drops intent.
        """
        raise InstrumentEngineValidationError(
            f"{subject}: engine {self.name!r} does not support instrument_action events"
        )

    def validate_ir_patch(self, subject: str, patch: dict) -> None:
        return None

    def validate_runtime_patch(self, subject: str, patch: dict) -> None:
        self.validate_ir_patch(subject, patch)

    def validate_authoring_patch(self, role: str, patch: dict) -> None:
        self.validate_ir_patch(role, patch)

    def capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(name=self.name)

    def capabilities_for_patch(self, patch: dict) -> EngineCapabilities:
        return self.capabilities()

    def describe(self, patch: dict | None = None) -> dict[str, Any]:
        c = self.capabilities_for_patch(patch) if patch is not None else self.capabilities()
        return {
            "name": c.name,
            "aliases": list(self.aliases),
            "note_rendering": c.note_rendering,
            "track_rendering": c.track_rendering,
            "track_post_process": c.track_post_process,
            "extended_tail": c.extended_tail,
            "instrument_expression": list(c.instrument_expression),
            "instrument_performance": c.instrument_performance,
            "instrument_actions": c.instrument_actions,
            "mechanics_realization": c.mechanics_realization,
            "mechanics_realizer": self.mechanics_realizer,
        }
