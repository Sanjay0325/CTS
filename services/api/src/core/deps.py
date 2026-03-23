"""
Shared FastAPI dependencies for backend services.

Centralizes Supabase checks and service factory creation so routers
don't repeat the same get_supabase_admin() + HTTPException(503) logic.
"""

from fastapi import HTTPException

from src.services.chat_data_supabase import ChatDataSupabase
from src.services.conversation_service_supabase import ConversationServiceSupabase
from src.services.document_service_supabase import DocumentServiceSupabase
from src.services.mcp_service_supabase import MCPServiceSupabase
from src.services.profile_service_supabase import ProfileServiceSupabase
from src.services.user_settings_service_supabase import UserSettingsServiceSupabase
from src.supabase_client import get_supabase_admin


def get_supabase_or_503():
    """Return Supabase admin client or raise 503 if not configured."""
    sb = get_supabase_admin()
    if not sb:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    return sb


def get_chat_data() -> ChatDataSupabase:
    """Dependency: ChatDataSupabase for chat, MCP tool calls, messages."""
    return ChatDataSupabase(get_supabase_or_503())


def get_conversation_service() -> ConversationServiceSupabase:
    """Dependency: ConversationServiceSupabase for list/get messages, update title."""
    return ConversationServiceSupabase(get_supabase_or_503())


def get_mcp_service() -> MCPServiceSupabase:
    """Dependency: MCPServiceSupabase for MCP server CRUD and tool discovery."""
    return MCPServiceSupabase(get_supabase_or_503())


def get_profile_service() -> ProfileServiceSupabase:
    """Dependency: ProfileServiceSupabase for model profiles."""
    return ProfileServiceSupabase(get_supabase_or_503())


def get_user_settings_service() -> UserSettingsServiceSupabase:
    """Dependency: UserSettingsServiceSupabase for active profile, etc."""
    return UserSettingsServiceSupabase(get_supabase_or_503())


def get_document_service() -> DocumentServiceSupabase:
    """Dependency: DocumentServiceSupabase for collections and documents."""
    return DocumentServiceSupabase(get_supabase_or_503())
