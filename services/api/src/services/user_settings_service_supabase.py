"""User settings service - active profile and other user preferences via Supabase."""

from datetime import datetime, timezone


class UserSettingsServiceSupabase:
    """User settings (active_profile_id, etc.) via Supabase."""

    def __init__(self, supabase_client):
        self.sb = supabase_client

    def set_active_profile(self, user_id: str, profile_id: str) -> None:
        """Set the active model profile for the user."""
        self.sb.table("user_settings").upsert(
            {
                "user_id": user_id,
                "active_profile_id": profile_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="user_id",
        ).execute()
