"""Supabase client for server-side operations."""

from supabase import create_client
from src.config import settings

_supabase = None


def get_supabase_admin():
    """Get Supabase client with service role (admin) for backend operations."""
    global _supabase
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    if _supabase is None:
        _supabase = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _supabase
