import os
from supabase import Client, create_client
from dotenv import load_dotenv

load_dotenv()


def get_supabase_client() -> Client:
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are missing")

    return create_client(supabase_url, supabase_key)