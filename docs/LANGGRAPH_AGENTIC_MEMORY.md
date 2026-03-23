# LangGraph & Agentic Memory in CTS

CTS implements a Mini ChatGPT-style interface with all four agentic memory types and MCP tool support via LangChain and LangGraph.

---

## Architecture

```
User Message
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  ChatService (context assembly)                                  │
│  • In-Context: Last 20 messages from conversation                 │
│  • External: memory_items from Supabase (cached 30s)              │
│  • RAG: document_chunks if collections selected                    │
│  • In-Cache: Tool list cache (60s), memory cache (30s)             │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  LangGraph StateGraph                                             │
│  START → agent (LLM + bind_tools) → [tools?] → agent (loop) → END │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  ToolNode: MCP tools/call JSON-RPC                                │
│  • Parallel execution when multiple tool_calls                    │
│  • Result truncation at 12K chars for speed                       │
│  • Dual-write for save_note/add_todo → Supabase                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Four Memory Types

| Type | Implementation | Where |
|------|----------------|-------|
| **In-Context** | Last N messages in conversation | `chat_data_supabase.get_messages()`, `MAX_CONTEXT_MESSAGES=20` |
| **External** | `memory_items` table (facts, preferences, summaries) | `chat_data_supabase.get_recent_memory()`, Settings → Save to memory |
| **In-Weights** | Model's parameters | No code – use any LLM |
| **In-Cache** | In-memory cache for tool lists (60s) and memory (30s) | `_tool_list_cache`, `_memory_cache` in `chat_service.py` |

---

## Multi-Tool Chains & Saving Results

When the user asks to **save the result** (e.g. "Search for X and save the summary to a note"):

1. **System prompt** instructs the agent to first get data, then call `save_note`/`add_todo`.
2. **Tool trigger hints** include explicit multi-tool chain guidance.
3. **LangGraph** loops: Agent → ToolNode → Agent until the model returns text-only.

---

## Flow Visualization

- **Graph tracer** (`graph_tracer.py`): Captures agent rounds and tool invocations from `astream_events`.
- **Prompt trace** stores `graph_steps` and `mermaid` flowchart.
- **View trace** in chat shows step-by-step execution and Mermaid diagram.

---

## Optional: LangSmith

For cloud trace visualization:

1. Sign up at [smith.langchain.com](https://smith.langchain.com)
2. Add to `.env`:
   ```env
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=your_key
   LANGSMITH_PROJECT=cts
   ```
3. Restart the API. Traces appear in the LangSmith dashboard.

---

## Performance

- **Tool result truncation**: Results > 12K chars are truncated to avoid context overflow and speed up parsing.
- **Caching**: Tool lists 60s, memory 30s to reduce MCP and DB calls.
- **Recursion limit**: 25 agent/tool rounds per request.
- **Streaming**: `astream_events` version `v2` for token and tool streaming.
