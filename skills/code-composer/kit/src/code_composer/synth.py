"""Compatibility shim. New code should import the domain module directly."""
from .audio.synth import adsr, equal_power_pan, synth_note

__all__ = ['adsr', 'equal_power_pan', 'synth_note']
