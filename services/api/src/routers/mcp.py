"""MCP router - server registration, tool discovery, and user data (notes, todos, reminders)."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.auth import get_current_user
from src.core.deps import get_mcp_service
from src.mcp_available_servers import AVAILABLE_MCP_SERVERS
from src.models import MCPServerCreate, MCPServerResponse
from src.services import mcp_client
from src.services.mcp_data_service import get_notes, get_reminders, get_todos
from src.services.mcp_service_supabase import MCPServiceSupabase
from src.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/available-servers")
async def list_available_servers(user: dict = Depends(get_current_user)):
    """List predefined MCP servers available for one-click add. Start servers with: pnpm dev:mcp:all"""
    return {"servers": AVAILABLE_MCP_SERVERS}


@router.get("/servers/{server_id}/health")
async def check_server_health(
    server_id: UUID,
    user: dict = Depends(get_current_user),
    svc: MCPServiceSupabase = Depends(get_mcp_service),
):
    """Quick health check — returns whether an MCP server is reachable."""
    url = svc._get_server_url(server_id, user["id"])
    if not url:
        raise HTTPException(status_code=404, detail="Server not found")
    alive = await mcp_client.check_health(url)
    return {"ok": alive, "server_url": url}


@router.get("/servers", response_model=list[MCPServerResponse])
async def list_servers(
    user: dict = Depends(get_current_user),
    svc: MCPServiceSupabase = Depends(get_mcp_service),
):
    """List registered MCP servers for current user."""
    return svc.list_servers(user["id"])


@router.post("/servers", response_model=MCPServerResponse)
async def register_server(
    data: MCPServerCreate,
    user: dict = Depends(get_current_user),
    svc: MCPServiceSupabase = Depends(get_mcp_service),
):
    """Register a new MCP server."""
    return svc.register_server(
        user_id=user["id"],
        name=data.name,
        server_url=data.server_url,
        transport=data.transport,
    )


@router.get("/servers/{server_id}/tools")
async def list_tools(
    server_id: UUID,
    user: dict = Depends(get_current_user),
    svc: MCPServiceSupabase = Depends(get_mcp_service),
):
    """List tools exposed by an MCP server."""
    tools = await svc.list_tools(server_id, user["id"])
    return {"tools": tools}


@router.get("/servers/{server_id}/resources")
async def list_resources(
    server_id: UUID,
    user: dict = Depends(get_current_user),
    svc: MCPServiceSupabase = Depends(get_mcp_service),
):
    """List resources exposed by an MCP server."""
    resources = await svc.list_resources(server_id, user["id"])
    return {"resources": resources}


@router.get("/servers/{server_id}/prompts")
async def list_prompts(
    server_id: UUID,
    user: dict = Depends(get_current_user),
    svc: MCPServiceSupabase = Depends(get_mcp_service),
):
    """List prompts exposed by an MCP server."""
    prompts = await svc.list_prompts(server_id, user["id"])
    return {"prompts": prompts}


@router.delete("/servers/{server_id}")
async def delete_server(
    server_id: UUID,
    user: dict = Depends(get_current_user),
    svc: MCPServiceSupabase = Depends(get_mcp_service),
):
    """Remove an MCP server."""
    success = svc.delete_server(server_id, user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"ok": True}


@router.get("/data/notes")
async def get_notes_data(user: dict = Depends(get_current_user)):
    """Get this user's notes from Supabase. Falls back to MCP tool if table missing."""
    try:
        user_id = user.get("id") or user.get("sub") or ""
        sb = get_supabase_admin()
        return await get_notes(sb, user_id)
    except Exception:
        return {"items": [], "storage": "supabase:user_notes", "error": "Service temporarily unavailable. Run migration 005_mcp_user_data.sql."}


@router.delete("/data/notes/{note_id}")
async def delete_note_data(note_id: str, user: dict = Depends(get_current_user)):
    """Delete a note by ID. Only owned by user."""
    user_id = user.get("id") or user.get("sub") or ""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        sb = get_supabase_admin()
        r = sb.table("user_notes").delete().eq("id", note_id).eq("user_id", user_id).execute()
        deleted = bool(r.data and len(r.data) > 0)
        if not deleted:
            raise HTTPException(status_code=404, detail="Note not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to delete note")


@router.get("/data/todos")
async def get_todos_data(user: dict = Depends(get_current_user)):
    """Get this user's todos from Supabase. Falls back to MCP tool if table missing."""
    try:
        user_id = user.get("id") or user.get("sub") or ""
        sb = get_supabase_admin()
        return await get_todos(sb, user_id)
    except Exception:
        return {"items": [], "storage": "supabase:user_todos", "error": "Service temporarily unavailable. Run migration 005_mcp_user_data.sql."}


@router.delete("/data/todos/{todo_id}")
async def delete_todo_data(todo_id: str, user: dict = Depends(get_current_user)):
    """Delete a todo by ID. Only owned by user."""
    user_id = user.get("id") or user.get("sub") or ""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        sb = get_supabase_admin()
        r = sb.table("user_todos").delete().eq("id", todo_id).eq("user_id", user_id).execute()
        deleted = bool(r.data and len(r.data) > 0)
        if not deleted:
            raise HTTPException(status_code=404, detail="Todo not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to delete todo")


@router.get("/data/reminders")
async def get_reminders_data(user: dict = Depends(get_current_user)):
    """Get this user's reminders from Supabase. Falls back to MCP tool if table missing."""
    try:
        user_id = user.get("id") or user.get("sub") or ""
        sb = get_supabase_admin()
        return await get_reminders(sb, user_id)
    except Exception:
        return {"items": [], "storage": "supabase:user_reminders", "error": "Service temporarily unavailable. Run migration 005_mcp_user_data.sql."}


@router.delete("/data/reminders/{reminder_id}")
async def delete_reminder_data(reminder_id: str, user: dict = Depends(get_current_user)):
    """Delete a reminder by ID. Only owned by user."""
    user_id = user.get("id") or user.get("sub") or ""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        sb = get_supabase_admin()
        r = sb.table("user_reminders").delete().eq("id", reminder_id).eq("user_id", user_id).execute()
        deleted = bool(r.data and len(r.data) > 0)
        if not deleted:
            raise HTTPException(status_code=404, detail="Reminder not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to delete reminder")
