# CTS — End-to-End Workflow: From Sign-In to AI Response

> A complete trace of what happens when a user opens CTS, signs in, types a message, and receives an AI response — every layer, every file, every byte explained.

---

## Table of Contents

1. [Phase 1: Sign In → Session](#phase-1-sign-in--session)
2. [Phase 2: The Chat UI Loads](#phase-2-the-chat-ui-loads)
3. [Phase 3: User Types a Message](#phase-3-user-types-a-message)
4. [Phase 4: Message Leaves the Browser](#phase-4-message-leaves-the-browser)
5. [Phase 5: Backend Receives the Request](#phase-5-backend-receives-the-request)
6. [Phase 6: Context Assembly — The 4 Memories](#phase-6-context-assembly--the-4-memories)
7. [Phase 7: System Prompt Construction](#phase-7-system-prompt-construction)
8. [Phase 8: LangGraph Agent Execution](#phase-8-langgraph-agent-execution)
9. [Phase 9: Tool Execution (When Needed)](#phase-9-tool-execution-when-needed)
10. [Phase 10: The Agent Loop — Tools Back to Agent](#phase-10-the-agent-loop--tools-back-to-agent)
11. [Phase 11: Streaming Tokens Back to UI](#phase-11-streaming-tokens-back-to-ui)
12. [Phase 12: Frontend Parses the Stream](#phase-12-frontend-parses-the-stream)
13. [Phase 13: Persistence & Metadata](#phase-13-persistence--metadata)
14. [Phase 14: Debug Payload — Memory Indicators](#phase-14-debug-payload--memory-indicators)
15. [The Complete Data Flow Map](#the-complete-data-flow-map)

---

## Phase 1: Sign In → Session

### What happens when you open CTS

```mermaid
flowchart TD
    A["User opens localhost:3001"] --> B["page.tsx (root)"]
    B --> C{"Has Supabase session?"}
    C -->|Yes| D["Redirect → /app/chat"]
    C -->|No| E["Redirect → /login"]
    E --> F["Login form<br/>email + password"]
    F --> G["supabase.auth.signInWithPassword()"]
    G --> H["Supabase returns JWT + session"]
    H --> I["router.replace('/app/chat')"]
```

**Step-by-step:**

| Step | File | What Happens |
|------|------|-------------|
| 1 | [page.tsx](file:///c:/CTS/apps/web/src/app/page.tsx) | Root page checks `supabase.auth.getSession()`. No session → redirect `/login` |
| 2 | [login/page.tsx](file:///c:/CTS/apps/web/src/app/login/page.tsx) | Form rendered. User enters email + password |
| 3 | [supabase.ts](file:///c:/CTS/apps/web/src/lib/supabase.ts) | `createBrowserClient()` creates Supabase client using `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` |
| 4 | Supabase Auth | `signInWithPassword({ email, password })` → Supabase validates credentials → returns **JWT access token** |
| 5 | Browser | JWT stored automatically by `@supabase/ssr` in cookies. User redirected to `/app/chat` |

**The JWT** contains:
```json
{
  "sub": "user-uuid-here",
  "email": "user@example.com",
  "role": "authenticated",
  "exp": 1711180000
}
```

> **Why this matters:** Every single API call from this point forward includes this JWT as `Authorization: Bearer <token>`. The backend verifies it to know **who** is making the request.

---

## Phase 2: The Chat UI Loads

When `/app/chat` renders, [ChatInterface.tsx](file:///c:/CTS/apps/web/src/components/ChatInterface.tsx) mounts and fires 4 parallel API calls:

```mermaid
flowchart LR
    Mount["ChatInterface mounts"] --> A["loadProfiles()"]
    Mount --> B["loadOllama()"]
    Mount --> C["loadConversations()"]
    Mount --> D["loadCollections()"]
    
    A --> A1["GET /profiles → Model configs"]
    B --> B1["GET /ollama/models → Local LLMs"]
    C --> C1["GET /conversations → Chat history"]
    D --> D1["GET /documents/collections → RAG docs"]
```

**What each call fetches:**

| Call | Backend Endpoint | Returns | Used For |
|------|-----------------|---------|----------|
| [loadProfiles()](file:///c:/CTS/apps/web/src/components/ChatInterface.tsx#119-130) | `GET /profiles` | `[{id, display_name}]` | Model selector dropdown |
| [loadOllama()](file:///c:/CTS/apps/web/src/components/ChatInterface.tsx#131-139) | `GET /ollama/models` | `{available, models[], default_model}` | Ollama model group in dropdown |
| [loadConversations()](file:///c:/CTS/apps/web/src/components/ChatInterface.tsx#150-161) | `GET /conversations` | `[{id, title, created_at}]` | Sidebar chat history |
| [loadCollections()](file:///c:/CTS/apps/web/src/components/ChatInterface.tsx#162-170) | `GET /documents/collections` | `[{id, name}]` | RAG collection checkboxes |

**Every call goes through** [api.ts](file:///c:/CTS/apps/web/src/lib/api.ts):
```typescript
export async function getAuthHeaders(): Promise<HeadersInit> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  const headers: HeadersInit = { "Content-Type": "application/json" };
  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }
  return headers;
}
```

> Every request automatically extracts the JWT from the Supabase session and adds it as a Bearer token. The backend never serves data without verifying this token first.

---

## Phase 3: User Types a Message

The chat area has a `<textarea>` connected to React state:

```
┌─────────────────────────────────────────────────┐
│  [Model: GPT-4o ▾]  [RAG: ☐ My Docs]  [☐ Save to memory]  │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  Save a note: title=Meeting, content=   │   │  ← textarea (input state)
│  │  Discussed project architecture         │   │
│  └─────────────────────────────────────────┘   │
│                                        [Send]  │  ← triggers handleSubmit()
└─────────────────────────────────────────────────┘
```

**When user presses Enter or clicks Send:**

```typescript
// ChatInterface.tsx:213
async function handleSubmit(e: React.FormEvent) {
  const trimmed = input.trim();
  if (!trimmed || loading) return;

  // 1. Optimistically add user message to UI
  const userMessage = { id: crypto.randomUUID(), role: "user", content: trimmed };
  setMessages(prev => [...prev, userMessage]);
  
  // 2. Clear input, show loading
  setInput("");
  setLoading(true);
  
  // 3. Pre-create empty assistant bubble (will be filled by stream)
  const assistantId = crypto.randomUUID();
  setMessages(prev => [...prev, { id: assistantId, role: "assistant", content: "" }]);
```

> **Key UX decision:** The user message appears **immediately** (optimistic update). The assistant bubble is created empty and filled token-by-token as the stream arrives. This gives the "typing" effect.

---

## Phase 4: Message Leaves the Browser

### Building the Request

```typescript
// ChatInterface.tsx:232-251
const body = {
  message: "Save a note: title=Meeting, content=Discussed project architecture",
  conversation_id: "existing-conv-uuid" | null,  // null = new chat
  profile_id: "profile-uuid" | null,              // API model
  ollama_model: "llama3.1" | undefined,           // OR local model  
  save_to_memory: false,                          // checkbox state
  memory_kind: "fact",
  collection_ids: ["collection-uuid"] | undefined // RAG collections
};

// Send via SSE stream
const res = await fetch(`${apiBase}/chat/stream`, {
  method: "POST",
  headers: { "Authorization": "Bearer eyJhbG...", "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
```

### The HTTP request on the wire

```
POST /chat/stream HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...  ← Supabase JWT
Content-Type: application/json

{
  "message": "Save a note: title=Meeting, content=Discussed project architecture",
  "conversation_id": null,
  "profile_id": "d8f3a1b2-...",
  "save_to_memory": false,
  "collection_ids": []
}
```

> The frontend also has a **fallback mechanism**: if the Next.js proxy returns 503, it retries directly to `http://localhost:8000` (bypass proxy). This handles development scenarios where the proxy route isn't set up.

---

## Phase 5: Backend Receives the Request

```mermaid
flowchart TD
    A["POST /chat/stream"] --> B["chat.py router"]
    B --> C["get_current_user(token)"]
    C --> D{"JWT valid?"}
    D -->|No| E["401 Unauthorized"]
    D -->|Yes| F["Extract user_id from JWT"]
    F --> G["ChatService.stream_chat()"]
    G --> H["EventSourceResponse (SSE)"]
```

### Step 1: Authentication — [auth.py](file:///c:/CTS/services/api/src/auth.py)

```python
# 3-layer JWT verification:
# Try 1: HS256 with SUPABASE_JWT_SECRET
decoded = jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"])
# Try 2: RS256 with JWKS from Supabase (if HS256 fails)
# Try 3: Validate via /auth/v1/user endpoint (if both fail)

return {"id": decoded["sub"], "email": decoded.get("email")}  # user dict
```

### Step 2: Route Handler — [chat.py](file:///c:/CTS/services/api/src/routers/chat.py)

```python
@router.post("/stream")
async def stream_chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    sb = get_supabase_or_503()
    data = ChatDataSupabase(sb)

    async def event_generator():
        async for event in ChatService.stream_chat(
            data=data,
            user_id=user["id"],
            message=req.message,
            conversation_id=req.conversation_id,
            profile_id=req.profile_id,
            save_to_memory=req.save_to_memory,
            collection_ids=req.collection_ids,
        ):
            yield event

    return EventSourceResponse(event_generator())
```

### Step 3: Profile Resolution — [chat_service.py:371-393](file:///c:/CTS/services/api/src/services/chat_service.py#L371-L393)

```python
# If ollama_model is set → build local Ollama profile
# Otherwise → load profile from Supabase (model_profiles + model_profile_secrets)

profile = data.get_profile_with_api_key(profile_id, user_id)
# Returns: {provider_base_url, model_name, api_style, api_key}
# Example: {
#   "provider_base_url": "https://api.openai.com",
#   "model_name": "gpt-4o",
#   "api_style": "openai",
#   "api_key": "sk-..."
# }
```

### Step 4: Conversation Management

```python
# New chat → create conversation in Supabase
if not conversation_id:
    conv_id = data.create_conversation(user_id)  # returns new UUID

# Save user message to messages table
data.insert_message(conv_id, user_id, "user", message)
```

> From this point, the user's message is **persisted in Supabase**. Even if the LLM call fails, the conversation exists.

---

## Phase 6: Context Assembly — The 4 Memories

This is where the magic happens. Before calling the LLM, we assemble context from **all four memory types**.

```mermaid
flowchart TD
    subgraph "Phase 6: Context Assembly"
        A["User message received"]
        
        A --> M1["🟢 In-Context Memory<br/>Load last 20 messages<br/>from Supabase messages table"]
        A --> M2["🔵 External Memory<br/>Load memory_items<br/>(facts, preferences)<br/>from Supabase + 2min cache"]
        A --> M3["🟠 In-Weights Memory<br/>Selected LLM model<br/>(GPT-4, Gemini, Llama)"]
        A --> M4["🟣 In-Cache Memory<br/>Check TTL caches<br/>tools: 5min, memory: 2min<br/>+ prompt cache key"]
        A --> R["📄 RAG Search<br/>Vector similarity<br/>on selected collections"]
        A --> T["🔧 MCP Tool Discovery<br/>tools/list on each server<br/>(cached 5 minutes)"]
        
        M1 --> SP["System Prompt"]
        M2 --> SP
        M3 --> LLM["LLM Call"]
        M4 --> SP
        R --> SP
        T --> SP
        SP --> LLM
    end
```

### Memory 1: In-Context (Current Conversation)

```python
# chat_service.py:437-438
msg_rows = data.get_messages(conv_id, MAX_CONTEXT_MESSAGES + 1)  # last 20
messages_for_llm = [{"role": r["role"], "content": r["content"]} for r in msg_rows]
```

**SQL equivalent:** `SELECT role, content FROM messages WHERE conversation_id = $1 ORDER BY created_at LIMIT 21`

**Result:** `[{role: "user", content: "Hi"}, {role: "assistant", content: "Hello!"}, ...]`

### Memory 2: External (Cross-Session)

```python
# chat_service.py:421-428 — with In-Cache Memory (TTL cache)
cache_key = f"mem:{user_id}"
memory_cache_hit, memory_items = _cache_get(_memory_cache, cache_key, 120)  # 2min
if not memory_cache_hit:
    memory_items = data.get_recent_memory(user_id, limit=10)
    _cache_set(_memory_cache, cache_key, memory_items)
```

**What this returns:**
```python
[
    {"kind": "fact", "text": "User's name is Sanjay"},
    {"kind": "preference", "text": "User prefers Python over JavaScript"},
    {"kind": "summary", "text": "Previously discussed CTS project architecture"},
]
```

### Memory 3: In-Weights (Model's Knowledge)

The model itself contains knowledge from pre-training. We select which model via [model_factory.py](file:///c:/CTS/services/api/src/langgraph_services/model_factory.py):

```python
def create_chat_model_from_profile(profile, temperature=0.7, streaming=True):
    if api_style == "gemini":
        return ChatGoogleGenerativeAI(model=model, max_retries=2)
    return ChatOpenAI(model=model, api_key=api_key, base_url=base_url, max_retries=2)
```

### Memory 4: In-Cache (Computational Reuse)

```python
# Tool list cache — avoids calling tools/list every message
cache_key = f"tools:{srv_id}"
hit, cached_tools = _cache_get(_tool_list_cache, cache_key, 300)  # 5min TTL
if not hit:
    tools = await data.list_tools_for_server(srv_url)  # JSON-RPC over httpx
    _cache_set(_tool_list_cache, cache_key, tools)

# Prompt cache key for OpenAI KV cache
cache_key_prefix = f"tools:{tool_list[:2000]}"  # Stable hash → API reuse
```

### RAG Search (If Collections Selected)

```python
# chat_service.py:410-419
rag_results = data.search_rag(user_id, collection_ids, message, limit=5)
# Calls match_document_chunks RPC → pgvector cosine similarity
# Returns top-5 relevant text chunks from user's uploaded documents
```

---

## Phase 7: System Prompt Construction

All memories are combined into one **system prompt** — carefully ordered for KV cache efficiency:

```python
# LAYER 1: Static base (always cached)
system_prompt = """You are a helpful AI assistant with agentic memory.
MEMORY: In-context (recent msgs), external (past sessions), in-weights (knowledge).
Prefer tools for live data."""

# LAYER 2: Available resources from MCP servers
system_prompt += "\n\n[Available resources]:\n- notes://..."

# LAYER 3: Tool definitions + few-shot examples + trigger hints
system_prompt += """
[TOOLS] You have tools. Call them when the user requests an action.

EXAMPLE 1 - User: 'save my name Alex as title and what you think as content'
→ You call save_note with title='Alex', content='<one sentence>'

- save_note: Save a note with title and content
- list_notes: List all saved notes
- add_todo: Add a todo item
- set_reminder: Set a reminder
...
"""

# LAYER 4: External memory (changes slowly — may be cached 2min)
system_prompt += """
[External memory - from previous sessions]:
- [fact] User's name is Sanjay
- [preference] User prefers Python
"""

# LAYER 5: RAG context (changes every message — never cached)
system_prompt += """
[RAG - user documents]:
- Chapter 3: Project architecture uses microservices...
- Chapter 5: Database design follows star schema...
"""
```

> **Architecture insight:** Static content first, variable content last. This maximizes OpenAI's prompt cache and KV cache hits — the model skips recomputing attention for the unchanging prefix.

---

## Phase 8: LangGraph Agent Execution

Now the assembled context goes to the LangGraph `StateGraph`:

```python
# chat_service.py:559-563
graph = create_chat_graph(profile, tools_with_server, data, user_id, conv_id, cache_key_prefix)
async for event in stream_chat_with_graph(graph, system_prompt, messages_for_llm, tools_executed, tracer):
    yield event
```

### Graph Creation — [chat_graph.py:136-197](file:///c:/CTS/services/api/src/langgraph_services/chat_graph.py#L136-L197)

```python
def create_chat_graph(profile, tools_with_server, data, user_id, conv_id):
    # 1. Create LLM from profile
    llm = create_chat_model_from_profile(profile, streaming=True, max_retries=2)
    
    # 2. Wrap MCP tools as LangChain StructuredTools
    tools = build_mcp_tools(tools_with_server, data, user_id, conv_id)
    
    # 3. Bind tools to LLM (enables function calling)
    llm_with_tools = llm.bind_tools(tools) if tools else llm
    
    # 4. Define the agent node (async!)
    async def agent_node(state):
        response = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}
    
    # 5. Build the graph
    builder = StateGraph(GraphState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", _should_continue)  # → tools or END
    builder.add_edge("tools", "agent")                         # tools → agent (loop)
    return builder.compile()
```

### What the LLM sees (the full message list):

```python
[
    SystemMessage(content="You are a helpful AI... [TOOLS] save_note, list_notes..."),
    HumanMessage(content="Hi, what's 2+2?"),          # In-context memory
    AIMessage(content="That's 4!"),                    # In-context memory
    HumanMessage(content="Save a note: title=Meeting, content=Discussed architecture"),  # Current
]
```

### The LLM responds:

For our example message "Save a note: title=Meeting, content=Discussed architecture", the LLM returns:

```python
AIMessage(
    content="",  # Empty when doing a tool call
    tool_calls=[{
        "id": "call_abc123",
        "name": "save_note",
        "args": {"title": "Meeting", "content": "Discussed architecture"}
    }]
)
```

> The LLM decided: "The user wants to save a note → I should call the [save_note](file:///c:/CTS/mcp-servers/notes/server.py#94-118) tool." This decision is powered by the tool definitions we bound and the few-shot examples in the system prompt.

---

## Phase 9: Tool Execution (When Needed)

### Routing Decision

```python
# chat_graph.py:122-133
def _should_continue(state):
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"   # ← We go here! The LLM wants to call a tool
    return END
```

### ToolNode executes the tool

LangGraph's `ToolNode` automatically:
1. Reads `tool_calls` from the `AIMessage`
2. Finds the matching `StructuredTool` by name ("save_note")
3. Calls it with the args: [save_note(title="Meeting", content="Discussed architecture", user_id="user-uuid")](file:///c:/CTS/mcp-servers/notes/server.py#94-118)

### MCP Tool Execution — the tool wrapper calls the MCP server

```python
# mcp_tools.py — the wrapped function
async def call_fn(**kwargs):
    kwargs["user_id"] = user_id        # Auto-injected context
    kwargs["conversation_id"] = conv_id  # Auto-injected context
    result = await data.call_tool(server_url, "save_note", kwargs)
    return f"[TOOL_OUTPUT: save_note]\n{result}"
```

### JSON-RPC call to MCP Server — [mcp_client.py](file:///c:/CTS/services/api/src/services/mcp_client.py)

```python
# Uses the shared httpx.AsyncClient (connection pooling!)
async def call_tool(server_url: str, tool_name: str, arguments: dict) -> str:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments}
    }
    response = await _shared_client.post(f"{server_url}/mcp", json=payload)
    # Parse result from JSON-RPC response
    return result["content"][0]["text"]  # "Saved note: Meeting"
```

### MCP Server processes the request — [notes/server.py](file:///c:/CTS/mcp-servers/notes/server.py)

```python
# Inside the Notes MCP server (port 8004):
@mcp.tool()
def save_note(title: str, content: str, user_id: str = "", conversation_id: str = ""):
    sb = _get_sb()  # Cached Supabase client
    sb.table("user_notes").insert({
        "user_id": user_id,
        "title": title,
        "content": content,
        "conversation_id": conversation_id
    }).execute()
    return f"Saved note: {title}"
```

> **What just happened:** The AI decided to call a tool → LangGraph routed to ToolNode → ToolNode called our MCP wrapper → The wrapper made a JSON-RPC call to the Notes server → The Notes server saved to Supabase → The result "Saved note: Meeting" travels all the way back.

---

## Phase 10: The Agent Loop — Tools Back to Agent

After the tool executes, **the result goes back to the agent**:

```mermaid
flowchart TD
    A["Agent (Round 1)"] -->|"AIMessage(tool_calls=[save_note])"|B["ToolNode"]
    B -->|"ToolMessage('Saved note: Meeting')"|C["Agent (Round 2)"]
    C -->|"AIMessage('I saved your note titled Meeting!')"|D["END"]
```

### State after tool execution:

```python
messages = [
    SystemMessage("You are a helpful AI..."),
    HumanMessage("Save a note: title=Meeting, content=..."),
    AIMessage("", tool_calls=[{name: "save_note", ...}]),    # Round 1
    ToolMessage("Saved note: Meeting"),                        # Tool result
    # → Agent runs again with this full context
]
```

### Agent Round 2:

The LLM now sees the tool result in context. It generates a **natural language confirmation**:

```python
AIMessage(content="I've saved your note titled 'Meeting' with the content about your project architecture discussion. ✅")
```

Since this message has **no `tool_calls`**, [_should_continue()](file:///c:/CTS/services/api/src/langgraph_services/chat_graph.py#122-134) returns `END` and the graph completes.

---

## Phase 11: Streaming Tokens Back to UI

### LangGraph's astream_events

```python
# chat_graph.py:227-250
async for event in graph.astream_events({"messages": lc_messages}, version="v2"):
    if event["event"] == "on_tool_start":
        yield {"data": json.dumps({"type": "tool_start", "tool": "save_note"})}
    
    elif event["event"] == "on_chat_model_stream":
        text = chunk.content  # Token from LLM
        yield {"data": json.dumps({"type": "text", "content": "I've"})}
        yield {"data": json.dumps({"type": "text", "content": " saved"})}
        yield {"data": json.dumps({"type": "text", "content": " your"})}
        # ... token by token
    
    elif event["event"] == "on_tool_end":
        yield {"data": json.dumps({"type": "tool_done", "tool": "save_note"})}
```

### SSE stream on the wire:

```
data: {"type":"tool_start","tool":"save_note"}

data: {"type":"tool_done","tool":"save_note"}

data: {"type":"text","content":"I've"}

data: {"type":"text","content":" saved"}

data: {"type":"text","content":" your"}

data: {"type":"text","content":" note"}

data: {"type":"text","content":" titled"}

data: {"type":"text","content":" 'Meeting'"}

data: {"type":"text","content":" ✅"}

data: {"type":"debug","memory":{"in_context_messages":3,"external_memory_items":2,"memory_cache_hit":true,"tool_cache_hits":1,"tools_available":8,"tools_used":["save_note"]}}

data: {"type":"done","conversation_id":"conv-uuid-here"}
```

---

## Phase 12: Frontend Parses the Stream

### ReadableStream processing — [ChatInterface.tsx:285-354](file:///c:/CTS/apps/web/src/components/ChatInterface.tsx#L285-L354)

```typescript
const reader = res.body?.getReader();
const decoder = new TextDecoder();
let buffer = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split("\n");
  buffer = lines.pop() || "";  // Keep incomplete line in buffer
  
  for (const line of lines) {
    if (line.startsWith("data: ")) {
      const parsed = JSON.parse(line.slice(6));
      
      switch (parsed.type) {
        case "text":
          // Append token to assistant bubble
          fullContent += parsed.content;
          setMessages(prev => prev.map(m => 
            m.id === assistantId ? { ...m, content: fullContent } : m
          ));
          break;
          
        case "tool_start":
          // Show "Calling save_note..." indicator
          setToolStatus(`Calling ${parsed.tool}...`);
          break;
          
        case "tool_done":
          setToolStatus(null);
          break;
          
        case "debug":
          // Display memory indicators panel
          setMemoryDebug(parsed.memory);
          break;
          
        case "done":
          // Save conversation_id, reload sidebar
          setConversationId(parsed.conversation_id);
          loadConversations();
          break;
          
        case "error":
          // Remove optimistic messages, restore input
          setMessages(prev => prev.filter(m => m.id !== userMessage.id && m.id !== assistantId));
          setInput(userMessage.content);  // Give message back to user
          break;
      }
    }
  }
}
```

> **Key UX patterns:**
> - **Token-by-token rendering:** Each [text](file:///c:/CTS/services/api/src/langgraph_services/mcp_tools.py#110-129) event updates the assistant message progressively — giving the "typing" effect
> - **Tool status:** When a tool is executing, the UI shows "Calling save_note..." with a pulsing animation
> - **Error recovery:** On error, the UI removes both optimistic messages and puts the input back in the textarea — the user never loses their message

---

## Phase 13: Persistence & Metadata

After streaming completes, the backend **persists everything**:

```python
# chat_service.py:624-674

# 1. Save assistant response
msg_id = data.insert_message(conv_id, user_id, "assistant", full_content)

# 2. Auto-generate chat title (only for new conversations)
if created_new:
    title = await ChatService._generate_chat_title(
        client, base_url, model, api_key, api_style,
        first_message=message,
        assistant_preview=full_content[:200],
    )
    data.update_conversation_title(conv_id, user_id, title)

# 3. Save detailed metadata for tracing
data.save_message_metadata(
    msg_id, conv_id,
    tools_used=["save_note"],
    external_dbs_used=["My Documents"],
    in_context_count=3,
    prompt_trace={
        "system_prompt_preview": system_prompt[:500],
        "rag_chunks": 0,
        "memory_items": 2,
        "tools_available": 8,
        "memory_cache_hit": True,
        "graph_steps": [...],       # From GraphTracer
        "mermaid": "flowchart TD..."  # Execution diagram
    },
    model_used="gpt-4o"
)

# 4. Save to memory if user checked "Save to memory"
if save_to_memory:
    data.create_memory_item(user_id, "fact", full_content[:500], conv_id)
```

> **Why metadata matters:** The UI has a "View trace" button on every assistant message. Clicking it fetches this metadata and shows the exact system prompt, which tools were called, how many RAG chunks were used, and a Mermaid flowchart of the execution path. This is **invaluable for debugging and demonstrating** the system.

---

## Phase 14: Debug Payload — Memory Indicators

The last two SSE events the UI receives:

```json
// Debug event — shows memory panel in UI
{
  "type": "debug",
  "memory": {
    "in_context_messages": 3,
    "external_memory_items": 2,
    "memory_cache_hit": true,
    "tool_cache_hits": 1,
    "tools_available": 8,
    "tools_used": ["save_note"],
    "external_dbs_used": [],
    "rag_chunks_retrieved": 0
  }
}

// Done event — finalizes the response
{
  "type": "done",
  "conversation_id": "b4c9e2c7-1c4c-5c2b-ac2b-..."
}
```

**The UI renders this as:**

```
┌──────────────────────────────────────────────┐
│  Memory Used (This Response)                 │
│                                              │
│  In-Context:       3 messages                │
│  External Memory:  2 items                   │
│  In-Cache Hit:     Yes                       │
│  Tools Available:  8                         │
│  Tools Used:       save_note                 │
└──────────────────────────────────────────────┘
```

> This panel proves to the user (and to an interviewer) that **all four memory types are actively participating** in every response.

---

## The Complete Data Flow Map

```mermaid
flowchart TD
    subgraph "BROWSER (Next.js)"
        U["User types message"]
        U --> F1["handleSubmit()"]
        F1 --> F2["Optimistic UI update"]
        F2 --> F3["fetch('/chat/stream', SSE)"]
        F3 --> F4["ReadableStream.read() loop"]
        F4 --> F5["Parse SSE events"]
        F5 --> F6["Update React state per event"]
        F6 --> F7["Render: markdown, tool status, memory panel"]
    end

    subgraph "BACKEND (FastAPI)"
        F3 -->|"POST + JWT"| B1["auth.py: verify JWT"]
        B1 --> B2["chat.py: route handler"]
        B2 --> B3["ChatService.stream_chat()"]
        
        subgraph "Context Assembly"
            B3 --> C1["In-Context: get_messages(20)"]
            B3 --> C2["External: get_recent_memory(10)"]
            B3 --> C3["RAG: search_rag(collections)"]
            B3 --> C4["Tools: list_tools (cached)"]
        end
        
        B3 --> B4["Build system prompt"]
        B4 --> B5["create_chat_graph()"]
    end

    subgraph "LANGGRAPH"
        B5 --> G1["agent_node: llm.ainvoke()"]
        G1 --> G2{"tool_calls?"}
        G2 -->|Yes| G3["ToolNode: execute tool"]
        G3 -->|JSON-RPC| MCP["MCP Server"]
        MCP -->|result| G3
        G3 --> G1
        G2 -->|No| G4["Stream tokens"]
    end

    subgraph "SUPABASE"
        C1 -.->|read| DB["PostgreSQL 15 tables"]
        C2 -.->|read| DB
        C3 -.->|pgvector| DB
        MCP -.->|write| DB
        G4 --> P1["Persist message"]
        P1 -.->|write| DB
    end

    G4 -->|SSE events| F4

    style U fill:#4CAF50,color:#fff
    style G1 fill:#FF9800,color:#fff
    style MCP fill:#2196F3,color:#fff
    style DB fill:#9C27B0,color:#fff
```

---

## Summary: What Makes This Special

| Feature | How We Built It | Why It Matters |
|---------|----------------|----------------|
| **4 Memory Types** | In-context (20 msgs), External (Supabase), In-weights (multi-model), In-cache (TTL + prompt cache) | Full agentic memory — not just chat history |
| **LangGraph Agent** | `StateGraph` with async `ainvoke`, Ollama fallback parser, 6-round cap | Proper agent loop, not a single LLM call |
| **26 MCP Servers** | JSON-RPC via shared `httpx.AsyncClient`, cached tool discovery | Real tool execution, not simulated |
| **SSE Streaming** | `astream_events v2`, token-by-token, tool status events | ChatGPT-quality UX |
| **Execution Tracing** | GraphTracer → Mermaid diagrams, metadata per message | Debuggable, demonstrable |
| **Multi-Model** | ModelFactory: OpenAI, Gemini, Ollama, Groq, OpenRouter | Any LLM works |
| **Data Security** | RLS on every table, JWT verification, per-user isolation | Enterprise-grade |
