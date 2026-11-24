import os
from supabase import Client, create_client
from dotenv import load_dotenv

load_dotenv()


class DatabaseConfigError(RuntimeError):
    """Supabase is not configured, or the client could not be created."""


def get_supabase_client() -> Client:
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise DatabaseConfigError("SUPABASE_URL and SUPABASE_KEY are missing")

    try:
        return create_client(supabase_url, supabase_key)
    except Exception as e:  # e.g. malformed URL or invalid key
        raise DatabaseConfigError(f"Could not create Supabase client: {e}") from e
