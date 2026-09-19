"""Backward-compatible pitched-instrument facade.

Normal rendering resolves an engine through ``audio.engines``. Low-level generic DSP
lives in ``audio.generic_synth`` so the registry does not depend back on this facade.
"""


def synth_patch_note(midi: int, duration_s: float, sr: int, patch: dict, velocity: float = 1.0, performance: dict | None = None):
    from .engines import engine_for_patch
    return engine_for_patch(patch).render_note(
        midi, duration_s, sr, patch, velocity=velocity, performance=performance
    )


def render_generic_note(midi: int, duration_s: float, sr: int, patch: dict, velocity: float = 1.0, performance: dict | None = None):
    from .generic_synth import render_generic_note as _render
    return _render(midi, duration_s, sr, patch, velocity=velocity, performance=performance)


__all__ = ["synth_patch_note", "render_generic_note"]
