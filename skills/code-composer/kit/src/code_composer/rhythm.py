"""Compatibility shim. New code should import the domain module directly."""
from .composition.rhythm import GrooveConfig, generate_rhythm_events, coupled_bass_pattern

__all__ = ['GrooveConfig', 'generate_rhythm_events', 'coupled_bass_pattern']
