# MCP Usage Guide – Sending Messages, Notes, IRCTC & More

Detailed guide to using MCP servers in CTS for messaging, note-taking, IRCTC train lookups, and other common tasks. Includes example prompts and backend flow.

---

## Troubleshooting: Tools Not Being Called

If prompts like "save a note with title X and description Y" don't invoke the tool:

1. **Use an API model (not Ollama)** – Select Gemini, OpenAI, Groq, or another API profile. Ollama/local Llama does not execute MCP tools; it streams text only.
2. **Add the MCP server** – Settings → MCP Servers → Add the Notes server at `http://localhost:8004/mcp`.
3. **Start the MCP server** – Run `cd mcp-servers/notes && python server.py` (or use the start script).

---

## Table of Contents

1. [Setup](#setup)
2. [Sending Messages](#sending-messages)
3. [Notes – Take, Store & Send Back](#notes--take-store--send-back)
4. [IRCTC – Train Search & Seat Availability](#irctc--train-search--seat-availability)
5. [Email Sending](#email-sending)
6. [Other Common Tasks](#other-common-tasks)
7. [Backend Flow – How Tools Are Invoked](#backend-flow--how-tools-are-invoked)
8. [Configuration Reference](#configuration-reference)

---

## Setup

### 1. Start the MCP servers

```powershell
.\scripts\start_all_mcps.ps1
```

Or start individual servers:

```bash
cd mcp-servers/whatsapp_business && python server.py   # Port 8024
cd mcp-servers/notes && python server.py              # Port 8004
cd mcp-servers/irctc && python server.py              # Port 8026
cd mcp-servers/email && python server.py              # Port 8014
```

### 2. Register in CTS

1. Open **Settings** (gear icon) → **MCP Servers** tab  
2. **Add Server**:
   - Name: e.g. `WhatsApp`, `Notes`, `IRCTC`, `Email`
   - URL: `http://localhost:8XXX/mcp` (replace XXX with port)
3. Click **List Tools** to confirm tools are discovered

---

## Sending Messages

### WhatsApp

**Tools:** `send_whatsapp_message`, `send_whatsapp_template`

**Configuration (`.env` or environment):**

```
WHATSAPP_ACCESS_TOKEN=your_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
```

Get credentials from [Meta Developer Console](https://developers.facebook.com/) → WhatsApp → API Setup.

**Example prompts:**

| Prompt | Tool used |
|--------|-----------|
| Send "Meeting at 3pm" to +919876543210 on WhatsApp | `send_whatsapp_message` |
| WhatsApp my friend 9876543210: Hey, call me back | `send_whatsapp_message` |
| Notify 91xxxxx about the summary | `send_whatsapp_message` |

**Parameters:**
- `to`: Phone with country code, e.g. `919876543210`
- `message`: Text body

---

### Email

**Tool:** `send_email`

**Configuration (for real sending):**

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=app_password
SMTP_FROM=your@gmail.com
```

Without these, the server runs in demo mode (no real emails sent).

**Example prompts:**

| Prompt | Tool used |
|--------|-----------|
| Email john@example.com: Subject "Report", body "See attached summary" | `send_email` |
| Send an email to myself with the meeting notes | `send_email` |

**Parameters:**
- `to`: Recipient address
- `subject`: Subject line
- `body`: Email body

---

## Notes – Take, Store & Send Back

**Tools:** `save_note`, `list_notes`, `get_notes_summary`

Notes are stored in **Supabase** `user_notes` (run migration `005_mcp_user_data.sql`). The chat service also writes directly to Supabase when `save_note` is called, so notes appear in **Settings → MCP Data → View Notes** even if the Notes MCP server uses its JSON fallback. The Notes server loads `.env` from the project root for `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

### Taking notes

| Prompt | Tool used |
|--------|-----------|
| Save a note: Meeting with client tomorrow 10am | `save_note` |
| Remember this: Project deadline is March 30 | `save_note` |
| Note down: Call Raj at 4pm | `save_note` |

**Parameters:**
- `title`: Short label (e.g. "Meeting reminder")
- `content`: Full note text

### Getting notes back

| Prompt | Tool used | What happens |
|--------|-----------|--------------|
| What are my notes? | `list_notes` | LLM shows titles + previews in chat |
| Show me everything I saved | `get_notes_summary` | LLM returns full content of all notes |
| Send my notes back to me | `get_notes_summary` | Same – full notes in response |
| Remind me what I noted down | `list_notes` or `get_notes_summary` | LLM shows your notes in chat |

### Sending notes to WhatsApp/Email

Use multiple tools in sequence. Example: *"Save a note about the project plan and send the summary to +919876543210 on WhatsApp"*

1. `save_note` – stores the note  
2. `get_notes_summary` or `list_notes` – reads content  
3. `send_whatsapp_message` – sends summary to phone  

The LLM chains these tools and returns the result in chat.

---

## IRCTC – Train Search & Seat Availability

**Tools:** `search_trains_between_stations`, `check_seat_availability`, `get_station_code`

**Configuration (live data):**

```
INDIAN_RAIL_API_KEY=your_key
```

Get API key from [Indian Rail API](https://indianrailapi.com/). Without it, the server uses demo data.

### Search trains between stations

| Prompt | Tool used |
|--------|-----------|
| Trains from Delhi to Kolkata | `search_trains_between_stations` |
| How to go from Mumbai to Bangalore by train? | `search_trains_between_stations` |
| Trains between NDLS and HWH on 2025-03-25 | `search_trains_between_stations` |

**Parameters:**
- `from_station`: Name (e.g. Delhi, Mumbai) or 3-letter code (NDLS, BCT)
- `to_station`: Same format
- `date`: Optional, YYYY-MM-DD

**Sample response:**
```
Trains between Delhi–Kolkata:
- 12301 RAJDHANI EXPRESS: Dep 16:55 | Arr 07:15 | 14:20H
- 12259 SHATABDI EXPRESS: Dep 06:00 | Arr 14:05 | 08:05H
```

### Check seat availability

| Prompt | Tool used |
|--------|-----------|
| Seat availability on 12301 from Delhi to Kolkata on 2025-03-22 | `check_seat_availability` |
| Are there 3AC seats on Rajdhani 12301 tomorrow? | `check_seat_availability` |
| Check 2A availability train 12259 Delhi Kolkata 2025-03-25 | `check_seat_availability` |

**Parameters:**
- `train_number`: e.g. `12301`
- `from_station`: Source
- `to_station`: Destination
- `date`: YYYY-MM-DD
- `class_code`: `1A`, `2A`, `3A`, `SL`, `CC`, `2S` (default `3A`)

**Sample response:**
```
Seat availability 12301 Delhi→Kolkata (3A):
- 2025-03-22: Available | Confirm: 100%
- 2025-03-23: GNWL12/WL5 | Confirm: 85%
```

### Station code lookup

| Prompt | Tool used |
|--------|-----------|
| What is the station code for New Delhi? | `get_station_code` |
| Code for Mumbai Central | `get_station_code` |

---

## Other Common Tasks

| Task | Server | Tools | Example prompt |
|------|--------|-------|-----------------|
| Recharge Jio | Jio Recharge | `search_jio_plans`, `recharge_jio` | Recharge my Jio number 9876543210 with ₹149 plan |
| Book flight | Flight Booking | `search_flights`, `book_flight` | Flights from NYC to London on 2025-04-01 |
| Book hotel | Hotel Booking | `search_hotels`, `book_hotel` | Hotels in Mumbai for 2 nights |
| Weather | Weather | `get_weather`, `get_forecast` | Weather in Mumbai tomorrow |
| Currency | Currency | `convert_currency`, `get_rates` | 100 USD to INR |
| Translate | Translator | `translate`, `list_languages` | Translate "Hello" to Hindi |
| Todo list | Todo | `add_todo`, `list_todos`, `complete_todo` | Add todo: Buy groceries |
| Reminder | Reminder | `set_reminder`, `list_reminders` | Remind me to call at 5pm |
| Calendar | Calendar | `create_event`, `list_events` | Create event: Meeting Friday 3pm |
| Search web | Search | `search` | Search for Python tutorials |
| Wikipedia | Wikipedia | `search_wikipedia` | Wikipedia article on Taj Mahal |

---

## Backend Flow – How Tools Are Invoked (LangChain + LangGraph)

```
User types prompt in chat
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  Chat Service (chat_service.py)                               │
│  1. Load user's MCP servers from mcp_servers table            │
│  2. Fetch tools for each server (tools/list via HTTP)        │
│  3. Build system prompt with RAG, memory, tool names          │
│  4. model_factory → LangChain chat model (OpenAI/Gemini)     │
│  5. mcp_tools.build_mcp_tools() → LangChain StructuredTools  │
│  6. create_chat_graph() → LangGraph StateGraph                │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  LangGraph: agent node (LLM with bind_tools)                  │
│  - Model returns AIMessage with tool_calls or plain text      │
└─────────────────────────────────────────────────────────────┘
         │
         ├── Plain text ───────────────────────────────────────► Stream to user
         │
         └── tool_calls ───────────────────────────────────────►
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  LangGraph: tools node (ToolNode)                            │
│  → ChatDataSupabase.call_tool(server_url, tool_name, args)   │
│  → POST {server_url}/mcp, method: "tools/call"                │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  MCP server executes tool, returns result                     │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  ToolMessage injected → agent node runs again (loop)          │
│  Recursion limit 25 until model returns text-only             │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  Final response streamed to user                              │
│  message_metadata stores: tools_used, external_dbs_used       │
└─────────────────────────────────────────────────────────────┘
```

### Relevant backend files

| File | Purpose |
|------|---------|
| `langgraph_services/model_factory.py` | Profile → ChatOpenAI / ChatGoogleGenerativeAI |
| `langgraph_services/mcp_tools.py` | MCP → StructuredTool, user context, dual-write |
| `langgraph_services/chat_graph.py` | StateGraph, agent ↔ tools loop, streaming |
| `services/chat_service.py` | Context assembly, RAG, memory, graph invocation |
| `services/chat_data_supabase.py` | `call_tool()` – MCP JSON-RPC `tools/call` |
| `tool_trigger_hints.py` | Keyword hints so the LLM picks the right tool |

### Tool discovery

1. Stored in `mcp_servers` table when you add a server in Settings  
2. `ChatService.stream_chat()` loads servers via `data.get_user_servers(user_id)`  
3. For each server, `data.list_tools_for_server(server_url)` sends JSON-RPC `tools/list`  
4. Tools are cached for 60 seconds  

### Tool execution (LangGraph)

1. Agent node: `llm.bind_tools(tools).invoke(messages)` – model returns AIMessage with optional `tool_calls`  
2. Conditional edge: if `tool_calls` present → route to tools node  
3. ToolNode invokes each tool → `data.call_tool(server_url, name, args)` → MCP `tools/call`  
4. ToolMessage(s) appended to state → agent node runs again  
5. Loop until model returns text-only → END  

---

## Where MCP Data Is Stored

| Server   | Storage File                                   | View in App                   |
|----------|------------------------------------------------|-------------------------------|
| **Notes**   | `mcp-servers/notes/notes.json`                 | Settings → MCP Data → View Notes |
| **Todo**   | `mcp-servers/todo/todos.json`                  | Settings → MCP Data → View Todos |
| **Reminder** | `mcp-servers/reminder/reminders.json`        | Settings → MCP Data → View Reminders |

Override paths with env vars: `MCP_NOTES_FILE`, `MCP_TODOS_FILE`, `MCP_REMINDERS_FILE`.

---

## Configuration Reference

### WhatsApp Business (8024)
```
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_API_VERSION=v21.0  # optional
```

### Email (8014)
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_FROM=  # optional, defaults to SMTP_USER
```

### Notes (8004)
```
MCP_NOTES_FILE=  # optional, default: mcp-servers/notes/notes.json
```

### IRCTC / Indian Rail (8026)
```
INDIAN_RAIL_API_KEY=  # from indianrailapi.com, for live train/seat data
```

---

---

## Flow – Where This Guide Fits

This guide describes **usage** of MCP tools in chat:

- **Setup**: Start MCP servers, register in Settings.
- **Prompts**: Example prompts that trigger specific tools (Notes, IRCTC, Email, etc.).
- **Backend**: How ChatService → model_factory → mcp_tools → LangGraph invokes tools.

For technical flow, see [TOOL_EXECUTION_FLOW.md](TOOL_EXECUTION_FLOW.md). For creating new servers, see [MCP_README.md](MCP_README.md).

---

## Contribution – Adding Examples

| Change | Action |
|--------|--------|
| Add example prompts for a tool | Add row to the relevant table (Notes, IRCTC, Email, etc.) |
| Add new server usage section | Add section with tools, config, example prompts |
| Update backend flow | Update "Backend Flow" diagram and file table |

---

## Troubleshooting

**"Tools Available: 0"**
- Ensure the MCP server is running (`python server.py`)
- Check the server URL includes `/mcp` (e.g. `http://localhost:8004/mcp`)
- Restart the API to clear tool cache

**WhatsApp / Email not sending**
- Check env vars in the shell that starts the MCP server
- For WhatsApp: verify token and phone number ID in Meta console

**IRCTC returns demo data**
- Set `INDIAN_RAIL_API_KEY` and restart the IRCTC server
- Use correct station codes or full names

**Notes not persisting**
- Ensure `mcp-servers/notes/` is writable
- Check `MCP_NOTES_FILE` path if overridden
