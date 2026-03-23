"""Ollama router - local Llama models available as 'default' to all users."""

from fastapi import APIRouter, Depends

from src.auth import get_current_user
from src.services.ollama_service import get_ollama_default_model, list_ollama_models

router = APIRouter()


@router.get("/models")
async def get_ollama_models(
    user: dict = Depends(get_current_user),
):
    """
    List local Ollama models. Available to all authenticated users.
    Used to show 'default' in chat model selector.
    Returns { available, models, default_model }.
    """
    models = await list_ollama_models()
    default = get_ollama_default_model(models) if models else None
    return {
        "available": len(models) > 0,
        "models": models,
        "default_model": default,
    }
