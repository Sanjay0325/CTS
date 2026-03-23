"""MCP Reminder - per-user reminders in Supabase (falls back to JSON file)."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Reminder", json_response=True, host="0.0.0.0", port=8018, stateless_http=True)

REMINDERS_FILE = os.environ.get("MCP_REMINDERS_FILE", Path(__file__).parent / "reminders.json")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

_sb_client = None


def _get_sb():
    global _sb_client
    if _sb_client is not None:
        return _sb_client
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        from supabase import create_client
        _sb_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return _sb_client
    except Exception:
        return None


def _load_reminders() -> list[dict]:
    if Path(REMINDERS_FILE).exists():
        try:
            with open(REMINDERS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_reminders(reminders: list[dict]) -> None:
    try:
        Path(REMINDERS_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(reminders, f, indent=2)
    except Exception:
        pass


@mcp.tool()
def set_reminder(text: str, when: str, user_id: str = "", conversation_id: str = "") -> str:
    """Set a reminder. When: date/time or relative (e.g. in 1 hour)."""
    now = datetime.now(timezone.utc).isoformat()

    if user_id:
        sb = _get_sb()
        if sb:
            try:
                row: dict = {"user_id": user_id, "text": text, "remind_at": when}
                if conversation_id:
                    row["conversation_id"] = conversation_id
                sb.table("user_reminders").insert(row).execute()
                return f"Reminder set: '{text}' at {when}"
            except Exception:
                pass

    reminders = _load_reminders()
    reminders.append({"text": text, "when": when, "created_at": now})
    _save_reminders(reminders)
    return f"Reminder set: '{text}' at {when}"


@mcp.tool()
def list_reminders_json(user_id: str = "") -> str:
    """Return all reminders as JSON array for UI. Each item: id, text, remind_at, created_at."""
    if user_id:
        sb = _get_sb()
        if sb:
            try:
                r = (
                    sb.table("user_reminders")
                    .select("id, text, remind_at, created_at, conversation_id")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .execute()
                )
                # Normalize field name: remind_at -> when for UI consistency
                items = []
                for row in (r.data or []):
                    items.append({
                        "id": row.get("id"),
                        "text": row.get("text"),
                        "when": row.get("remind_at"),
                        "created_at": row.get("created_at"),
                        "conversation_id": row.get("conversation_id"),
                    })
                return json.dumps(items)
            except Exception:
                pass

    reminders = _load_reminders()
    for i, r in enumerate(reminders):
        if "created_at" not in r:
            r["created_at"] = ""
        if "id" not in r:
            r["id"] = str(i)
    return json.dumps(reminders)


@mcp.tool()
def list_reminders(user_id: str = "") -> str:
    """List all reminders."""
    if user_id:
        sb = _get_sb()
        if sb:
            try:
                r = (
                    sb.table("user_reminders")
                    .select("text, remind_at")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .execute()
                )
                items = r.data or []
                if not items:
                    return "No reminders."
                return "\n".join(f"- {r['text']} @ {r['remind_at']}" for r in items)
            except Exception:
                pass

    reminders = _load_reminders()
    if not reminders:
        return "No reminders."
    return "\n".join(f"- {r['text']} @ {r['when']}" for r in reminders)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
