"""Compatibility shim. New code should import the domain module directly."""
from .core.theory import NOTE_TO_PC, SCALES, midi_to_hz, scale_pitch_classes, quantize_to_scale, scale_degree_to_midi, triad_from_degree, nearest_inversion, voice_leading_cost

__all__ = ['NOTE_TO_PC', 'SCALES', 'midi_to_hz', 'scale_pitch_classes', 'quantize_to_scale', 'scale_degree_to_midi', 'triad_from_degree', 'nearest_inversion', 'voice_leading_cost']
