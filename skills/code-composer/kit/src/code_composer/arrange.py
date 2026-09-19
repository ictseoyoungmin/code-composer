"""Compatibility shim. New code should import the domain module directly."""
from .composition.arrange import arrange_ir

__all__ = ['arrange_ir']
