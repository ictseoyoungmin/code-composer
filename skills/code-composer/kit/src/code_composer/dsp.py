"""Compatibility shim. New code should import the domain module directly."""
from .audio.dsp import stereo_delay, delay_wet, simple_reverb, reverb_wet, one_pole_lowpass, one_pole_highpass, apply_pan, compressor, duck, soft_limit

__all__ = ['stereo_delay', 'delay_wet', 'simple_reverb', 'reverb_wet', 'one_pole_lowpass', 'one_pole_highpass', 'apply_pan', 'compressor', 'duck', 'soft_limit']
