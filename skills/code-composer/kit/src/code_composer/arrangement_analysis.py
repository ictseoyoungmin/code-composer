"""Compatibility shim. New code should import the domain module directly."""
from .analysis.arrangement_analysis import analyze_arrangement, section_contrast_score

__all__ = ['analyze_arrangement', 'section_contrast_score']
