from __future__ import annotations
from pathlib import Path
import json, re, sys

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "kit"

FORBIDDEN_AUDIO = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
FORBIDDEN_PARENT = re.compile(r"\.\./")
FORBIDDEN_CANONICAL_DIRS = {"build", "dist"}

def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    raise SystemExit(1)

def main() -> int:
    if ROOT.name != "code-composer": fail("skill directory must be named code-composer")
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for name in sorted(FORBIDDEN_CANONICAL_DIRS):
        if (KIT / name).exists():
            fail(f"transient build directory inside canonical skill: kit/{name}")
    egg_info = [p for p in KIT.rglob("*.egg-info") if p.is_dir()]
    if egg_info:
        fail(f"package metadata inside canonical skill: {egg_info[0].relative_to(ROOT)}")
    if "name: code-composer" not in skill: fail("SKILL.md name mismatch")
    for p in ROOT.rglob("*"):
        if not p.is_file(): continue
        rel = p.relative_to(ROOT)
        if p.suffix.lower() in FORBIDDEN_AUDIO: fail(f"audio artifact inside skill: {rel}")
        if p.suffix.lower() == ".mid": fail(f"MIDI artifact inside skill: {rel}")
        if p.suffix.lower() in {".md", ".json", ".toml", ".py", ".txt"}:
            text = p.read_text(encoding="utf-8", errors="ignore")
            if FORBIDDEN_PARENT.search(text): fail(f"parent-directory reference in {rel}")
    catalog = json.loads((KIT / "presets/CATALOG.json").read_text())
    if catalog.get("policy") != "presets provide sonic capability, not musical content":
        fail("factory preset catalog policy mismatch")
    for meta in catalog.get("presets", []):
        if "patch" in meta: fail("agent-facing preset catalog must not expose raw patch values")
        if meta.get("musical_content") is not False: fail("factory preset must declare musical_content=false")
    forbidden_music_keys = {"notes","note_events","events","melody","motif","motifs","rhythm","rhythms","chords","progression","progressions","arrangement","form","sections","midi"}
    def scan_preset(value, label):
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key).lower() in forbidden_music_keys: fail(f"musical content key in factory preset {label}: {key}")
                scan_preset(child, label)
        elif isinstance(value, list):
            for child in value: scan_preset(child, label)
    for preset_file in (KIT / "src/code_composer/reference/presets").glob("*.json"):
        data=json.loads(preset_file.read_text())
        if data.get("musical_content") is not False: fail(f"factory preset not marked non-musical: {preset_file.name}")
        scan_preset(data, preset_file.name)

    manifest = json.loads((KIT / "fixtures/fixture-manifest.json").read_text())
    for name, meta in manifest.items():
        if not (meta.get("synthetic") is True and meta.get("musical_reference") is False):
            fail(f"fixture not declared synthetic/non-reference: {name}")
        if int(meta.get("event_count", 999)) > 8: fail(f"fixture too musically rich: {name}")
    print("PASS: standalone skill structure and musical-content firewall")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
