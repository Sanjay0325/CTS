# CTS – System Architecture Guide

**Production-grade conversational AI with agentic memory, MCP tool integration, and LangGraph orchestration.**

You are reading a comprehensive system design document. It explains the entire CTS application in multiple phases: from model API key setup through chat UI, four memory contexts, message processing flow, LangGraph state lifecycle, MCP server integration, tool calling, and viewing saved data.

### Architecture Diagrams

<img src="assets/Gemini_Generated_Image_adskx9adskx9adsk.png" alt="CTS System Architecture - 5-phase flow" width="800"/>

<img src="assets/Gemini_Generated_Image_v8yomsv8yomsv8yo.png" alt="CTS Architecture Diagram" width="800"/>

---

## 🔷 PHASE 1: MODEL API KEY & PROFILE SETUP

### Overview

CTS supports any OpenAI-compatible or Gemini API. API keys are stored securely in Supabase (Vault or `model_profile_secrets`). Keys are **never** returned to the frontend after creation.

### Flow

```
User signs in → Settings → Model Profiles
         │
         ▼
Pick preset (OpenAI, Groq, OpenRouter, Gemini, etc.)
         │
         ▼
Paste API key → Add Profile
         │
         ▼
Key stored in model_profile_secrets (Supabase)
         │
         ▼
Select profile in chat dropdown → chat uses this profile for all LLM calls
```

### Supported Providers

| Preset | Base URL | Example Model | API Key Source |
|--------|----------|---------------|----------------|
| **OpenAI** | `https://api.openai.com` | gpt-4o-mini | platform.openai.com |
| **Gemini** | `https://generativelanguage.googleapis.com/v1beta` | gemini-2.0-flash | aistudio.google.com |
| **Groq** | `https://api.groq.com/openai` | llama-3.1-70b-versatile | console.groq.com |
| **OpenRouter** | `https://openrouter.ai/api` | qwen/qwen-2.5-72b-instruct | openrouter.ai/keys |
| **Ollama (default)** | `http://localhost:11434` | qwen3, llama3.1 | No key – local only |

### Backend Resolution

```
Chat request (profile_id) → ChatDataSupabase.get_profile_with_api_key()
         │
         ▼
ProfileServiceSupabase fetches profile + decrypted api_key from Vault
         │
         ▼
model_factory.create_chat_model_from_profile(profile) → ChatOpenAI / ChatGoogleGenerativeAI
         │
         ▼
LangGraph agent uses this model for all inference
```

### Key Files

| File | Purpose |
|------|---------|
| `routers/profiles.py` | CRUD for model profiles |
| `services/profile_service_supabase.py` | Fetch profile with decrypted API key |
| `langgraph_services/model_factory.py` | Profile → LangChain chat model |

---

## 🔷 PHASE 2: CHAT UI INTERFACE

### Overview

The chat interface is a ChatGPT-style conversational UI built with Next.js 14, TypeScript, and Tailwind CSS.

### UI Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Header: "CTS Chat"  [Settings]  [Sign out]                              │
├───────────────┬─────────────────────────────────────────────────────────┤
│               │                                                          │
│  Sidebar      │  Main Chat Area                                          │
│  ─────────    │  ─────────────                                          │
│  + New Chat   │  • Conversation messages (user / assistant)              │
│               │  • Streaming text with markdown                          │
│  Chat list    │  • Tool status: "🔧 save_note" when tools run            │
│  (clickable)  │  • Memory debug: in-context, external, tools, RAG       │
│               │  • "View trace" under assistant messages                 │
│               │                                                          │
│               │  Input area:                                             │
│               │  • Text input                                            │
│               │  • [Save to memory] checkbox                             │
│               │  • [Send] button                                         │
│               │  • Model dropdown (profiles / Ollama)                     │
│               │  • Collection selector (RAG)                             │
│               │                                                          │
└───────────────┴─────────────────────────────────────────────────────────┘
```

### Request Flow (Frontend → Backend)

```
User types message → Clicks Send
         │
         ▼
POST /chat/stream
{
  message: "...",
  conversation_id: "...",  // null for new chat
  profile_id: "...",      // null → use active profile
  ollama_model: "qwen3",   // optional, overrides profile
  save_to_memory: false,
  memory_kind: "fact",
  collection_ids: ["id1"]  // RAG collections to search
}
         │
         ▼
