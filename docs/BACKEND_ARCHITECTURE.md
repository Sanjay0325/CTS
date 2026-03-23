# CTS Backend Architecture

Modular FastAPI backend with LangChain/LangGraph for chat and MCP tool execution.

---

## Directory Structure

```
services/api/src/
├── main.py                 # FastAPI app, lifespan, routers, CORS
├── config.py               # Settings from .env
├── models.py               # Pydantic request/response models
├── auth.py                 # JWT verification, get_current_user
├── db.py                   # asyncpg pool (optional, used by memory router)
├── supabase_client.py      # Supabase admin client singleton
├── mcp_available_servers.py # Predefined MCP servers for one-click add
├── tool_trigger_hints.py   # System-prompt hints for tool use
│
├── core/                   # Shared modules
│   ├── __init__.py
│   ├── constants.py        # GEMINI_MODEL_ALIASES (single source)
│   └── deps.py             # FastAPI dependencies (get_chat_data, get_mcp_service, etc.)
│
├── routers/                # HTTP endpoints
│   ├── auth.py             # GET /auth/me
│   ├── chat.py             # POST /chat/stream (SSE)
│   ├── conversations.py    # List, messages, title, active profile
│   ├── documents.py        # Collections, documents, RAG
│   ├── memory.py           # Memory items (asyncpg)
│   ├── mcp.py              # Servers, tools, data (notes, todos, reminders)
│   ├── ollama.py           # GET /ollama/models
│   └── profiles.py         # Model profiles CRUD
│
├── services/               # Business logic & data access
│   ├── chat_service.py     # Chat orchestration, streaming, context
│   ├── chat_data_supabase.py # Profile, messages, MCP tools/call, RAG
│   ├── conversation_service_supabase.py
│   ├── document_service_supabase.py
│   ├── document_service.py  # chunk_text, get_embeddings_sync
│   ├── memory_service.py    # Memory CRUD (asyncpg)
│   ├── mcp_data_service.py # Notes, todos, reminders (Supabase + MCP fallback)
│   ├── mcp_service_supabase.py
│   ├── profile_service_supabase.py
│   ├── user_settings_service_supabase.py  # Active profile
│   └── ollama_service.py   # List Ollama models
│
└── langgraph_services/     # LangChain/LangGraph
    ├── model_factory.py   # Profile → ChatOpenAI / ChatGoogleGenerativeAI
    ├── mcp_tools.py       # MCP → LangChain StructuredTool
    └── chat_graph.py      # StateGraph: agent ↔ tools loop
```

---

## Flow

1. **Request** → Router receives HTTP request, `Depends(get_current_user)` validates JWT.
2. **Dependencies** → `core/deps.py` provides service instances (Supabase required → 503 if not configured).
3. **Service** → Business logic in `services/*`. Chat uses `ChatService` + `ChatDataSupabase` + LangGraph.
4. **Response** → Router returns JSON or SSE stream.

---

## Key Dependencies

| Router      | Depends On                         |
|-------------|------------------------------------|
| chat        | get_chat_data                      |
| conversations | get_conversation_service, get_chat_data, get_user_settings_service |
| documents   | get_document_service               |
| mcp         | get_mcp_service, mcp_data_service  |
| profiles    | get_profile_service                |

All Supabase-backed routers use `get_supabase_or_503()` internally via these deps.

---

## Contribution

- **New router**: Add to `main.py`, use `core.deps` for service factories.
- **New service**: Create in `services/`, add dep in `core/deps.py` if shared.
- **New model provider**: Extend `langgraph_services/model_factory.py`.
- **New Pydantic model**: Add to `src/models.py`.
