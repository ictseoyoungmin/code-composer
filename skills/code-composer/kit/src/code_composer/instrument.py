"""Compatibility shim. New code should import the domain module directly."""
from .audio.instrument import synth_patch_note

__all__ = ['synth_patch_note']
