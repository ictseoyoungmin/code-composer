from typing import Any

from .constraints import validate_hard_constraints_dict, HardConstraintError

REQUIRED_TOP_LEVEL = {
    "meta", "transport", "tonal", "form",
    "materials", "instruments", "tracks", "mix"
}

class IRValidationError(ValueError):
    pass

def _require(cond: bool, message: str):
    if not cond:
        raise IRValidationError(message)

def validate_ir(ir: dict[str, Any]) -> None:
    missing = REQUIRED_TOP_LEVEL - set(ir.keys())
    if missing:
        raise IRValidationError(f"Missing IR fields: {sorted(missing)}")

    meta = ir["meta"]
    transport = ir["transport"]
    tonal = ir["tonal"]
    materials = ir["materials"]

    if "hard_constraints" in ir:
        try:
            validate_hard_constraints_dict(ir["hard_constraints"])
        except HardConstraintError as exc:
            raise IRValidationError(str(exc)) from exc

    _require(isinstance(meta.get("global_seed"), int), "meta.global_seed must be int")
    _require(transport.get("bpm", 0) > 0, "transport.bpm must be > 0")
    _require(transport.get("beats_per_bar", 0) > 0, "transport.beats_per_bar must be > 0")
    _require(isinstance(tonal.get("root"), str), "tonal.root must be string")
    _require(isinstance(tonal.get("scale"), str), "tonal.scale must be string")

    for key in ("motifs", "progressions", "rhythms"):
        _require(key in materials, f"materials.{key} missing")
        _require(isinstance(materials[key], dict), f"materials.{key} must be object")

    for motif_id, motif in materials["motifs"].items():
        _require("intervals" in motif, f"motif {motif_id} missing intervals")
        _require("rhythm" in motif, f"motif {motif_id} missing rhythm")
        _require(len(motif["intervals"]) == len(motif["rhythm"]),
                 f"motif {motif_id}: intervals/rhythm length mismatch")
        _require(all(x > 0 for x in motif["rhythm"]),
                 f"motif {motif_id}: rhythm durations must be > 0")

    for prog_id, prog in materials["progressions"].items():
        _require("degrees" in prog and prog["degrees"], f"progression {prog_id} missing degrees")

    instruments = ir["instruments"]
    _require(isinstance(instruments, dict) and instruments, "instruments must be non-empty object")

    from ..audio.engines import validate_ir_patch, InstrumentEngineValidationError
    for inst_id, inst in instruments.items():
        if inst.get("kind") == "percussion":
            continue
        try:
            validate_ir_patch(inst_id, inst)
        except InstrumentEngineValidationError as exc:
            raise IRValidationError(str(exc)) from exc

    arrangement = ir.get("arrangement")
    if arrangement is not None:
        _require("roles" in arrangement, "arrangement.roles missing")
        _require("motif" in arrangement, "arrangement.motif missing")
        _require(arrangement["motif"] in materials["motifs"],
                 f"arrangement motif {arrangement['motif']} missing")


    for track in ir["tracks"]:
        tid = track.get("id", "<unknown>")
        _require(track.get("instrument") in instruments,
                 f"track {tid} refers to unknown instrument {track.get('instrument')}")
        source = track.get("source", {})
        source_type = source.get("type")
        _require(source_type in {"motif", "phrase", "chords", "bass", "resolved"},
                 f"track {tid} has unsupported source.type {source_type}")

        if source_type in {"motif", "phrase"}:
            _require(source.get("motif") in materials["motifs"],
                     f"track {tid}: unknown motif {source.get('motif')}")
        elif source_type in {"chords", "bass"}:
            _require(source.get("progression") in materials["progressions"],
                     f"track {tid}: unknown progression {source.get('progression')}")
        elif source_type == "resolved":
            for ev in track.get("events", []):
                _require(ev["duration_beats"] > 0, "event.duration_beats must be > 0")
