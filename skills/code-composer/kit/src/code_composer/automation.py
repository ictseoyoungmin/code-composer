"""Compatibility shim. New code should import the domain module directly."""
from .mix.automation import evaluate_lane, compile_automation, value_at_beat

__all__ = ['evaluate_lane', 'compile_automation', 'value_at_beat']
