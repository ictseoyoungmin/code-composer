"""Compatibility shim. New code should import the domain module directly."""
from .analysis.section_analysis import EPS, analyze_sections, diagnose

__all__ = ['EPS', 'analyze_sections', 'diagnose']
