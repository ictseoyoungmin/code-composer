"""Compatibility shim. New code should import the domain module directly."""
from .composition.topline import ToplineConfig, resolve_topline

__all__ = ['ToplineConfig', 'resolve_topline']
