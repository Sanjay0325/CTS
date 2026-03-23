"""Memory service - external memory (memory_items) management."""

from uuid import UUID, uuid4

import asyncpg
from src.models import MemoryItemResponse


class MemoryService:
    """Service for external memory (persistent memory_items)."""

    @staticmethod
    async def list_items(conn: asyncpg.Connection, user_id: str) -> list[MemoryItemResponse]:
        """List all memory items for user."""
        rows = await conn.fetch(
            """
            SELECT id, kind, text, source, created_at
            FROM memory_items
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 100
            """,
            user_id,
        )
        return [
            MemoryItemResponse(
                id=r["id"],
                kind=r["kind"],
                text=r["text"],
                source=r["source"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    @staticmethod
    async def create_item(
        conn: asyncpg.Connection,
        user_id: str,
        kind: str,
        text: str,
        source: str | None = None,
    ) -> MemoryItemResponse:
        """Create a memory item."""
        item_id = uuid4()
        await conn.execute(
            """
            INSERT INTO memory_items (id, user_id, kind, text, source)
            VALUES ($1, $2, $3, $4, $5)
            """,
            item_id,
            user_id,
            kind,
            text,
            source or "manual",
        )
        row = await conn.fetchrow(
            "SELECT id, kind, text, source, created_at FROM memory_items WHERE id = $1",
            item_id,
        )
        return MemoryItemResponse(
            id=row["id"],
            kind=row["kind"],
            text=row["text"],
            source=row["source"],
            created_at=row["created_at"],
        )

    @staticmethod
    async def delete_item(
        conn: asyncpg.Connection, item_id: UUID, user_id: str
    ) -> bool:
        """Delete a memory item."""
        result = await conn.execute(
            "DELETE FROM memory_items WHERE id = $1 AND user_id = $2",
            item_id,
            user_id,
        )
        return result == "DELETE 1"
