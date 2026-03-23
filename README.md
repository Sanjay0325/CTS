# CTS - Mini ChatGPT-Style Interface with Agentic Memory & MCP Support

A fully functional conversational AI interface modeled after ChatGPT, with model configuration, MCP (Model Context Protocol) server integration, LangChain/LangGraph for orchestration, and four types of agentic memory.

---

## 📘 Full System Architecture

For a **detailed phase-by-phase guide** covering API key setup, chat UI, four memory contexts, message processing flow, LangGraph state lifecycle, MCP integration, tool calling, and viewing saved data, see:

**[docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md)**

---

## Architecture Overview

### Architecture Diagrams


![CTS System Architecture - 5-phase flow](./public/Gemini_Generated_Image_adskx9adskx9adsk.png)


```
┌─────────────────┐     ┌─────────────────────────────────────────────────────────┐     ┌─────────────────┐
│   Next.js       │────▶│   FastAPI (Chat Router)                                  │────▶│   Supabase      │
│   (Frontend)    │     │   ┌─────────────────┐    ┌───────────────────────────┐  │     │   Auth, DB,     │
│   SSE stream    │     │   │ ChatService      │───▶│ LangGraph Agent           │  │     │   Vault         │
└─────────────────┘     │   │ (context, RAG,   │    │ • Model Factory           │  │     └─────────────────┘
                         │   │  memory, tools) │    │ • MCP → LangChain tools   │  │
                         │   └─────────────────┘    │ • agent ↔ tools loop      │  │
                         │            │              └─────────────┬─────────────┘  │
                         │            └────────────────────────────┼─────────────────┤
                         │                                          │               │
                         │                                          ▼               │
                         │              ┌─────────────────────────────────────────┐│
                         │              │   MCP Servers (JSON-RPC tools/call)      ││
                         │              │   Notes, Todo, Calculator, Weather, etc.  ││
                         │              └─────────────────────────────────────────┘│
                         └─────────────────────────────────────────────────────────┘
```

![CTS System Architecture - 5-phase flow](./public/Gemini_Generated_Image_v8yomsv8yomsv8yo.png)

- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python 3.10+, uvicorn, **LangChain + LangGraph**
- **Database**: Supabase (PostgreSQL, Auth, Vault for API keys)
- **MCP**: Model Context Protocol for tool discovery and invocation; MCP tools are wrapped as LangChain tools and executed by LangGraph's ToolNode

### Backend Flow (Contributing to Responses)

1. **Request** → Chat router receives POST `/chat/stream` with message, conversation_id, profile_id.
2. **Context assembly** → ChatService loads: profile (API key, model), conversation, RAG (if collections selected), external memory (memory_items), in-context messages, MCP tools (from all registered servers).
3. **Model selection** → `model_factory.create_chat_model_from_profile()` returns a LangChain chat model (ChatOpenAI for OpenAI/Ollama/Groq/OpenRouter, ChatGoogleGenerativeAI for Gemini).
4. **Tool wrapping** → `mcp_tools.build_mcp_tools()` converts each MCP tool to a LangChain StructuredTool; user_id and conversation_id are injected for notes/todos/reminders.
5. **LangGraph execution** → StateGraph: **agent** (LLM with bind_tools) → **tools** (ToolNode executes MCP via JSON-RPC) → **agent** (loop until no tool calls). Streaming via `astream_events`.
6. **Persistence** → Assistant message, metadata (tools_used, RAG chunks), conversation title, optional memory item.
7. **Response** → SSE stream: `text`, `tool_start`, `tool_done`, `debug`, `done`.

---

## Quick Start

### 1. Install Dependencies

```bash
cd c:\CTS
pnpm install
cd apps/web && pnpm install
cd ../../services/api && pip install -e .
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in:

| Variable | Where to Get | Required |
|----------|--------------|----------|
| `SUPABASE_URL` | Supabase Dashboard → Project Settings → API | Yes |
| `SUPABASE_ANON_KEY` | Same as above | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Same as above | Yes |
| `SUPABASE_JWT_SECRET` | Supabase Dashboard → Project Settings → API → JWT Secret | **Yes** |
| `DATABASE_URL` | Project Settings → Database | Yes |
| `NEXT_PUBLIC_*` | Same as above for frontend | Yes |

### 3. Run the Application

**Terminal 1 – API:**
```bash
cd services/api
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 – Web:**
```bash
cd apps/web
pnpm dev
```

