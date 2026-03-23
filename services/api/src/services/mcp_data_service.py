"""
MCP user data service - notes, todos, reminders.

Fetches from Supabase first (user_notes, user_todos, user_reminders).
Falls back to MCP tool calls (list_notes_json, list_todos_json, list_reminders_json)
when Supabase tables are empty or not migrated.
Never raises - returns structured dict with items, storage, optional error.
"""

import json
import logging
from typing import Any

from src.services.chat_data_supabase import ChatDataSupabase

logger = logging.getLogger(__name__)


async def call_mcp_data_tool(
    tool_name: str, user_id: str, data: ChatDataSupabase
) -> str | None:
    """
    Find user's MCP server exposing tool_name, call it with user_id, return result.
    Returns None if no server has the tool or call fails.
    """
    servers = data.get_user_servers(user_id) or []
    for srv in servers:
        srv_url = (srv.get("server_url") or "").rstrip("/")
        if not srv_url:
            continue
        try:
            tools = await data.list_tools_for_server(srv_url)
            tool_names = [t.get("name") for t in (tools or []) if t.get("name")]
            if tool_name in tool_names:
                result = await data.call_tool(srv_url, tool_name, {"user_id": user_id})
                return result
        except Exception as e:
            logger.warning("MCP data tool '%s' failed on server %s: %s", tool_name, srv_url, e)
            continue
    return None


async def get_notes(sb, user_id: str) -> dict[str, Any]:
    """Get notes: Supabase first, then MCP fallback. Never raises."""
    if not user_id:
        return {"items": [], "storage": "supabase:user_notes", "error": "Invalid user"}
    items: list[dict] = []
    storage = "supabase:user_notes"
    try:
        if sb:
            r = (
                sb.table("user_notes")
                .select("id, title, content, created_at, conversation_id")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
            items = list(r.data or [])
    except Exception as e:
        logger.warning("Supabase notes query failed: %s", e)
    if not items and sb:
        try:
            data = ChatDataSupabase(sb)
            result = await call_mcp_data_tool("list_notes_json", user_id, data)
            if result:
                mcp_items = json.loads(result)
                if isinstance(mcp_items, list) and mcp_items:
                    items = [
                        {**x, "id": x.get("id", str(i))}
                        for i, x in enumerate(mcp_items)
                    ]
                    storage = "mcp-servers/notes (merged)"
        except Exception as e:
            logger.warning("MCP notes fallback failed: %s", e)
    return {"items": items, "storage": storage}


async def get_todos(sb, user_id: str) -> dict[str, Any]:
    """Get todos: Supabase first, then MCP fallback. Never raises."""
    if not user_id:
        return {"items": [], "storage": "supabase:user_todos", "error": "Invalid user"}
    try:
        if sb:
            r = (
                sb.table("user_todos")
                .select("id, task, priority, done, created_at, conversation_id")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
            return {"items": r.data or [], "storage": "supabase:user_todos"}
    except Exception as e:
        logger.warning("Supabase todos query failed: %s", e)
    result = None
    if sb:
        try:
            data = ChatDataSupabase(sb)
            result = await call_mcp_data_tool("list_todos_json", user_id, data)
            if result is None:
                result = await call_mcp_data_tool("list_todos", user_id, data)
        except Exception as e:
            logger.warning("MCP todos fallback failed: %s", e)
    if result is None:
        return {
            "items": [],
            "storage": "mcp-servers/todo/todos.json",
            "error": "No Todo MCP server or not running.",
        }
    try:
        return {"items": json.loads(result), "storage": "mcp-servers/todo/todos.json"}
    except Exception:
        return {
            "items": [],
            "storage": "mcp-servers/todo/todos.json",
            "error": "Parse error.",
        }


async def get_reminders(sb, user_id: str) -> dict[str, Any]:
    """Get reminders: Supabase first, then MCP fallback. Never raises."""
    if not user_id:
        return {
            "items": [],
            "storage": "supabase:user_reminders",
            "error": "Invalid user",
        }
    try:
        if sb:
            r = (
                sb.table("user_reminders")
                .select("id, text, remind_at, created_at, conversation_id")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
            items = r.data or []
            normalized = [
                {
                    "id": x.get("id"),
                    "text": x.get("text"),
                    "when": x.get("remind_at"),
                    "created_at": x.get("created_at"),
                    "conversation_id": x.get("conversation_id"),
                }
                for x in items
            ]
            return {"items": normalized, "storage": "supabase:user_reminders"}
    except Exception as e:
        logger.warning("Supabase reminders query failed: %s", e)
    result = None
    if sb:
        try:
            data = ChatDataSupabase(sb)
            result = await call_mcp_data_tool("list_reminders_json", user_id, data)
            if result is None:
                result = await call_mcp_data_tool("list_reminders", user_id, data)
        except Exception as e:
            logger.warning("MCP reminders fallback failed: %s", e)
    if result is None:
        return {
            "items": [],
            "storage": "mcp-servers/reminder/reminders.json",
            "error": "No Reminder MCP server or not running.",
        }
    try:
        return {
            "items": json.loads(result),
            "storage": "mcp-servers/reminder/reminders.json",
        }
    except Exception:
        return {
            "items": [],
            "storage": "mcp-servers/reminder/reminders.json",
            "error": "Parse error.",
        }