EventSourceResponse (SSE stream)
         │
         ▼
Events: { type: "text", content: "..." }
        { type: "tool_start", tool: "save_note" }
        { type: "tool_done", tool: "save_note" }
        { type: "debug", memory: { ... } }
        { type: "done", conversation_id: "..." }
        { type: "error", content: "..." }
```

### Key Components

| Component | Path | Responsibility |
|-----------|------|-----------------|
| **ChatPage** | `apps/web/src/app/app/chat/page.tsx` | Layout, Settings toggle |
| **ChatInterface** | `apps/web/src/components/ChatInterface.tsx` | Messages, input, SSE handling |
| **SettingsPanel** | `apps/web/src/components/SettingsPanel.tsx` | Profiles, MCP servers, MCP Data |

---

## 🔷 PHASE 3: FOUR MEMORY CONTEXTS – DETAILED

CTS implements four agentic memory types. All feed into the system prompt except **In-Weights** (model knowledge).

### Memory Type 1: In-Context

| Attribute | Value |
|-----------|-------|
| **What** | Recent messages in the current conversation |
| **Source** | `messages` table, `conversation_id` |
| **Limit** | Last 20 messages (`MAX_CONTEXT_MESSAGES = 20`) |
| **Fetch** | `ChatDataSupabase.get_messages(conv_id, limit)` |
| **Order** | Chronological (oldest first in prompt) |
| **Handling** | Loaded per request; appended to `messages_for_llm` as `[{"role":"user","content":"..."}, ...]` |

**Explicit handling:**
```python
# chat_service.py
msg_rows = data.get_messages(conv_id, MAX_CONTEXT_MESSAGES + 1)
messages_for_llm = [{"role": r["role"], "content": r["content"]} for r in msg_rows]
# Later: converted to HumanMessage / AIMessage for LangGraph
```

---

### Memory Type 2: External Memory

| Attribute | Value |
|-----------|-------|
| **What** | Facts, preferences, summaries from previous sessions |
| **Source** | `memory_items` table |
| **Limit** | Last 10 items |
| **Kinds** | `summary`, `fact`, `preference` (filtered) |
| **Cache** | 120 seconds (`_memory_cache`) – reduces DB calls |
| **UI** | Settings → "Save to memory" checkbox; manual add in Settings |

**Explicit handling:**
```python
# chat_service.py – In-Cache Memory
cache_key = f"mem:{user_id}"
if cache_key in _memory_cache and (time.time() - _memory_cache[cache_key]["ts"]) < _memory_cache_ttl:
    memory_items = _memory_cache[cache_key]["data"]
else:
    memory_items = data.get_recent_memory(user_id, limit=10)
    _memory_cache[cache_key] = {"data": memory_items, "ts": time.time()}

memory_context = "\n\n[External memory - from previous sessions]:\n"
for m in memory_items:
    memory_context += f"- [{m['kind']}] {m['text']}\n"
# Appended to system_prompt
```

---

### Memory Type 3: In-Weights (Model Knowledge)

| Attribute | Value |
|-----------|-------|
| **What** | Knowledge encoded in the model's parameters |
| **Source** | LLM pretraining |
| **Handling** | No explicit code – model uses it automatically |
| **Note** | Enables general knowledge; CTS augments with In-Context, External, RAG, tools |

---

### Memory Type 4: In-Cache

| Attribute | Value |
|-----------|-------|
| **What** | In-memory KV cache for expensive lookups |
| **Tool list cache** | 300s TTL – `_tool_list_cache["tools:{server_id}"]` |
| **Memory cache** | 120s TTL – `_memory_cache["mem:{user_id}"]` |
| **Purpose** | Avoid repeated MCP `tools/list` and `memory_items` queries |

**Explicit handling:**
```python
# chat_service.py
_cache_ttl = 300   # tool list
_memory_cache_ttl = 120  # memory items

# Tool cache
if cache_key in _tool_list_cache and (time.time() - _tool_list_cache[cache_key]["ts"]) < _cache_ttl:
    tools = _tool_list_cache[cache_key]["data"]
else:
    tools = await data.list_tools_for_server(srv_url)
    _tool_list_cache[cache_key] = {"data": tools, "ts": time.time()}
