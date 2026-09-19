"""Compatibility shim. New code should import the domain module directly."""
from .analysis.transition_material_analysis import analyze_transition_material

__all__ = ['analyze_transition_material']
