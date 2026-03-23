# Message Handling & MCP Data UI – Progress

Documentation of scenarios handled and implementation status.

---

## Rate Limit Handling (Mar 2025)

| Scenario | Backend | Frontend |
|----------|---------|----------|
| **429 from LLM API** | `LLMRateLimitError` with `retry_after_seconds` from `Retry-After` header | Shows banner "Retry in Xs", disables Send, countdown |
| **429 in error text** | Fallback: add `retry_after_seconds: 60` | Same as above |
| **Quota exceeded** | Same fallback | Same as above |

- `chat_service.py`: `_parse_retry_after(resp)`, `LLMRateLimitError`, 429 handling in LangGraph stream flow (`stream_chat_with_graph`)
- Frontend: `rateLimitError` state, countdown `useEffect`, Send button shows "Wait Xs" when limited

---

## MCP Data Endpoint Hardening (ECONNRESET fix)

- `/mcp/data/notes`, `/data/todos`, `/data/reminders`: Always return from Supabase on success (even empty). Never block on MCP.
- `_safe_notes`, `_safe_todos`, `_safe_reminders`: Wrapped in try/except. MCP fallback wrapped. Never raise.
- If migration `005_mcp_user_data.sql` not run: returns `{"items": [], "error": "..."}` instead of crashing.
- Run migration in Supabase SQL editor for per-user notes/todos/reminders.

---

## MCP Data UI (Notes, Todos, Reminders)

### Implemented

| Feature | Status |
|---------|--------|
| **Title-only list** | ✓ Each view shows items as clickable titles |
| **Popup on click** | ✓ Modal with full description, created_at, metadata |
| **Notes** | ✓ title, content, created_at in popup |
| **Todos** | ✓ task, priority, done status, created_at in popup |
| **Reminders** | ✓ text, when, created_at in popup |
| **Structured API** | ✓ `list_notes_json`, `list_todos_json`, `list_reminders_json` return JSON |
| **Storage paths** | ✓ Shown in UI: notes.json, todos.json, reminders.json |

### MCP Server Changes

- **Notes**: `list_notes_json()` tool; `created_at` on new saves
- **Todo**: `list_todos_json()` tool; `created_at` on new saves
- **Reminder**: `list_reminders_json()` tool; `created_at` on new saves

---

## Message Handling (Rate Limit / Failed Responses)

### Scenarios Handled

| Scenario | Backend | Frontend |
|----------|---------|----------|
| **New conversation, LLM fails** | Delete entire conversation (cascade messages) | Clear last user + assistant, restore input |
| **Existing conversation, LLM fails** | Delete last user message only | Clear last user + assistant, restore input |
| **HTTP error before stream** (401, 500) | N/A (no message persisted yet for new; for existing see below) | Clear last user + assistant, restore input |
| **Stream returns type "error"** | Same as above – delete conv or last user msg | Clear last user + assistant, restore input |
| **User retries after failure** | Clean context – no orphan user messages | Input restored; user can edit and retry |

### Why Duplicates Occurred

1. User sends message → backend inserts user message
2. LLM call fails (e.g. 429)
3. **Before**: User message stayed in DB; next send added another message
4. **After**: Last user message is deleted on failure
5. Frontend clears failed attempt and restores message to input for retry

### Backend Logic

```
On exception:
  if created_new:
    delete_conversation(conv_id)   # Remove entire conversation
  else:
    delete_last_user_message(conv_id, user_id)   # Remove orphan user message
```

### Frontend Logic

```
On error (stream type "error" or fetch exception):
  messages = messages.filter(m => m.id !== lastUserMsg.id && m.id !== assistantId)
  input = lastUserMessage.content   # Restore for retry
```

---

## Edge Cases Considered

| Case | Handling |
|------|----------|
| **Multiple rapid retries** | Each failure clears that attempt; only successful messages remain |
| **Network error mid-stream** | Caught in catch block; same clear + restore |
| **429 on first message of new chat** | Conversation deleted; next send creates new conv |
| **429 on continuation** | Last user message deleted; conversation keeps prior messages |
| **User modifies input before retry** | Restored input can be edited; next send uses modified text |

---

---

## Flow – How Message Handling & MCP Data Work

```
User sends message → backend inserts user message
         │
         ├── Success: LLM returns → assistant message saved → metadata (tools_used, etc.)
         │
         └── Failure (429, 500, etc.):
                   │
                   ├── New conversation → delete entire conversation
                   ├── Existing conversation → delete last user message only
                   └── Frontend: clear failed messages, restore input for retry

MCP Data (Notes, Todos, Reminders):
  save_note / add_todo → MCP server + dual-write to Supabase
  → Settings → MCP Data → View Notes / View Todos
```

---

## Contribution – Message & MCP Data Changes

| Change | Where to edit |
|--------|----------------|
| Rate limit handling | `chat_service.py` – `_parse_retry_after`, `LLMRateLimitError` |
| Delete on failure | `chat_service.py` – exception handler, `data.delete_last_user_message()` |
| MCP Data UI layout | `apps/web/src/components/SettingsPanel.tsx` |
| Notes/todos dual-write | `langgraph_services/mcp_tools.py` – `_invoke` for save_note/add_todo |
| Migration for user notes/todos | `supabase/migrations/005_mcp_user_data.sql` |

---

## Files Changed

| File | Changes |
|------|---------|
| `mcp-servers/notes/server.py` | `list_notes_json`, `created_at` on save |
| `mcp-servers/todo/server.py` | `list_todos_json`, `created_at` on save |
| `mcp-servers/reminder/server.py` | `list_reminders_json`, `created_at` on save |
| `services/api/src/routers/mcp.py` | Return `{items, storage}` from /data/notes, /todos, /reminders |
| `services/api/src/services/chat_data_supabase.py` | `delete_last_user_message()` |
| `services/api/src/services/chat_service.py` | Call delete_last_user_message on error for existing conv |
| `apps/web/src/components/SettingsPanel.tsx` | Title list + metadata popup for MCP Data |
| `apps/web/src/components/ChatInterface.tsx` | Clear failed messages and restore input on error |