```

---

### RAG (Document Memory) – Bonus Context

| Attribute | Value |
|-----------|-------|
| **What** | User-uploaded documents, chunked and embedded |
| **Source** | `document_chunks` (vector search) |
| **Trigger** | User selects collections in chat |
| **Handling** | `data.search_rag(user_id, collection_ids, message, limit=5)` |
| **Injection** | `rag_context` appended to `system_prompt` |

---

## 🔷 PHASE 4: MESSAGE PROCESSING – STEP-BY-STEP FLOW

### End-to-End Lifecycle

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  1. REQUEST ARRIVAL                                                           │
│     POST /chat/stream → Chat Router → get_current_user (JWT)                  │
└──────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  2. PROFILE & CONVERSATION                                                    │
│     • Resolve profile (profile_id or active_profile_id)                        │
│     • Get or create conversation; persist user message                        │
└──────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  3. CONTEXT ASSEMBLY (ChatService.stream_chat)                                 │
│     • RAG: search_rag() if collection_ids provided                             │
│     • External memory: get_recent_memory() [cached 120s]                      │
│     • In-context: get_messages(conv_id, 21)                                    │
│     • MCP tools: get_user_servers() → list_tools_for_server() [cached 300s]    │
│     • MCP resources & prompts: list_resources_for_server, list_prompts        │
└──────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  4. SYSTEM PROMPT CONSTRUCTION                                                │
│     Base: "You are a helpful AI assistant with agentic memory..."             │
│     + [Resources] if any                                                      │
│     + [Prompts] if any                                                        │
│     + [TOOLS] block with tool list, examples, trigger hints                  │
│     + [External memory] items                                                 │
│     + [RAG] chunks if collections selected                                    │
└──────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  5. LANGGRAPH INVOCATION                                                      │
│     create_chat_graph() + stream_chat_with_graph()                             │
│     → agent ↔ tools loop until model returns text-only                        │
└──────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  6. PERSISTENCE                                                               │
│     • Insert assistant message into messages                                   │
│     • save_message_metadata (tools_used, prompt_trace, model_used)            │
│     • Update conversation title (new chat)                                    │
│     • Optional: create_memory_item if save_to_memory checked                  │
└──────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  7. STREAM EVENTS TO CLIENT                                                   │
│     text, tool_start, tool_done, debug, done (or error)                       │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Error Handling

| Scenario | Backend | Frontend |
|----------|---------|----------|
| **429 Rate limit** | `LLMRateLimitError`; delete new conv or last user msg | Retry countdown, restore input |
| **New conv, LLM fails** | `delete_conversation()` | Clear failed messages |
| **Existing conv, LLM fails** | `delete_last_user_message()` | Restore input for retry |

---

## 🔷 PHASE 5: LANGGRAPH STATE – START TO END

### Graph Definition

```
StateGraph(GraphState)
  START → agent → [conditional: tool_calls?] → tools (if yes) → agent (loop)
                                              → END (if no)
```

### State Schema

```python
class GraphState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
```

- ** messages **: List of `SystemMessage`, `HumanMessage`, `AIMessage`, `ToolMessage`
- **add_messages**: LangGraph reducer – new messages are appended, not replaced

### State Lifecycle (Per Request)

```
INITIAL STATE (stream_chat_with_graph):
  messages = [
    SystemMessage(content=system_prompt),  # Full context: memory, RAG, tools
    HumanMessage(content=msg1),
    AIMessage(content=resp1),
    HumanMessage(content=msg2),   # Latest user message
  ]

AGENT NODE (invoke):
  response = llm_with_tools.invoke(messages)
  # response = AIMessage(content="", tool_calls=[{name:"save_note", args:{...}}])

STATE AFTER AGENT:
  messages += [AIMessage(tool_calls=[...])]

ROUTE: _should_continue(state)
  • Last message has tool_calls? → "tools"
  • tool_count >= MAX_TOOL_ROUNDS (6)? → END (prevent loops)
  • Else → END

TOOLS NODE (ToolNode):
  For each tool_call: invoke StructuredTool → data.call_tool(server_url, name, args)
  ToolMessage(id=tool_call_id, content="[TOOL_OUTPUT: save_note]\nSaved note: ...")

STATE AFTER TOOLS:
  messages += [ToolMessage(...), ToolMessage(...)]

