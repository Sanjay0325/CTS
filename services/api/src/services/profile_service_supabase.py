"""Model profile service using Supabase REST API (works when direct Postgres is unreachable)."""

from datetime import datetime
from uuid import UUID, uuid4

from src.models import ModelProfileResponse


class ProfileServiceSupabase:
    """Profile service using Supabase client - uses HTTPS, no direct Postgres needed."""

    def __init__(self, supabase_client):
        self.sb = supabase_client

    def list_profiles(self, user_id: str) -> list[ModelProfileResponse]:
        """List all profiles for a user."""
        r = (
            self.sb.table("model_profiles")
            .select("id, display_name, provider_base_url, api_style, model_name, model_version, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        rows = r.data or []
        return [
            ModelProfileResponse(
                id=row["id"],
                display_name=row["display_name"],
                provider_base_url=row["provider_base_url"],
                api_style=row["api_style"],
                model_name=row["model_name"],
                model_version=row.get("model_version"),
                created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            )
            for row in rows
        ]

    def create_profile(
        self,
        user_id: str,
        display_name: str,
        provider_base_url: str,
        api_key: str,
        api_style: str = "openai",
        model_name: str = "",
        model_version: str | None = None,
    ) -> ModelProfileResponse:
        """Create profile and store API key in api_key_plain (no Vault via REST)."""
        profile_id = str(uuid4())
        profile_row = {
            "id": profile_id,
            "user_id": user_id,
            "display_name": display_name,
            "provider_base_url": provider_base_url,
            "api_style": api_style,
            "model_name": model_name or "",
            "model_version": model_version or "",
        }
        self.sb.table("model_profiles").insert(profile_row).execute()

        secret_row = {
            "profile_id": profile_id,
            "vault_secret_id": None,
            "api_key_plain": (api_key or "").strip(),
        }
        self.sb.table("model_profile_secrets").insert(secret_row).execute()

        return ModelProfileResponse(
            id=UUID(profile_id),
            display_name=display_name,
            provider_base_url=provider_base_url,
            api_style=api_style,
            model_name=model_name,
            model_version=model_version,
            created_at=datetime.utcnow(),
        )

    def delete_profile(self, profile_id: UUID, user_id: str) -> bool:
        """Delete profile (secrets cascade). Returns True if deleted."""
        r = (
            self.sb.table("model_profiles")
            .delete()
            .eq("id", str(profile_id))
            .eq("user_id", user_id)
            .execute()
        )
        return bool(r.data and len(r.data) > 0)

    def get_profile_with_api_key(self, profile_id: UUID, user_id: str) -> dict | None:
        """Get profile with API key for chat. Returns None if not found."""
        r = (
            self.sb.table("model_profiles")
            .select("id, display_name, provider_base_url, api_style, model_name, model_version")
            .eq("id", str(profile_id))
            .eq("user_id", user_id)
            .execute()
        )
        if not r.data or len(r.data) == 0:
            return None
        profile = r.data[0]

        s = (
            self.sb.table("model_profile_secrets")
            .select("api_key_plain")
            .eq("profile_id", str(profile_id))
            .execute()
        )
        api_key = None
        if s.data and len(s.data) > 0:
            raw = s.data[0].get("api_key_plain")
            api_key = (raw or "").strip() if raw else None
        if not api_key:
            return None
        return {
            "id": profile["id"],
            "display_name": profile["display_name"],
            "provider_base_url": profile["provider_base_url"],
            "api_style": profile["api_style"],
            "model_name": profile["model_name"],
            "model_version": profile.get("model_version"),
            "api_key": api_key,
        }
