from __future__ import annotations

from .base import EngineCapabilities, InstrumentEngine, InstrumentEngineValidationError


def _num(v,name,lo,hi):
    try: x=float(v)
    except Exception as exc: raise InstrumentEngineValidationError(f"{name} must be numeric") from exc
    if not lo<=x<=hi: raise InstrumentEngineValidationError(f"{name} outside [{lo},{hi}]")
    return x


class PluckedBassEngine(InstrumentEngine):
    name="plucked_bass"
    aliases=("bass_string",)

    def render_note(self,midi,duration_s,sr,patch,*,velocity=1.0,performance=None):
        from ..plucked_bass import render_plucked_bass_note
        return render_plucked_bass_note(midi,duration_s,sr,patch,velocity=velocity,performance=performance)

    def _validate(self,subject,patch):
        if not isinstance(patch,dict):
            raise InstrumentEngineValidationError(f"instrument {subject}: patch must be object")
        g=patch.get("plucked_bass_graph",{})
        if not isinstance(g,dict):
            raise InstrumentEngineValidationError(f"instrument {subject}: plucked_bass_graph must be object")
        if "max_partials" in g:
            x=_num(g["max_partials"],f"{subject}.plucked_bass.max_partials",1,48)
            if int(x)!=x: raise InstrumentEngineValidationError(f"{subject}.plucked_bass.max_partials must be integer")
        for k,lo,hi in (
            ("pluck_position",.03,.49),("pickup_position",.03,.49),("partial_rolloff",.45,3.0),
            ("inharmonicity",0,.003),("base_decay_s",.05,8.0),("frequency_damping",0,2.0),
            ("damping_power",.2,3.0),("decay_keytrack",-.05,.08),("attack_s",.0002,.2),
            ("release_s",.002,1.0),("finger_noise_gain",0,.15),("finger_noise_low_hz",20,10000),
            ("finger_noise_high_hz",50,18000),("finger_noise_decay_s",.002,.25),
            ("finger_noise_attack_s",.0001,.05),("highpass_hz",10,500),("pickup_lowpass_hz",200,18000),
            ("drive",.05,5.0),("output_gain",0,2.0),("stereo_width",0,.25),("side_highpass_hz",100,8000),
        ):
            if k in g: _num(g[k],f"{subject}.plucked_bass.{k}",lo,hi)
        if float(g.get("finger_noise_low_hz",550))>=float(g.get("finger_noise_high_hz",4200)):
            raise InstrumentEngineValidationError(f"{subject}.plucked_bass finger-noise low cutoff must be below high cutoff")
        if float(g.get("highpass_hz",24))>=float(g.get("pickup_lowpass_hz",4200)):
            raise InstrumentEngineValidationError(f"{subject}.plucked_bass highpass must be below pickup_lowpass")

    def validate_ir_patch(self,subject,patch): self._validate(subject,patch)
    def validate_authoring_patch(self,role,patch): self._validate(role,patch)

    def capabilities(self):
        return EngineCapabilities(
            name=self.name,
            instrument_expression=("pitch_start_cents","pitch_end_cents","pitch_time_s","attack_scale","release_scale"),
        )
