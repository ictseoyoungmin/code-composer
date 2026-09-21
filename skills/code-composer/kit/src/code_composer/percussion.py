"""Compatibility shim. New code should import the domain module directly."""
from .audio.percussion import kick, snare, hat, render_drum_event

__all__ = ['kick', 'snare', 'hat', 'render_drum_event']
