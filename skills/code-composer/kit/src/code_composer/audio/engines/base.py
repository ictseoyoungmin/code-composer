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


class InstrumentEngine:
    """Narrow deterministic rendering/validation boundary for pitched instruments."""

    name = "base"
    aliases: tuple[str, ...] = ()

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

    def validate_ir_patch(self, subject: str, patch: dict) -> None:
        return None

    def validate_runtime_patch(self, subject: str, patch: dict) -> None:
        self.validate_ir_patch(subject, patch)

    def validate_authoring_patch(self, role: str, patch: dict) -> None:
        self.validate_ir_patch(role, patch)

    def capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(name=self.name)

    def describe(self) -> dict[str, Any]:
        c = self.capabilities()
        return {
            "name": c.name,
            "aliases": list(self.aliases),
            "note_rendering": c.note_rendering,
            "track_rendering": c.track_rendering,
            "track_post_process": c.track_post_process,
            "extended_tail": c.extended_tail,
            "instrument_expression": list(c.instrument_expression),
        }
