"""MCP Todo - per-user todo list in Supabase (falls back to JSON file)."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP


def _load_project_env():
    """Load .env from project root so SUPABASE_URL/SERVICE_ROLE_KEY are available."""
    try:
        from dotenv import load_dotenv
        root = Path(__file__).resolve().parent.parent.parent
        for name in (".env", ".env.local"):
            p = root / name
            if p.exists():
                load_dotenv(p)
                break
    except ImportError:
        pass


_load_project_env()

mcp = FastMCP("Todo", json_response=True, host="0.0.0.0", port=8009, stateless_http=True)

TODOS_FILE = os.environ.get("MCP_TODOS_FILE", Path(__file__).parent / "todos.json")
SUPABASE_URL = os.environ.get("SUPABASE_URL", os.environ.get("NEXT_PUBLIC_SUPABASE_URL", ""))
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", os.environ.get("SUPABASE_KEY", ""))

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


def _load_todos() -> list[dict]:
    if Path(TODOS_FILE).exists():
        try:
            with open(TODOS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_todos(todos: list[dict]) -> None:
    try:
        Path(TODOS_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(TODOS_FILE, "w", encoding="utf-8") as f:
            json.dump(todos, f, indent=2)
    except Exception:
        pass


def _is_recent_duplicate_todo(sb, user_id: str, task: str, within_seconds: int = 120) -> bool:
    """Avoid duplicate inserts when LLM calls add_todo multiple times with same task."""
    if not sb or not user_id:
        return False
    try:
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=within_seconds)).isoformat()
        r = (
            sb.table("user_todos")
            .select("id")
            .eq("user_id", user_id)
            .eq("task", task or "")
            .gte("created_at", cutoff)
            .limit(1)
            .execute()
        )
        return bool(r.data and len(r.data) > 0)
    except Exception:
        return False


@mcp.tool()
def add_todo(task: str, priority: str = "medium", user_id: str = "", conversation_id: str = "") -> str:
    """Add a todo item. Priority: low, medium, high."""
    now = datetime.now(timezone.utc).isoformat()

    if user_id:
        sb = _get_sb()
        if sb:
            try:
                if _is_recent_duplicate_todo(sb, user_id, task or ""):
                    return f"Todo already added: {task or 'Task'}"
                row: dict = {"user_id": user_id, "task": task, "priority": priority, "done": False}
                if conversation_id:
                    row["conversation_id"] = conversation_id
                sb.table("user_todos").insert(row).execute()
                return f"Added: {task} (priority: {priority})"
            except Exception:
                pass

    todos = _load_todos()
    todos.append({"task": task, "priority": priority, "done": False, "created_at": now})
    _save_todos(todos)
    return f"Added: {task} (priority: {priority})"


@mcp.tool()
def list_todos_json(include_done: bool = True, user_id: str = "") -> str:
    """Return all todos as JSON array for UI. Each item: id, task, priority, done, created_at."""
    if user_id:
        sb = _get_sb()
        if sb:
            try:
                q = (
                    sb.table("user_todos")
                    .select("id, task, priority, done, created_at, conversation_id")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                )
                if not include_done:
                    q = q.eq("done", False)
                r = q.execute()
                return json.dumps(r.data or [])
            except Exception:
                pass

    todos = _load_todos()
    if not include_done:
        todos = [t for t in todos if not t.get("done", False)]
    for i, t in enumerate(todos):
        if "created_at" not in t:
            t["created_at"] = ""
        if "id" not in t:
            t["id"] = str(i)
    return json.dumps(todos)


@mcp.tool()
def list_todos(include_done: bool = False, user_id: str = "") -> str:
    """List all todos. Set include_done=True to show completed."""
    if user_id:
        sb = _get_sb()
        if sb:
            try:
                q = (
                    sb.table("user_todos")
                    .select("task, priority, done")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                )
                if not include_done:
                    q = q.eq("done", False)
                r = q.execute()
                items = r.data or []
                if not items:
                    return "No todos."
                return "\n".join(
                    f"- [{'x' if t['done'] else ' '}] {t['task']} ({t['priority']})"
                    for t in items
                )
            except Exception:
                pass

    todos = _load_todos()
    items = todos if include_done else [t for t in todos if not t.get("done", False)]
    if not items:
        return "No todos."
    return "\n".join(f"- [{'x' if t['done'] else ' '}] {t['task']} ({t['priority']})" for t in items)


@mcp.tool()
def complete_todo(task: str, user_id: str = "") -> str:
    """Mark a todo as complete by task name (partial match)."""
    if user_id:
        sb = _get_sb()
        if sb:
            try:
                r = (
                    sb.table("user_todos")
                    .select("id, task")
                    .eq("user_id", user_id)
                    .eq("done", False)
                    .ilike("task", f"%{task}%")
                    .limit(1)
                    .execute()
                )
                if r.data:
                    row = r.data[0]
                    sb.table("user_todos").update({"done": True}).eq("id", row["id"]).execute()
                    return f"Completed: {row['task']}"
                return f"Todo not found: {task}"
            except Exception:
                pass

    todos = _load_todos()
    for t in todos:
        if task.lower() in t.get("task", "").lower():
            t["done"] = True
            _save_todos(todos)
            return f"Completed: {t['task']}"
    return f"Todo not found: {task}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
