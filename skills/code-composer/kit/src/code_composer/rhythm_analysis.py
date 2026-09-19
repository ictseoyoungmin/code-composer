"""Compatibility shim. New code should import the domain module directly."""
from .analysis.rhythm_analysis import analyze_rhythm, rhythmic_contrast

__all__ = ['analyze_rhythm', 'rhythmic_contrast']