LOOP BACK TO AGENT:
  Agent sees ToolMessage(s), generates next response (text or more tool_calls)
  Repeats until AIMessage has no tool_calls → END

FINAL STATE:
  messages = [System, Human, AIMessage, Human, AIMessage(tool_calls), ToolMessage, AIMessage(content="Done!")]
```

### Streaming vs Final Invoke

- **Streaming**: `graph.astream_events()` – yields `on_chat_model_stream`, `on_tool_start`, `on_tool_end`
- **Final text**: If no text was streamed (tools ran but agent didn't stream final reply), `graph.ainvoke()` fetches final `AIMessage.content`

### Key Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `MAX_TOOL_ROUNDS` | 6 | Max ToolMessage count before forcing END |
| `recursion_limit` | 50 | LangGraph recursion cap |
| `MAX_CONTEXT_MESSAGES` | 20 | In-context message window |

### Graph Tracer (Observability)

`GraphTracer` captures `on_tool_start` / `on_tool_end` and builds:
- `graph_steps`: List of `{type: "agent"|"tool", round, name, args_preview, result_preview}`
- `mermaid`: Flowchart string for "View trace" UI

---

## 🔷 PHASE 6: MCP SERVER INTEGRATION – TOOLS & SERVERS

### Overview

MCP (Model Context Protocol) servers expose tools over HTTP. CTS discovers tools via `tools/list` and executes via `tools/call` JSON-RPC.

### Registration Flow

```
User: Settings → MCP Servers → Add Server
  Name: "Notes"
  URL: http://localhost:8004/mcp
         │
         ▼
Backend: INSERT into mcp_servers (user_id, name, server_url)
         │
         ▼
ChatService: data.get_user_servers(user_id) → list of {id, name, server_url}
```

### Tool Discovery (Per Request)

```
For each server in get_user_servers():
  cache_key = f"tools:{server_id}"
  if cached and not expired (300s):
    tools = cache[cache_key]
  else:
    tools = await data.list_tools_for_server(server_url)
    # POST {server_url}/mcp, method: "tools/list"
    cache[cache_key] = {data: tools, ts: now}
  all_tools.extend(tools)
  tools_with_server.append((server_url, tool))
```

### Tool-to-Server Map

```python
tool_to_server["save_note"] = "http://localhost:8004"
tool_to_server["get_weather"] = "http://localhost:8003"
# Used when executing: call_tool(server_url, tool_name, args)
```

### MCP JSON-RPC

**tools/list:**
```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
→ result.tools = [{name, description, inputSchema}, ...]
```

**tools/call:**
```json
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"save_note","arguments":{"title":"X","content":"Y","user_id":"..."}}}
→ result.content[].text concatenated
```

### Built-in Servers (Selection)

| Server | Port | Tools |
|--------|------|-------|
| Notes | 8004 | save_note, list_notes, list_notes_json, get_notes_summary |
| Todo | 8009 | add_todo, list_todos, complete_todo |
| Calculator | 8002 | add, multiply, power |
| Weather | 8003 | get_weather, get_forecast |

---

## 🔷 PHASE 7: TOOL CALLING IN OUR APPLICATION

### End-to-End Tool Flow

```
1. LLM receives system prompt with [TOOLS] block listing all tools + descriptions
2. User: "Save a note: Meeting at 3pm"
3. Agent node: llm.bind_tools(tools).invoke(messages)
4. Model returns AIMessage(tool_calls=[{name:"save_note", args:{title:"Meeting", content:"Meeting at 3pm"}}])
5. _should_continue → "tools"
6. ToolNode invokes each tool:
   - StructuredTool._invoke(**args)
   - → mcp_tools._invoke: _inject_user_context() adds user_id, conversation_id
   - → data.call_tool(server_url, "save_note", {title, content, user_id, conversation_id})
   - → POST {server_url}/mcp, tools/call
