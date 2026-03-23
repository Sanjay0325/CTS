"""Auth router - verify user endpoint."""

from fastapi import APIRouter, Depends

from src.auth import get_current_user

router = APIRouter()


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Return current user info from JWT."""
    return {"id": user["id"], "payload": user.get("payload", {})}