Open http://localhost:3000

---

## Adding Model Profiles

CTS supports OpenAI, Gemini, Groq, OpenRouter, Qwen, Kimi, Together, Fireworks & more. **See [docs/API_KEY_SETUP.md](docs/API_KEY_SETUP.md) for full guide.**

1. Click **Settings** → **Model Profiles**
2. Pick a preset: **OpenAI**, **Gemini**, **Groq**, **OpenRouter**, etc.
3. Paste your API key
4. Click **Add Profile**

| Provider | Preset | API Key From |
|----------|--------|--------------|
| OpenAI | OpenAI | platform.openai.com/api-keys |
| Google | Gemini | aistudio.google.com/apikey |
| Groq | Groq | console.groq.com/keys |
| OpenRouter | OpenRouter | openrouter.ai/keys |
| Ollama (local) | default | No key – run `ollama pull qwen3` |

---

## Prompt Trace

Each assistant message stores a prompt trace. Click **View trace** under any AI response to see model used, RAG chunks, memory items, tools available/used, and system prompt preview.

---

## Verify Keys & Backend

```bash
python scripts/verify_keys_and_backend.py
```

---

## Chat History & RAG

- **Chat History**: Sidebar shows all conversations. "New Chat" starts fresh.
- **In-Context Memory**: Last 20 messages in the conversation.
- **External Memory**: Facts/summaries from Settings → Save to memory.
- **RAG Documents**: Upload in Settings → RAG Documents. Select collections when chatting.
- **Memory Indicators**: Each response shows in-context count, external items, tools, RAG DBs used.

---

## MCP Servers (22 Included)

**Guides:** [docs/MCP_README.md](docs/MCP_README.md) | [docs/MCP_USAGE_GUIDE.md](docs/MCP_USAGE_GUIDE.md) | [docs/TOOL_EXECUTION_FLOW.md](docs/TOOL_EXECUTION_FLOW.md)

| Server | Port | URL | Tools |
|--------|------|-----|-------|
| Notes | 8004 | `http://localhost:8004/mcp` | save_note, list_notes |
| Todo | 8009 | `http://localhost:8009/mcp` | add_todo, list_todos, complete_todo |
| Calculator | 8002 | `http://localhost:8002/mcp` | add, multiply, power |
| Weather | 8003 | `http://localhost:8003/mcp` | get_weather, get_forecast |

**Start all MCP servers:**
```powershell
.\scripts\start_all_mcps.ps1
```

---

## Using MCP Tools in Chat

1. **Start an MCP server** (e.g. Notes): `cd mcp-servers/notes && python server.py`
2. **Settings** → **MCP Servers** → Add Server: `http://localhost:8004/mcp`
3. Click **List Tools** to verify
4. Ask naturally in chat: "Save a note: Meeting at 3pm" → uses `save_note`

---

## Four Memory Types (Agentic)

| Type | Description | Implementation |
|------|-------------|----------------|
| **In-Context** | Recent messages in the conversation | Last 20 messages in prompt |
| **External** | Facts, preferences, summaries from `memory_items` | Settings → Save to memory |
| **In-Weights** | Model's built-in knowledge | Use any LLM |
| **In-Cache** | Cached tool lists and memory lookups | 60s tool cache, 120s memory cache |

---

## Troubleshooting

- **429 Quota Exceeded**: Add billing or wait. See provider dashboard.
- **Invalid or expired token**: Set `SUPABASE_JWT_SECRET` in `.env`, restart API.
- **Tools Available: 0**: Add MCP server in Settings, ensure server is running.
- **Images not showing**: Images are in `docs/assets/`. Add new ones there and reference as `docs/assets/filename.png`.

---

## Project Structure

```
c:\CTS\
├── apps/web/                     # Next.js frontend
├── services/api/                 # FastAPI backend
│   └── src/langgraph_services/  # LangGraph, model_factory, mcp_tools
├── mcp-servers/                  # Notes, Todo, Calculator, etc.
├── docs/                         # Documentation + assets/
└── README.md
```

---

## Contributing

- **New model**: Extend `langgraph_services/model_factory.py`
- **New MCP tool**: Update `mcp_tools.py` or add server in `mcp-servers/`
- **Chat logic**: Edit `chat_service.py` or `chat_graph.py`