7. MCP Notes server: save_note() → inserts into Supabase user_notes (or JSON fallback)
8. Result: "[TOOL_OUTPUT: save_note]\nSaved note: Meeting"
9. ToolMessage appended to state → agent runs again
10. Model: "I've saved your note about the meeting at 3pm."
11. No tool_calls → END
12. Assistant message persisted; tools_used=["save_note"]
```

### User Context Injection

For notes, todos, reminders:
- `user_id` and `conversation_id` are injected by `mcp_tools._inject_user_context()`
- Ensures data is stored per user in `user_notes` / `user_todos`

### Param Aliasing

Models sometimes send wrong param names. `mcp_tools._normalize_tool_args()` maps:
- `location` → `city` (get_weather)
- `from`, `to` → `from_currency`, `to_currency` (convert_currency)
- `name`, `subject` → `title` (save_note)

### Tool Trigger Hints

`tool_trigger_hints.py` injects keyword→tool hints into the system prompt:
- "save", "note", "remember" → save_note
- "todo", "task" → add_todo
- "weather", "temperature" → get_weather

### Priority Tool Ordering

Message-inferred priority: if user says "save a note", `save_note` is ordered first in the tool list so the model sees it prominently.

---

## 🔷 PHASE 8: END RESULT – WHAT GETS PERSISTED

### Messages

- **User message**: Inserted at request start
- **Assistant message**: Inserted after stream completes (or fallback: "Executed: save_note.")

### Message Metadata

Stored in `message_metadata`:
- `tools_used`: e.g. `["save_note"]`
- `external_dbs_used`: RAG collection names
- `in_context_count`: Number of messages in context
- `prompt_trace`: system_prompt_preview, rag_chunks, memory_items, tools_available, graph_steps, mermaid
- `model_used`: e.g. `qwen3`

### Conversation Title

- New chat: LLM generates title from first message + preview (or truncated first 50 chars)
- Stored in `conversations.title`

### Memory Item (Optional)

If "Save to memory" was checked: `create_memory_item(user_id, kind, text, conv_id)`

---

## 🔷 PHASE 9: VIEWING SAVED THINGS – MCP DATA UI

### Overview

Notes, todos, and reminders saved via MCP tools are viewable in **Settings → MCP Data**.

### Flow

```
User: Settings → MCP Data tab
         │
         ▼
Buttons: [View Notes] [View Todos] [View Reminders]
         │
         ▼
loadMcpData("notes") → GET /mcp/data/notes
         │
         ▼
Backend: Supabase user_notes table (or MCP list_notes_json fallback)
         │
         ▼
Returns: { items: [{id, title, content, created_at}, ...], storage: "supabase:user_notes" }
         │
         ▼
UI: List of titles; click → popup with full content, created_at
```

### Storage Paths

| Type | Table / File | View In |
|------|--------------|---------|
| **Notes** | `user_notes` (Supabase) or `mcp-servers/notes/notes.json` | View Notes |
| **Todos** | `user_todos` (Supabase) or `mcp-servers/todo/todos.json` | View Todos |
| **Reminders** | `user_reminders` (Supabase) or `mcp-servers/reminder/reminders.json` | View Reminders |

### Migration

Run `supabase/migrations/005_mcp_user_data.sql` to create `user_notes`, `user_todos`, `user_reminders`. Without it, MCP Data returns `{items: [], error: "..."}`.

### View Trace

Under each assistant message: **View trace** opens a modal showing:
- Model used
- Tools used
- RAG chunks, memory items
- System prompt preview
- Mermaid flowchart of agent/tool steps

---

## 🔷 PRODUCTION REQUIREMENTS SUMMARY

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 14, TypeScript, Tailwind, SSE |
| **Backend** | FastAPI, uvicorn |
| **Database** | Supabase (PostgreSQL, Auth, Vault) |
| **Orchestration** | LangChain, LangGraph |
| **MCP** | HTTP JSON-RPC (streamable-http) |

---

## 🔷 REFERENCE: KEY FILES

| Concern | Files |
|---------|-------|
| **Chat flow** | `routers/chat.py`, `services/chat_service.py` |
| **LangGraph** | `langgraph_services/chat_graph.py`, `graph_tracer.py` |
| **MCP tools** | `langgraph_services/mcp_tools.py`, `services/chat_data_supabase.py` (call_tool) |
| **Memory** | `chat_service.py` (context assembly), `chat_data_supabase.py` (get_recent_memory, get_messages) |
| **Model** | `langgraph_services/model_factory.py` |
| **UI** | `ChatInterface.tsx`, `SettingsPanel.tsx` |

---

*This document is the canonical system architecture for CTS. For setup and usage, see [README.md](../README.md) and [docs/](.).*
