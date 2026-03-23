"""
Pydantic models for API requests and responses.

Covers: model profiles, MCP servers, chat, memory, conversations, documents.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Model Profiles
class ModelProfileCreate(BaseModel):
    """Request to create a model profile."""

    display_name: str = Field(..., min_length=1, max_length=100)
    provider_base_url: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)

    api_style: str = Field(default="openai", pattern="^[a-zA-Z0-9_-]+$")  # openai, gemini, groq, openrouter, together, etc.
    model_name: str = Field(..., min_length=1)
    model_version: Optional[str] = None


class ModelProfileResponse(BaseModel):
    """Model profile response (without API key)."""

    id: UUID
    display_name: str
    provider_base_url: str
    api_style: str
    model_name: str
    model_version: Optional[str] = None
    created_at: datetime


# MCP Servers
class MCPServerCreate(BaseModel):
    """Request to register an MCP server."""

    name: str = Field(..., min_length=1, max_length=100)
    server_url: str = Field(..., min_length=1)
    transport: str = Field(default="streamable-http", pattern="^(streamable-http|stdio)$")


class MCPServerResponse(BaseModel):
    """MCP server response."""

    id: UUID
    name: str
    server_url: str
    transport: str
    created_at: datetime


# Chat
class ChatMessage(BaseModel):
    """Single chat message."""

    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    """Chat request with streaming."""

    conversation_id: Optional[UUID] = None
    message: str = Field(..., min_length=1)
    profile_id: Optional[UUID] = None
    ollama_model: Optional[str] = None  # When set, use local Ollama as "default" (all users)
    save_to_memory: Optional[bool] = False
    memory_kind: Optional[str] = Field(default="fact", pattern="^(fact|preference)$")
    collection_ids: Optional[list[str]] = None  # RAG: search these collections


# Memory
class MemoryItemCreate(BaseModel):
    """Request to create a memory item."""

    kind: str = Field(..., pattern="^(summary|fact|preference)$")
    text: str = Field(..., min_length=1)
    source: Optional[str] = None


class MemoryItemResponse(BaseModel):
    """Memory item response."""

    id: UUID
    kind: str
    text: str
    source: Optional[str] = None
    created_at: datetime


# Conversations
class ConversationCreate(BaseModel):
    """Request to create a conversation."""

    title: str = Field(default="New conversation", max_length=200)


class ConversationResponse(BaseModel):
    """Conversation response."""

    id: UUID
    title: str
    created_at: datetime
    updated_at: Optional[datetime] = None


# Documents
class DocumentCollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""


class DocumentUpload(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    collection_id: Optional[str] = None


# Conversations (updates)
class ConversationTitleUpdate(BaseModel):
    """Request to update conversation title."""

    title: str = Field(..., min_length=1, max_length=200)


class ActiveProfileUpdate(BaseModel):
    """Request to set active model profile for user."""

    profile_id: UUID
