"""Minimal tests for JWT verification."""

import pytest
from src.auth import verify_supabase_jwt


@pytest.mark.asyncio
async def test_verify_invalid_token_returns_none():
    """Invalid token should return None."""
    result = await verify_supabase_jwt("invalid-token")
    assert result is None


@pytest.mark.asyncio
async def test_verify_empty_token_returns_none():
    """Empty token should return None."""
    result = await verify_supabase_jwt("")
    assert result is None
