"""Model profiles router - list, create, verify, delete profiles."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.auth import get_current_user
from src.core.deps import get_profile_service
from src.models import ModelProfileCreate, ModelProfileResponse
from src.services.profile_service_supabase import ProfileServiceSupabase

router = APIRouter()


@router.get("", response_model=list[ModelProfileResponse])
async def list_profiles(
    user: dict = Depends(get_current_user),
    svc: ProfileServiceSupabase = Depends(get_profile_service),
):
    """List current user's model profiles."""
    return svc.list_profiles(user["id"])


@router.post("", response_model=ModelProfileResponse)
async def create_profile(
    data: ModelProfileCreate,
    user: dict = Depends(get_current_user),
    svc: ProfileServiceSupabase = Depends(get_profile_service),
):
    """Create a new model profile. API key is stored in api_key_plain."""
    try:
        return svc.create_profile(
            user_id=user["id"],
            display_name=data.display_name,
            provider_base_url=data.provider_base_url,
            api_key=data.api_key,
            api_style=data.api_style,
            model_name=data.model_name,
            model_version=data.model_version,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{profile_id}/verify")
async def verify_profile(
    profile_id: UUID,
    user: dict = Depends(get_current_user),
    svc: ProfileServiceSupabase = Depends(get_profile_service),
):
    """Verify profile exists and has API key (without exposing it). Returns 200 if OK."""
    profile = svc.get_profile_with_api_key(profile_id, user["id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not profile.get("api_key"):
        raise HTTPException(status_code=400, detail="Profile has no API key")
    return {"ok": True, "has_key": True, "model": profile.get("model_name"), "api_style": profile.get("api_style")}


@router.delete("/{profile_id}")
async def delete_profile(
    profile_id: UUID,
    user: dict = Depends(get_current_user),
    svc: ProfileServiceSupabase = Depends(get_profile_service),
):
    """Delete a model profile and its secret."""
    success = svc.delete_profile(profile_id, user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"ok": True}
