# ============================================================
# WISEMARKET — CENTRAL PATH / SETTINGS
# ============================================================
# Single source of truth for filesystem paths.
#
# Repo root resolution order:
#   1. env var WISEMARKET_ROOT (if set and exists)
#   2. auto-detected: three levels up from this file
#      (backend/config/settings.py -> backend/config -> backend -> <root>)
#
# Import these instead of hardcoding absolute paths.
# ============================================================
import os
from pathlib import Path


def _detect_root() -> Path:
    env_root = os.environ.get("WISEMARKET_ROOT")
    if env_root:
        p = Path(env_root).expanduser().resolve()
        if p.exists():
            return p
    # backend/config/settings.py -> parents[2] == repo root
    return Path(__file__).resolve().parents[2]


ROOT_DIR: Path = _detect_root()
DATA_DIR: Path = ROOT_DIR / "data"
ONTOLOGY_DIR: Path = DATA_DIR / "ontology"
ENV_FILE: Path = ROOT_DIR / ".env"

# String forms for APIs that don't accept Path
ROOT_DIR_STR: str = str(ROOT_DIR)
DATA_DIR_STR: str = str(DATA_DIR)
ONTOLOGY_DIR_STR: str = str(ONTOLOGY_DIR)
ENV_FILE_STR: str = str(ENV_FILE)

if __name__ == "__main__":
    print(f"ROOT_DIR      = {ROOT_DIR}")
    print(f"DATA_DIR      = {DATA_DIR}  (exists: {DATA_DIR.exists()})")
    print(f"ONTOLOGY_DIR  = {ONTOLOGY_DIR}  (exists: {ONTOLOGY_DIR.exists()})")
    print(f"ENV_FILE      = {ENV_FILE}  (exists: {ENV_FILE.exists()})")
