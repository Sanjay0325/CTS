"""Core shared modules: dependencies, constants."""

from src.core.constants import GEMINI_MODEL_ALIASES
from src.core.deps import (
    get_chat_data,
    get_conversation_service,
    get_document_service,
    get_mcp_service,
    get_profile_service,
    get_supabase_or_503,
    get_user_settings_service,
)

__all__ = [
    "GEMINI_MODEL_ALIASES",
    "get_chat_data",
    "get_conversation_service",
    "get_document_service",
    "get_mcp_service",
    "get_profile_service",
    "get_supabase_or_503",
    "get_user_settings_service",
]
