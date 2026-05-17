"""
Supabase client factory.

Strategy (no service role key):
  - A global admin client handles JWT validation via supabase.auth.get_user()
  - Per-request user-scoped clients are created by calling .postgrest.auth(token)
    so every query runs under the user's identity — RLS policies apply automatically.
"""
from supabase import create_client, Client
from app.config import settings


def get_supabase_admin() -> Client:
    """Global client — used ONLY for auth token validation, never for data queries."""
    return create_client(settings.supabase_url, settings.supabase_key)


def get_user_client(token: str) -> Client:
    """
    Returns a Supabase client authenticated as the requesting user.
    All data operations (INSERT / SELECT / UPDATE) made with this client
    respect Row Level Security and are scoped to that user's rows.
    """
    client = create_client(settings.supabase_url, settings.supabase_key)
    client.postgrest.auth(token)
    return client
