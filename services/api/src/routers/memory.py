"""Memory router - external memory management via Supabase REST."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.auth import get_current_user
from src.core.deps import get_supabase_or_503
from src.models import MemoryItemCreate, MemoryItemResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[MemoryItemResponse])
async def list_memory(
    user: dict = Depends(get_current_user),
):
    """List memory items for current user."""
    sb = get_supabase_or_503()
    r = (
        sb.table("memory_items")
        .select("id, kind, text, source, created_at")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return [
        MemoryItemResponse(
            id=row["id"],
            kind=row["kind"],
            text=row["text"],
            source=row.get("source"),
            created_at=row["created_at"],
        )
        for row in (r.data or [])
    ]


@router.post("", response_model=MemoryItemResponse)
async def create_memory(
    data: MemoryItemCreate,
    user: dict = Depends(get_current_user),
):
    """Create a memory item (fact or preference)."""
    sb = get_supabase_or_503()
    r = sb.table("memory_items").insert({
        "user_id": user["id"],
        "kind": data.kind,
        "text": data.text,
        "source": data.source or "manual",
    }).execute()
    if not r.data or len(r.data) == 0:
        raise HTTPException(status_code=500, detail="Failed to create memory item")
    row = r.data[0]
    logger.info("Created memory item kind=%s for user %s", data.kind, user["id"])
    return MemoryItemResponse(
        id=row["id"],
        kind=row["kind"],
        text=row["text"],
        source=row.get("source"),
        created_at=row["created_at"],
    )


@router.delete("/{item_id}")
async def delete_memory(
    item_id: UUID,
    user: dict = Depends(get_current_user),
):
    """Delete a memory item."""
    sb = get_supabase_or_503()
    r = (
        sb.table("memory_items")
        .delete()
        .eq("id", str(item_id))
        .eq("user_id", user["id"])
        .execute()
    )
    if not r.data or len(r.data) == 0:
        raise HTTPException(status_code=404, detail="Memory item not found")
    return {"ok": True}

