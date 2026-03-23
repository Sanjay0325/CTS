"""
CTS API - FastAPI application entry point.

Provides:
  - Auth: JWT verification, /auth/me
  - Chat: POST /chat/stream (SSE with LangChain/LangGraph)
  - Conversations: list, messages, title, active profile
  - Documents: RAG collections and uploads
  - Memory: external memory items (facts, preferences)
  - MCP: server registration, tools, notes/todos/reminders
  - Profiles: model profiles with API keys
  - Ollama: list local models
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import settings
from src.db import close_pool, init_pool
from src.routers import auth, chat, conversations, documents, memory, mcp, ollama, profiles
from src.services.mcp_client import close_mcp_client, init_mcp_client

# ─── Structured logging ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cts")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init httpx pool, asyncpg pool (optional), LangSmith tracing. Shutdown: close all."""
    import os
    if str(settings.langsmith_tracing).lower() in ("true", "1") and settings.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project or "cts"
    # Shared httpx client for MCP calls (connection reuse)
    init_mcp_client()
    logger.info("Shared MCP httpx client initialized")
    try:
        await init_pool()
        logger.info("Database pool initialized")
    except Exception:
        logger.info("Database pool skipped (DATABASE_URL not set or unreachable)")
    yield
    await close_mcp_client()
    await close_pool()
    logger.info("Shutdown complete")


app = FastAPI(
    lifespan=lifespan,
    title="CTS API",
    description="Chat interface with LangChain/LangGraph, MCP tools, RAG, and agentic memory.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(ollama.router, prefix="/ollama", tags=["ollama"])
app.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(memory.router, prefix="/memory", tags=["memory"])
app.include_router(mcp.router, prefix="/mcp", tags=["mcp"])
app.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return actual error in 500 responses for debugging."""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__},
    )


@app.get("/health")
async def health():
    """Health check. Returns 200 when API is running."""
    return {"status": "ok"}
