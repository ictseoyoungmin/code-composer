"""Compatibility shim. New code should import the domain module directly."""
from .analysis.timbre_analysis import mono, onset_click_score, high_band_ratio, spectral_flatness, harmonic_concentration

__all__ = ['mono', 'onset_click_score', 'high_band_ratio', 'spectral_flatness', 'harmonic_concentration']
