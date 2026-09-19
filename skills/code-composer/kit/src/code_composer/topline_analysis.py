"""Compatibility shim. New code should import the domain module directly."""
from .analysis.topline_analysis import analyze_topline_space, topline_space_score

__all__ = ['analyze_topline_space', 'topline_space_score']
