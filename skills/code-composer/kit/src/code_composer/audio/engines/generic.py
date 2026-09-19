from __future__ import annotations

from .base import EngineCapabilities, InstrumentEngine, InstrumentEngineValidationError

WAVEFORMS = {"sine", "saw", "square", "triangle"}
FILTER_TYPES = {"none", "lowpass", "highpass", "bandpass"}
WAVESHAPERS = {"none", "tanh", "softclip"}


def _num(v, name, lo, hi):
    try:
        x = float(v)
    except Exception as exc:
        raise InstrumentEngineValidationError(f"{name} must be numeric") from exc
    if not (lo <= x <= hi):
        raise InstrumentEngineValidationError(f"{name} outside [{lo},{hi}]")
    return x


class GenericSynthEngine(InstrumentEngine):
    name = "generic"
    aliases = ("synth", "graph")

    def render_note(self, midi, duration_s, sr, patch, *, velocity=1.0, performance=None):
        from ..generic_synth import render_generic_note
        return render_generic_note(
            midi, duration_s, sr, patch, velocity=velocity, performance=performance
        )

    def validate_ir_patch(self, subject, patch):
        if not isinstance(patch, dict):
            raise InstrumentEngineValidationError(f"instrument {subject}: patch must be object")
        # Legacy pre-v0.6 tonal instruments remain readable. New authoring is stricter.
        if "graph" not in patch:
            return
        graph = patch["graph"]
        oscillators = graph.get("oscillators")
        if not isinstance(oscillators, list) or not oscillators:
            raise InstrumentEngineValidationError(
                f"instrument {subject}: oscillators must be non-empty list"
            )
        for osc in oscillators:
            if osc.get("waveform", "sine") not in WAVEFORMS:
                raise InstrumentEngineValidationError(
                    f"instrument {subject}: unsupported waveform"
                )
        env = graph.get("envelope", {})
        for key in ("attack", "decay", "release"):
            if key in env and float(env[key]) < 0:
                raise InstrumentEngineValidationError(
                    f"instrument {subject}: {key} must be >= 0"
                )
        if "sustain" in env and not (0 <= float(env["sustain"]) <= 1):
            raise InstrumentEngineValidationError(
                f"instrument {subject}: sustain must be in [0,1]"
            )
        breath = graph.get("breath", {})
        if breath:
            if float(breath.get("gain", 0.0)) < 0:
                raise InstrumentEngineValidationError(
                    f"instrument {subject}: breath.gain must be >= 0"
                )
            if float(breath.get("low_cutoff", 0.0)) >= float(breath.get("high_cutoff", 1e9)):
                raise InstrumentEngineValidationError(
                    f"instrument {subject}: breath low_cutoff must be < high_cutoff"
                )
        pitch_env = graph.get("pitch_envelope", {})
        if pitch_env and "time_s" in pitch_env and float(pitch_env["time_s"]) < 0:
            raise InstrumentEngineValidationError(
                f"instrument {subject}: pitch_envelope.time_s must be >= 0"
            )
        attack_partial = graph.get("attack_partial", {})
        if attack_partial and float(attack_partial.get("gain", 0.0)) < 0:
            raise InstrumentEngineValidationError(
                f"instrument {subject}: attack_partial.gain must be >= 0"
            )
        declick = graph.get("declick", {})
        if declick and "ms" in declick and float(declick["ms"]) < 0:
            raise InstrumentEngineValidationError(
                f"instrument {subject}: declick.ms must be >= 0"
            )

    def validate_authoring_patch(self, role, patch):
        if not isinstance(patch, dict):
            raise InstrumentEngineValidationError(
                f"sound_palette.{role}.patch must be an object"
            )
        graph = patch.get("graph", patch)
        if not isinstance(graph, dict):
            raise InstrumentEngineValidationError(
                f"sound_palette.{role}.patch.graph must be an object"
            )
        oscillators = graph.get("oscillators", [])
        if not isinstance(oscillators, list) or not (1 <= len(oscillators) <= 6):
            raise InstrumentEngineValidationError(
                f"{role}: oscillators must contain 1..6 entries"
            )
        for i, osc in enumerate(oscillators):
            if not isinstance(osc, dict):
                raise InstrumentEngineValidationError(f"{role}: oscillator {i} must be an object")
            wave = osc.get("waveform", "sine")
            if wave not in WAVEFORMS:
                raise InstrumentEngineValidationError(f"{role}: unsupported waveform {wave}")
            _num(osc.get("gain", 1.0), f"{role}.oscillators[{i}].gain", 0.0, 2.0)
            _num(osc.get("octave", 0), f"{role}.oscillators[{i}].octave", -3, 3)
            _num(osc.get("semitone", 0), f"{role}.oscillators[{i}].semitone", -24, 24)
            _num(osc.get("detune_cents", 0), f"{role}.oscillators[{i}].detune_cents", -120, 120)
        unison = graph.get("unison", {})
        if unison:
            voices = int(_num(unison.get("voices", 1), f"{role}.unison.voices", 1, 7))
            if voices != float(unison.get("voices", 1)):
                raise InstrumentEngineValidationError(f"{role}.unison.voices must be an integer")
            _num(unison.get("detune_cents", 0), f"{role}.unison.detune_cents", 0, 40)
            _num(unison.get("stereo_width", 0), f"{role}.unison.stereo_width", 0, 1)
        env = graph.get("envelope", {})
        if env:
            _num(env.get("attack", .01), f"{role}.envelope.attack", 0, 5)
            _num(env.get("decay", .08), f"{role}.envelope.decay", 0, 5)
            _num(env.get("sustain", .65), f"{role}.envelope.sustain", 0, 1)
            _num(env.get("release", .18), f"{role}.envelope.release", 0, 8)
        filt = graph.get("filter", {})
        if filt:
            ftype = filt.get("type", "lowpass")
            if ftype not in FILTER_TYPES:
                raise InstrumentEngineValidationError(f"{role}: unsupported filter type {ftype}")
            if ftype in {"lowpass", "highpass"}:
                _num(filt.get("cutoff", 18000), f"{role}.filter.cutoff", 20, 20000)
            elif ftype == "bandpass":
                low = _num(filt.get("low_cutoff", 300), f"{role}.filter.low_cutoff", 20, 19000)
                high = _num(filt.get("high_cutoff", 7000), f"{role}.filter.high_cutoff", 30, 20000)
                if low >= high:
                    raise InstrumentEngineValidationError(
                        f"{role}: bandpass low_cutoff must be below high_cutoff"
                    )
            _num(filt.get("env_amount", 0), f"{role}.filter.env_amount", -1, 2)
        lfo = graph.get("lfo", {})
        if lfo:
            _num(lfo.get("rate_hz", 0), f"{role}.lfo.rate_hz", 0, 20)
            _num(lfo.get("pitch_cents", 0), f"{role}.lfo.pitch_cents", 0, 100)
            _num(lfo.get("amp_depth", 0), f"{role}.lfo.amp_depth", 0, 1)
        ws = graph.get("waveshaper", {})
        if ws:
            kind = ws.get("type", "none")
            if kind not in WAVESHAPERS:
                raise InstrumentEngineValidationError(f"{role}: unsupported waveshaper {kind}")
            _num(ws.get("drive", 1.0), f"{role}.waveshaper.drive", .1, 5.0)
        pe = graph.get("pitch_envelope", {})
        if pe:
            _num(pe.get("start_cents", 0), f"{role}.pitch_envelope.start_cents", -1200, 1200)
            _num(pe.get("end_cents", 0), f"{role}.pitch_envelope.end_cents", -1200, 1200)
            _num(pe.get("time_s", .04), f"{role}.pitch_envelope.time_s", .001, 2.0)
        breath = graph.get("breath", {})
        if breath:
            _num(breath.get("gain", 0), f"{role}.breath.gain", 0, .25)
            low = _num(breath.get("low_cutoff", 1400), f"{role}.breath.low_cutoff", 20, 19000)
            high = _num(breath.get("high_cutoff", 6500), f"{role}.breath.high_cutoff", 30, 20000)
            if low >= high:
                raise InstrumentEngineValidationError(
                    f"{role}: breath low_cutoff must be below high_cutoff"
                )
        partial = graph.get("attack_partial", {})
        if partial:
            _num(partial.get("gain", 0), f"{role}.attack_partial.gain", 0, .4)
            _num(partial.get("harmonic", 2), f"{role}.attack_partial.harmonic", 1, 16)
            _num(partial.get("attack_s", .004), f"{role}.attack_partial.attack_s", .0001, 1)
            _num(partial.get("decay_s", .045), f"{role}.attack_partial.decay_s", .0001, 2)
        declick = graph.get("declick", {})
        if declick:
            _num(declick.get("ms", 0), f"{role}.declick.ms", 0, 50)
        _num(graph.get("output_gain", 1.0), f"{role}.output_gain", 0, 2)

    def capabilities(self):
        return EngineCapabilities(name=self.name, instrument_expression=("pitch_start_cents",))
