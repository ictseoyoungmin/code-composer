"""Compatibility shim. New code should import the domain module directly."""
from .analysis.instrument_analysis import spectral_centroid, stereo_width, waveform_rms, compare_patches

__all__ = ['spectral_centroid', 'stereo_width', 'waveform_rms', 'compare_patches']
