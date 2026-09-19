"""Compatibility shim. New code should import the domain module directly."""
from .analysis.phrase_analysis import analyze_phrase

__all__ = ['analyze_phrase']
