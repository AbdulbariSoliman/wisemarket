# ============================================================
# WISEMARKET — TEST CONFIGURATION
# ============================================================
# - Ensures repo root is importable (backend.*) and WISEMARKET_ROOT set.
# - Loads test env (.env.test if present, else .env).
# - Auto-marks every test in test_api.py as `integration`.
# - Skips integration tests cleanly when no DB is configured.
# ============================================================
import os
from pathlib import Path
import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

# Make `backend` importable and give settings.py a root to detect.
os.environ.setdefault("WISEMARKET_ROOT", str(ROOT))
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load .env.test first (CI/local Postgres), fall back to .env.
_env_test = ROOT / ".env.test"
load_dotenv(_env_test if _env_test.exists() else ROOT / ".env")


def _db_configured() -> bool:
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"))


def pytest_collection_modifyitems(config, items):
    """Auto-mark all tests in test_api.py as integration, and skip
    integration tests when no DB is configured."""
    skip_integration = pytest.mark.skip(
        reason="integration test: set SUPABASE_URL/SUPABASE_KEY to a seeded DB to run"
    )
    for item in items:
        if "test_api.py" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        if "integration" in item.keywords and not _db_configured():
            item.add_marker(skip_integration)
