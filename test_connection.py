import os
from pathlib import Path
from dotenv import load_dotenv
from backend.api.db import get_supabase_client

# Force load from the exact absolute path
env_path = Path('/workspaces/Swiss-Basket-AI/.env')
load_dotenv(dotenv_path=env_path)

print(f"Checking .env at: {env_path}")
print(f"File exists: {env_path.exists()}")

try:
    client = get_supabase_client()
    print("✅ SUCCESS: The keys were found and client is created!")
    print(f"✅ Client type: {type(client).__name__}")
except Exception as e:
    print(f"❌ FAILED: {e}")
