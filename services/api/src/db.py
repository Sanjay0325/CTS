"""Database connection and session management."""

from typing import AsyncGenerator

import asyncpg
from src.config import settings

_pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool | None:
    """Initialize database connection pool. Returns None if DATABASE_URL not set."""
    global _pool
    if _pool is None and settings.database_url:
        _pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    return _pool


async def close_pool() -> None:
    """Close database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get database connection for request context."""
    pool = await init_pool()
    if pool is None:
        raise ValueError("DATABASE_URL is not set. Configure it in .env to use database features.")
    async with pool.acquire() as conn:
        yield conn
