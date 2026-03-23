"""Conversation service using Supabase REST."""

from datetime import datetime, timezone

from src.models import ConversationResponse


class ConversationServiceSupabase:
    """Conversation list and messages via Supabase."""

    def __init__(self, supabase_client):
        self.sb = supabase_client

    def list_conversations(self, user_id: str, limit: int = 50) -> list[ConversationResponse]:
        """List user's conversations, most recently updated first."""
        r = (
            self.sb.table("conversations")
            .select("id, title, created_at, updated_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = r.data or []
        result = []
        for row in rows:
            created = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            updated = None
            if row.get("updated_at"):
                try:
                    updated = datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00"))
                except Exception:
                    updated = created
            result.append(ConversationResponse(id=row["id"], title=row["title"], created_at=created, updated_at=updated))
        return result

    def get_messages(self, conversation_id: str, user_id: str) -> list[dict]:
        """Get all messages for a conversation."""
        r = (
            self.sb.table("messages")
            .select("id, role, content, created_at")
            .eq("conversation_id", conversation_id)
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        rows = r.data or []
        return [
            {"id": str(x["id"]), "role": x["role"], "content": x["content"], "created_at": x["created_at"]}
            for x in rows
        ]

    def update_conversation_title(self, conversation_id: str, user_id: str, title: str) -> bool:
        """Update conversation title."""
        r = (
            self.sb.table("conversations")
            .update({"title": title, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", conversation_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(r.data and len(r.data) > 0)

    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Delete a conversation and its messages (cascade)."""
        try:
            r = self.sb.table("conversations").delete().eq("id", conversation_id).eq("user_id", user_id).execute()
            return bool(r.data and len(r.data) > 0)
        except Exception:
            return False

    def delete_message(self, conversation_id: str, message_id: str, user_id: str) -> bool:
        """Delete a message. Only if it belongs to user's conversation."""
        try:
            r = (
                self.sb.table("messages")
                .delete()
                .eq("id", message_id)
                .eq("conversation_id", conversation_id)
                .eq("user_id", user_id)
                .execute()
            )
            return bool(r.data and len(r.data) > 0)
        except Exception:
            return False
