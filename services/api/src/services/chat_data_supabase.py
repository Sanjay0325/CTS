"""Supabase-backed data access for chat - avoids direct Postgres when unreachable."""

import logging
from uuid import UUID

from src.services import mcp_client

logger = logging.getLogger(__name__)


class ChatDataSupabase:
    """Data access for chat using Supabase REST API."""

    def __init__(self, supabase_client):
        self.sb = supabase_client

    def get_active_profile_id(self, user_id: str) -> str | None:
        """Get active profile ID from user_settings."""
        r = (
            self.sb.table("user_settings")
            .select("active_profile_id")
            .eq("user_id", user_id)
            .execute()
        )
        if r.data and len(r.data) > 0:
            return r.data[0].get("active_profile_id")
        return None

    def get_profile_with_api_key(self, profile_id: str, user_id: str) -> dict | None:
        """Get profile with API key for LLM calls."""
        from src.services.profile_service_supabase import ProfileServiceSupabase
        svc = ProfileServiceSupabase(self.sb)
        return svc.get_profile_with_api_key(UUID(profile_id), user_id)

    def create_conversation(self, user_id: str, title: str = "New conversation") -> str:
        """Create conversation, return id."""
        r = (
            self.sb.table("conversations")
            .insert({"user_id": user_id, "title": title})
            .execute()
        )
        if not r.data or len(r.data) == 0:
            raise ValueError("Failed to create conversation")
        return str(r.data[0]["id"])

    def update_conversation_title(self, conversation_id: str, user_id: str, title: str) -> bool:
        """Update conversation title. Returns True if updated."""
        from datetime import datetime, timezone
        r = (
            self.sb.table("conversations")
            .update({"title": title, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", conversation_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(r.data and len(r.data) > 0)

    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Delete a conversation and its messages (e.g. when LLM fails so it won't appear in history)."""
        try:
            self.sb.table("conversations").delete().eq("id", conversation_id).eq("user_id", user_id).execute()
            return True
        except Exception:
            return False

    def save_note_direct(self, user_id: str, title: str, content: str, conversation_id: str | None = None) -> bool:
        """Save a note directly to Supabase. Ensures notes appear in MCP Data regardless of MCP server config."""
        try:
            title = str(title) if title is not None else ""
            if isinstance(content, (list, tuple)):
                content = "\n".join(str(x) for x in content)
            else:
                content = str(content) if content is not None else ""
            row = {"user_id": user_id, "title": title, "content": content or ""}
            if conversation_id:
                row["conversation_id"] = conversation_id
            self.sb.table("user_notes").insert(row).execute()
            return True
        except Exception:
            return False

    def add_todo_direct(
        self, user_id: str, task: str, priority: str = "medium", conversation_id: str | None = None
    ) -> bool:
        """Add a todo directly to Supabase. Ensures todos appear in MCP Data regardless of MCP server config."""
        try:
            if isinstance(task, (list, tuple)):
                task = "\n".join(str(x) for x in task)
            else:
                task = str(task) if task is not None else ""
            priority = (priority or "medium").lower()
            if priority not in ("low", "medium", "high"):
                priority = "medium"
            row = {"user_id": user_id, "task": task, "priority": priority, "done": False}
            if conversation_id:
                row["conversation_id"] = conversation_id
            self.sb.table("user_todos").insert(row).execute()
            return True
        except Exception:
            return False

    def insert_message(self, conversation_id: str, user_id: str, role: str, content: str) -> str | None:
        """Insert a message. Returns message id if available."""
        r = self.sb.table("messages").insert({
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": role,
            "content": content,
        }).execute()
        if r.data and len(r.data) > 0:
            return str(r.data[0].get("id"))
        return None

    def delete_last_user_message(self, conversation_id: str, user_id: str) -> bool:
        """Delete the most recent user message in a conversation. Used when LLM fails to avoid orphan messages."""
        r = (
            self.sb.table("messages")
            .select("id")
            .eq("conversation_id", conversation_id)
            .eq("user_id", user_id)
            .eq("role", "user")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not r.data or len(r.data) == 0:
            return False
        msg_id = r.data[0].get("id")
        if not msg_id:
            return False
        try:
            self.sb.table("messages").delete().eq("id", msg_id).eq("user_id", user_id).execute()
            return True
        except Exception:
            return False

    def get_messages(self, conversation_id: str, limit: int) -> list[dict]:
        """Get recent messages for context."""
        r = (
            self.sb.table("messages")
            .select("role, content")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = r.data or []
        return list(reversed(rows))

    def get_recent_memory(self, user_id: str, limit: int = 10) -> list[dict]:
        """Get recent memory items for context."""
        r = (
            self.sb.table("memory_items")
            .select("id, kind, text, source, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = r.data or []
        # Filter to allowed kinds (summary, fact, preference)
        allowed = {"summary", "fact", "preference"}
        return [dict(x) for x in rows if x.get("kind") in allowed]

    def create_memory_item(
        self, user_id: str, kind: str, text: str, source: str = "manual", embedding: list[float] | None = None
    ) -> None:
        """Create a memory item, optionally with a vector embedding for semantic search."""
        row = {
            "user_id": user_id,
            "kind": kind,
            "text": text,
            "source": source,
        }
        if embedding:
            row["embedding"] = embedding
            
        self.sb.table("memory_items").insert(row).execute()

    def search_memory(self, user_id: str, query: str, limit: int = 5) -> list[dict]:
        """Search memory items semantically using vector similarity. Falls back to recent if unavailable."""
        if query and query.strip():
            from src.config import get_embedding_api_key
            from src.services.document_service import get_embeddings_sync
            
            api_key = get_embedding_api_key()
            if api_key:
                try:
                    embeddings = get_embeddings_sync([query.strip()], api_key)
                    if embeddings and embeddings[0]:
                        emb = embeddings[0]
                        r = self.sb.rpc(
                            "match_memory_items",
                            {
                                "query_embedding": emb,
                                "filter_user_id": str(user_id),
                                "match_count": limit,
                                "match_threshold": 0.4, # Slightly lower threshold for memory recall
                            },
                        ).execute()
                        if r.data:
                            allowed = {"summary", "fact", "preference"}
                            return [dict(x) for x in r.data if x.get("kind") in allowed]
                except Exception as e:
                    logger.warning(f"Memory semantic search failed, falling back to recent: {e}")
                    
        # Fallback to recent memory
        return self.get_recent_memory(user_id, limit)

    def search_rag(self, user_id: str, collection_ids: list[str], query: str, limit: int = 5) -> list[dict]:
        """Search document chunks in selected collections."""
        from src.services.document_service_supabase import DocumentServiceSupabase
        svc = DocumentServiceSupabase(self.sb)
        return svc.search_collections(user_id, collection_ids, query, limit)

    def save_message_metadata(
        self,
        message_id: str,
        conversation_id: str,
        tools_used: list[str],
        external_dbs_used: list[str],
        in_context_count: int,
        prompt_trace: dict | None = None,
        model_used: str | None = None,
    ) -> None:
        """Save metadata and prompt trace for assistant message."""
        row = {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "tools_used": tools_used,
            "external_dbs_used": external_dbs_used,
            "in_context_count": in_context_count,
        }
        if prompt_trace is not None:
            row["prompt_trace"] = prompt_trace
        if model_used is not None:
            row["model_used"] = model_used
        try:
            self.sb.table("message_metadata").upsert(
                row, on_conflict="message_id"
            ).execute()
        except Exception:
            # Fallback if prompt_trace/model_used columns missing (migration 006 not run)
            if "prompt_trace" in row or "model_used" in row:
                try:
                    self.sb.table("message_metadata").upsert(
                        {
                            "message_id": message_id,
                            "conversation_id": conversation_id,
                            "tools_used": tools_used,
                            "external_dbs_used": external_dbs_used,
                            "in_context_count": in_context_count,
                        },
                        on_conflict="message_id",
                    ).execute()
                except Exception:
                    pass

    def get_message_trace(self, message_id: str, user_id: str) -> dict | None:
        """Get prompt trace for an assistant message (for visualization)."""
        try:
            # Verify message belongs to user via conversation
            msg_r = (
                self.sb.table("messages")
                .select("conversation_id")
                .eq("id", message_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            if not msg_r.data or len(msg_r.data) == 0:
                return None
            r = (
                self.sb.table("message_metadata")
                .select("prompt_trace, model_used, tools_used, external_dbs_used, in_context_count")
                .eq("message_id", message_id)
                .limit(1)
                .execute()
            )
            if not r.data or len(r.data) == 0:
                return None
            row = r.data[0]
            return {
                "prompt_trace": row.get("prompt_trace"),
                "model_used": row.get("model_used"),
                "tools_used": row.get("tools_used") or [],
                "external_dbs_used": row.get("external_dbs_used") or [],
                "in_context_count": row.get("in_context_count") or 0,
            }
        except Exception:
            return None

    def get_user_servers(self, user_id: str) -> list[dict]:
        """Get MCP servers for user."""
        r = (
            self.sb.table("mcp_servers")
            .select("id, name, server_url, transport")
            .eq("user_id", user_id)
            .execute()
        )
        return [dict(x) for x in (r.data or [])]

    async def list_tools_for_server(self, server_url: str) -> list[dict]:
        """List tools from MCP server via shared httpx client."""
        return await mcp_client.list_tools(server_url)

    async def list_resources_for_server(self, server_url: str) -> list[dict]:
        """List resources from MCP server via shared httpx client."""
        return await mcp_client.list_resources(server_url)

    async def list_prompts_for_server(self, server_url: str) -> list[dict]:
        """List prompts from MCP server via shared httpx client."""
        return await mcp_client.list_prompts(server_url)

    async def call_tool(
        self, server_url: str, tool_name: str, arguments: dict
    ) -> str | None:
        """Execute a tool on an MCP server via shared httpx client."""
        if not server_url:
            return None
        return await mcp_client.call_tool(server_url, tool_name, arguments)
