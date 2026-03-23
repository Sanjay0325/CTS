"""Conversations router - list conversations, messages, update title, active profile."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.auth import get_current_user
from src.core.deps import get_chat_data, get_conversation_service, get_user_settings_service
from src.models import ActiveProfileUpdate, ConversationResponse, ConversationTitleUpdate
from src.services.chat_data_supabase import ChatDataSupabase
from src.services.conversation_service_supabase import ConversationServiceSupabase
from src.services.user_settings_service_supabase import UserSettingsServiceSupabase

router = APIRouter()


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    user: dict = Depends(get_current_user),
    svc: ConversationServiceSupabase = Depends(get_conversation_service),
):
    """List user's conversations (chat history)."""
    return svc.list_conversations(user["id"])


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: UUID,
    user: dict = Depends(get_current_user),
    svc: ConversationServiceSupabase = Depends(get_conversation_service),
):
    """Get messages for a conversation."""
    return svc.get_messages(str(conversation_id), user["id"])


@router.get("/{conversation_id}/messages/{message_id}/trace")
async def get_message_trace(
    conversation_id: UUID,
    message_id: UUID,
    user: dict = Depends(get_current_user),
    data: ChatDataSupabase = Depends(get_chat_data),
):
    """Get prompt trace for a message (visualize RAG, memory, tools, model used)."""
    trace = data.get_message_trace(str(message_id), user["id"])
    if not trace:
        # No metadata row (old message or save failed) - return empty trace instead of 404
        return {
            "prompt_trace": None,
            "model_used": None,
            "tools_used": [],
            "external_dbs_used": [],
            "in_context_count": 0,
        }
    return trace


@router.put("/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: UUID,
    data: ConversationTitleUpdate,
    user: dict = Depends(get_current_user),
    svc: ConversationServiceSupabase = Depends(get_conversation_service),
):
    """Update conversation title."""
    ok = svc.update_conversation_title(str(conversation_id), user["id"], data.title)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True}


@router.delete("/{conversation_id}/messages/{message_id}")
async def delete_message(
    conversation_id: UUID,
    message_id: UUID,
    user: dict = Depends(get_current_user),
    svc: ConversationServiceSupabase = Depends(get_conversation_service),
):
    """Delete a message from a conversation. Reduces in-context for future replies."""
    ok = svc.delete_message(str(conversation_id), str(message_id), user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"ok": True}


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    user: dict = Depends(get_current_user),
    svc: ConversationServiceSupabase = Depends(get_conversation_service),
):
    """Delete a conversation and all its messages."""
    ok = svc.delete_conversation(str(conversation_id), user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True}


@router.put("/settings/active-profile")
async def set_active_profile(
    data: ActiveProfileUpdate,
    user: dict = Depends(get_current_user),
    svc: UserSettingsServiceSupabase = Depends(get_user_settings_service),
):
    """Set active model profile for user."""
    svc.set_active_profile(user["id"], str(data.profile_id))
    return {"ok": True}
