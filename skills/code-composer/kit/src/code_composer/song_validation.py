"""Aggregate CR01 Song validation that may inspect the installed render runtime."""
from __future__ import annotations

from .audio.engines import registered_engines
from .core.song import SongValidationError, validate_song
from .presets import PresetError, get_preset


class SongRuntimeValidationError(SongValidationError):
    pass


def validate_song_for_runtime(song: dict) -> None:
    """Validate authored Song structure plus explicitly locked render resources.

    No renderer is selected when render_lock is absent. This function only checks
    resources the author explicitly locked.
    """
    validate_song(song)
    engines = set(registered_engines())

    for instrument in song["instruments"]:
        lock = instrument.get("render_lock")
        if not lock:
            continue
        subject = f"instruments.{instrument['id']}.render_lock"
        engine = lock.get("engine")
        if engine is not None and engine not in engines:
            raise SongRuntimeValidationError(
                f"{subject}.engine: unknown engine {engine!r}; available={sorted(engines)}"
            )

        preset_id = lock.get("preset")
        preset = None
        if preset_id is not None:
            try:
                preset = get_preset(preset_id, lock.get("preset_version"))
            except PresetError as exc:
                raise SongRuntimeValidationError(f"{subject}.preset: {exc}") from exc

        if preset is not None and engine is not None and preset.get("engine") != engine:
            raise SongRuntimeValidationError(
                f"{subject}: engine {engine!r} conflicts with preset engine {preset.get('engine')!r}"
            )


__all__ = [
    "SongRuntimeValidationError",
    "validate_song_for_runtime",
]
