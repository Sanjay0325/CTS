"""MCP Notes server - per-user note storage in Supabase (falls back to JSON file)."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Load .env from project root so SUPABASE_URL/SERVICE_ROLE_KEY are available
def _load_project_env():
    try:
        from dotenv import load_dotenv
        root = Path(__file__).resolve().parent.parent.parent  # CTS project root
        for name in (".env", ".env.local"):
            p = root / name
            if p.exists():
                load_dotenv(p)
                break
    except ImportError:
        pass  # dotenv optional

_load_project_env()

mcp = FastMCP("Notes", json_response=True, host="0.0.0.0", port=8004, stateless_http=True)

NOTES_FILE = os.environ.get("MCP_NOTES_FILE", Path(__file__).parent / "notes.json")
SUPABASE_URL = os.environ.get("SUPABASE_URL", os.environ.get("NEXT_PUBLIC_SUPABASE_URL", ""))
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", os.environ.get("SUPABASE_KEY", ""))

_sb_client = None


def _get_sb():
    """Return a cached supabase client using service role key, or None if not configured."""
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


# ---------- JSON fallback helpers ----------

def _load_notes() -> list[dict]:
    if Path(NOTES_FILE).exists():
        try:
            with open(NOTES_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_notes(notes: list[dict]) -> None:
    try:
        Path(NOTES_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=2)
    except Exception:
        pass


# ---------- Tools ----------

def _is_recent_duplicate_note(sb, user_id: str, title: str, content: str, within_seconds: int = 120) -> bool:
    """Avoid duplicate inserts when LLM calls save_note multiple times with same content."""
    if not sb or not user_id:
        return False
    try:
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=within_seconds)).isoformat()
        r = (
            sb.table("user_notes")
            .select("id")
            .eq("user_id", user_id)
            .eq("title", title or "")
            .eq("content", content or "")
            .gte("created_at", cutoff)
            .limit(1)
            .execute()
        )
        return bool(r.data and len(r.data) > 0)
    except Exception:
        return False


@mcp.tool()
def save_note(title: str, content: str, user_id: str = "", conversation_id: str = "") -> str:
    """Save a note. Params: title (required), content (required). Use when: remember this, take a note, save that."""
    now = datetime.now(timezone.utc).isoformat()

    if user_id:
        sb = _get_sb()
        if sb:
            try:
                if _is_recent_duplicate_note(sb, user_id, title or "", content or ""):
                    return f"Note already saved: {title or 'Note'}"
                row: dict = {"user_id": user_id, "title": title, "content": content}
                if conversation_id:
                    row["conversation_id"] = conversation_id
                sb.table("user_notes").insert(row).execute()
                return f"Saved note: {title}"
            except Exception:
                pass

    # Fallback: JSON file
    notes = _load_notes()
    notes.append({"title": title, "content": content, "created_at": now})
    _save_notes(notes)
    return f"Saved note: {title}"


@mcp.tool()
def list_notes_json(user_id: str = "") -> str:
    """Return all notes as JSON array for UI. Each item: id, title, content, created_at."""
    if user_id:
        sb = _get_sb()
        if sb:
            try:
                r = (
                    sb.table("user_notes")
                    .select("id, title, content, created_at, conversation_id")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .execute()
                )
                return json.dumps(r.data or [])
            except Exception:
                pass

    # Fallback: JSON file
    notes = _load_notes()
    for i, n in enumerate(notes):
        if "created_at" not in n:
            n["created_at"] = ""
        if "id" not in n:
            n["id"] = str(i)
    return json.dumps(notes)


@mcp.tool()
def list_notes(user_id: str = "") -> str:
    """List all saved notes with titles and content preview. Use when user asks: what are my notes, show my notes, list notes."""
    if user_id:
        sb = _get_sb()
        if sb:
            try:
                r = (
                    sb.table("user_notes")
                    .select("title, content")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .execute()
                )
                notes = r.data or []
                if not notes:
                    return "No notes saved."
                return "\n".join(
                    f"- **{n['title']}**: {n['content'][:80]}{'...' if len(n['content']) > 80 else ''}"
                    for n in notes
                )
            except Exception:
                pass

    notes = _load_notes()
    if not notes:
        return "No notes saved."
    return "\n".join(
        f"- **{n['title']}**: {n['content'][:80]}{'...' if len(n['content']) > 80 else ''}"
        for n in notes
    )


@mcp.tool()
def get_notes_summary(user_id: str = "") -> str:
    """Get full content of all notes. Use when user says: send my notes back, show everything I saved."""
    if user_id:
        sb = _get_sb()
        if sb:
            try:
                r = (
                    sb.table("user_notes")
                    .select("title, content")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .execute()
                )
                notes = r.data or []
                if not notes:
                    return "No notes saved."
                return "\n\n---\n\n".join(f"## {n['title']}\n{n['content']}" for n in notes)
            except Exception:
                pass

    notes = _load_notes()
    if not notes:
        return "No notes saved."
    return "\n\n---\n\n".join(f"## {n['title']}\n{n['content']}" for n in notes)


if __name__ == "__main__":
    import sys
    # Support stdio for Cursor/IDE integration (spawns process); otherwise HTTP for CTS
    use_stdio = "--stdio" in sys.argv or os.environ.get("MCP_TRANSPORT") == "stdio"
    mcp.run(transport="stdio" if use_stdio else "streamable-http")
