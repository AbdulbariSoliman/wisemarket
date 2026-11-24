# ============================================================
# WISEMARKET — CHECK SUPABASE CONNECTION
# Usage (from the repo root):  python scripts/check_connection.py
# ============================================================
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402
from backend.config.settings import ENV_FILE  # noqa: E402
from backend.api.db import get_supabase_client  # noqa: E402

load_dotenv(dotenv_path=ENV_FILE)
print(f"Checking .env at: {ENV_FILE}")
print(f"File exists: {ENV_FILE.exists()}")

try:
    client = get_supabase_client()
    resp = client.table("products").select("gtin").limit(1).execute()
    print(f"SUCCESS: connected to Supabase ({len(resp.data)} row read from products)")
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
