"""Acoustic-guitar synthesis package.

AG00 establishes the engine/package boundary only. AG01 owns steel-string fidelity.
"""
from .render import render_acoustic_guitar_note

__all__ = ["render_acoustic_guitar_note"]
