"""Chat router - streaming chat with LLM and MCP tools."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from src.auth import get_current_user
from src.core.deps import get_chat_data
from src.models import ChatRequest
from src.services.chat_data_supabase import ChatDataSupabase
from src.services.chat_service import ChatService

router = APIRouter()


async def _stream_with_error_handling(inner_stream):
    """Wrap stream to yield error event on exception instead of dropping connection."""
    try:
        async for event in inner_stream:
            yield event
    except ValueError as e:
        yield {"data": json.dumps({"type": "error", "content": str(e)})}
    except Exception as e:
        yield {"data": json.dumps({"type": "error", "content": str(e)})}


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    user: dict = Depends(get_current_user),
    data: ChatDataSupabase = Depends(get_chat_data),
):
    """Stream chat response with LLM. Uses profile's api_key, provider_base_url, model."""
    try:
        stream = ChatService.stream_chat(
            data=data,
            user_id=user["id"],
            conversation_id=str(request.conversation_id) if request.conversation_id else None,
            message=request.message,
            profile_id=str(request.profile_id) if request.profile_id else None,
            ollama_model=request.ollama_model,
            save_to_memory=request.save_to_memory or False,
            memory_kind=request.memory_kind or "fact",
            collection_ids=request.collection_ids,
        )
        wrapped = _stream_with_error_handling(stream)
        return EventSourceResponse(wrapped)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
