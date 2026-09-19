"""Compatibility shim. New code should import the domain module directly."""
from .composition.phrase import PhraseConfig, motif_identity_score, compose_phrase

__all__ = ['PhraseConfig', 'motif_identity_score', 'compose_phrase']
