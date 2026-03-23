# Tool Execution Flow

How MCP tools are invoked via LangChain/LangGraph and integrated into the chat response.

---

## Overview

| Component | Role |
|-----------|------|
| **LangGraph** | Orchestrates agent ↔ tools loop; routes tool_calls to ToolNode |
| **Model Factory** | Creates LangChain chat model (ChatOpenAI, ChatGoogleGenerativeAI) from CTS profile |
| **MCP Tools Adapter** | Wraps MCP tools as LangChain StructuredTools; injects user_id, conversation_id |
| **ToolNode** | Executes tools; calls ChatDataSupabase.call_tool() → MCP JSON-RPC |
| **MCP Servers** | Run tools; persist to Supabase or JSON |

---

## Flow (Step by Step)

```
1. ChatService receives user message
2. Loads MCP tools from registered servers (tools/list)
3. model_factory.create_chat_model_from_profile(profile) → ChatOpenAI / ChatGoogleGenerativeAI
4. mcp_tools.build_mcp_tools(tools_with_server, data, user_id, conv_id) → [StructuredTool, ...]
5. create_chat_graph(profile, tools, data, user_id, conv_id) → compiled StateGraph
6. stream_chat_with_graph(graph, system_prompt, messages) →
   - agent node: llm.bind_tools(tools).invoke(messages)
   - if AIMessage has tool_calls → route to tools node
   - tools node: ToolNode invokes each tool → calls data.call_tool(server_url, name, args)
   - data.call_tool → POST {server_url}/mcp, method: "tools/call", params: {name, arguments}
   - MCP server runs tool, returns result
   - result → ToolMessage → back to agent node (loop)
   - when no tool_calls → END → stream final text
7. SSE events: tool_start, tool_done, text chunks, debug, done
```

---

## MCP JSON-RPC (tools/call)

```
POST {server_url}/mcp
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "get_weather",
    "arguments": {"city": "London"}
  }
}
```

- **Response**: `result.content[].text` concatenated
- **On error**: `error.message` or `result.isError` → error string injected so LLM can retry

---

## User Context Injection

For notes, todos, and reminders, the backend injects `user_id` and `conversation_id` into tool args (see `mcp_tools._inject_user_context`). This ensures:

- Notes/todos are stored per user in Supabase `user_notes` / `user_todos`
- They appear in **Settings → MCP Data → View Notes / View Todos**

---

## Dual-Write (Notes & Todos)

When `save_note` or `add_todo` runs:

1. MCP tool executes (Notes/Todo server writes to Supabase or JSON)
2. `mcp_tools._invoke` also calls `data.save_note_direct()` / `data.add_todo_direct()` so data appears in MCP Data even if the MCP server uses a JSON fallback

---

## Relevant Code

| File | Purpose |
|------|---------|
| `langgraph_services/model_factory.py` | Profile → LangChain chat model |
| `langgraph_services/mcp_tools.py` | MCP → StructuredTool, user context, dual-write |
| `langgraph_services/chat_graph.py` | StateGraph, agent node, ToolNode, streaming |
| `services/chat_data_supabase.py` | `call_tool()` – MCP JSON-RPC `tools/call` |
| `tool_trigger_hints.py` | Keyword hints so LLM picks the right tool |

---

## Contribution – How to Extend Tool Execution

| Change | Where to edit |
|--------|----------------|
| Add a new model provider (Anthropic, etc.) | `model_factory.py` – add branch in `create_chat_model_from_profile()` |
| Change how tools are wrapped | `mcp_tools.py` – `build_mcp_tools()`, `_invoke` wrapper |
| Adjust agent loop (e.g. max tools per turn) | `chat_graph.py` – `create_chat_graph()`, recursion limit |
| Fix MCP JSON-RPC behavior | `chat_data_supabase.py` – `call_tool()` |
| Add keywords so LLM picks a tool | `tool_trigger_hints.py` – extend `TOOL_TRIGGER_HINTS` |
