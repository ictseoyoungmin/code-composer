from pathlib import Path
REPO_ROOT=Path(__file__).resolve().parents[1]
SKILL_ROOT=REPO_ROOT/"skills"/"code-composer"
KIT_ROOT=SKILL_ROOT/"kit"
SOURCE_ROOT=KIT_ROOT/"src"/"code_composer"
SCHEMA_ROOT=KIT_ROOT/"schemas"
PACKAGED_SCHEMA_ROOT=SOURCE_ROOT/"reference"/"schemas"
