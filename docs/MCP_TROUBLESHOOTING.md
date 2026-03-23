# MCP Troubleshooting & Detailed Overview

## Why "Tools Available: 0"?

The **Tools Available** count comes from MCP servers you have **registered in Settings**. If it shows 0, one or more of these is wrong:

| Check | What to do |
|-------|------------|
| **No servers added** | Open **Settings** → **MCP Servers** → Add at least one server |
| **Wrong URL** | Use `http://localhost:8XXX/mcp` (e.g. `http://localhost:8014/mcp` for Email) |
| **MCP server not running** | Start it: `cd mcp-servers/email && python server.py` |
| **Port conflict** | Ensure no other app uses the same port |

### Step-by-step to get tools working

1. **Start an MCP server** (e.g. Calculator on port 8002):
   ```powershell
   cd C:\CTS\mcp-servers\calculator
   pip install mcp
   python server.py
   ```
   Wait for: `Uvicorn running on http://0.0.0.0:8002`

2. **Add it in CTS**:
   - Open **Settings** (gear icon) → **MCP Servers** tab
   - **Name:** `Calculator`
   - **Server URL:** `http://localhost:8002/mcp`
   - Click **Add Server**

3. **Verify**: Click **List Tools** next to the server. You should see `add`, `multiply`, `power`.

4. **Chat**: Ask "What is 15 * 27?" – the LLM will see and can execute tools via LangGraph. See [Tool Execution](TOOL_EXECUTION_FLOW.md).

---

## Why http://localhost:8014/mcp "Doesn't Open"

The MCP endpoint is **not a webpage**. It expects **POST** requests with JSON-RPC, not browser GET.

- **Browser**: Typing the URL does a GET → MCP may return nothing or an error
- **Correct usage**: The CTS backend POSTs `{"method":"tools/list",...}` to fetch tools

**To test if the server is running:**

```powershell
# PowerShell - test Email MCP (port 8014). Must include Accept header.
$headers = @{"Content-Type"="application/json"; "Accept"="application/json"}
Invoke-RestMethod -Uri "http://localhost:8014/mcp" -Method POST -Headers $headers -Body '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

If the server is running, you'll get JSON with `result.tools`. 

**"Missing session ID"**: All CTS MCP servers use `stateless_http=True`, so no session is needed. Restart the MCP server after pulling the latest code.

---

## Calculations: Why the LLM Does It Itself

LLMs can do simple math **without tools**. For "15 * 27", the model computes 405 directly. That's expected.

- **Calculator MCP** is useful for: complex expressions, unit conversions, or when you want the result to come from a tool
- **Tool vs native**: The model may choose either; it's not wrong if it uses its own math

---

## Public APIs & Real Tasks (Jio Recharge, etc.)

### Current state

- **Flight, Hotel, Currency, Email, etc.**: Demo/mock implementations. They return placeholder text, not real bookings.
- **Jio Recharge**: No MCP exists yet. To support it, you need:
  1. A **Jio/Recharge API** (e.g. A1Topup, Paytm, Enginify)
  2. An **MCP server** that calls that API
  3. **API keys** stored securely (env vars, Supabase secrets)

### How to add real Jio Recharge

1. **Create MCP** `mcp-servers/jio_recharge/`:
   - `search_plans(amount: int)` – list plans (e.g. ₹19)
   - `recharge(mobile: str, plan_id: str, amount: float)` – perform recharge

2. **Use API key** from env:
   ```python
   import os
   API_KEY = os.environ.get("JIO_RECHARGE_API_KEY", "")
   ```

3. **Wire to real API** (example with A1Topup-style):
   ```python
   # POST to provider's recharge endpoint with API key
   ```

4. **Store API key** in `.env`:
   ```
   JIO_RECHARGE_API_KEY=your_key_here
   ```

### Using your LLM API key

- **LLM API key** (OpenAI, Gemini, etc.): Used by CTS to call the model. Stored in **Settings → Model Profiles**.
- **Recharge/Booking API keys**: Separate keys for external services. Store in `.env` or Supabase secrets, and read them in the MCP server.

---

## Tool Execution (LangChain + LangGraph)

**Tool execution is fully implemented.** The backend uses LangChain + LangGraph:

1. MCP tools are wrapped as LangChain StructuredTools
2. The LLM is bound with `bind_tools(tools)` – it returns native `tool_calls`
3. LangGraph’s ToolNode executes each tool via MCP `tools/call` JSON-RPC
4. Results are injected; the agent loop continues until the model returns a final response

See [TOOL_EXECUTION_FLOW.md](TOOL_EXECUTION_FLOW.md) for details.

---

## Notes or Todos Not Appearing in MCP Data

If the LLM says it saved a note or todo but nothing shows in **Settings → MCP Data**:

| Check | Fix |
|-------|-----|
| **Notes MCP not added** | Settings → MCP Servers → Add Notes at `http://localhost:8004/mcp` |
| **Todo MCP not added** | Add Todo at `http://localhost:8009/mcp` |
| **MCP server not running** | `cd mcp-servers/notes && python server.py` (or `.\scripts\start_all_mcps.ps1`) |
| **Migration 005 not run** | Run `supabase/migrations/005_mcp_user_data.sql` to create `user_notes`, `user_todos` |
| **Supabase env vars** | `.env` must have `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` |

The backend dual-writes notes/todos to Supabase, so they appear even when the MCP server uses a JSON fallback.

---

## Quick Reference: MCP Ports

| Server | Port | URL |
|--------|------|-----|
| Demo | 8001 | `http://localhost:8001/mcp` |
| Calculator | 8002 | `http://localhost:8002/mcp` |
| Weather | 8003 | `http://localhost:8003/mcp` |
| Notes | 8004 | `http://localhost:8004/mcp` |
| Timezone | 8005 | `http://localhost:8005/mcp` |
| Search | 8006 | `http://localhost:8006/mcp` |
| Translator | 8007 | `http://localhost:8007/mcp` |
| Unit Converter | 8008 | `http://localhost:8008/mcp` |
| Todo | 8009 | `http://localhost:8009/mcp` |
| Flight Booking | 8010 | `http://localhost:8010/mcp` |
| Hotel Booking | 8011 | `http://localhost:8011/mcp` |
| Currency | 8012 | `http://localhost:8012/mcp` |
| Wikipedia | 8013 | `http://localhost:8013/mcp` |
| **Email** | **8014** | `http://localhost:8014/mcp` |
| Calendar | 8015 | `http://localhost:8015/mcp` |
| News | 8016 | `http://localhost:8016/mcp` |
| Stocks | 8017 | `http://localhost:8017/mcp` |
| Reminder | 8018 | `http://localhost:8018/mcp` |
| QR Code | 8019 | `http://localhost:8019/mcp` |
| JSON Tools | 8020 | `http://localhost:8020/mcp` |
| Hash | 8021 | `http://localhost:8021/mcp` |
| UUID | 8022 | `http://localhost:8022/mcp` |
| Jio Recharge | 8023 | `http://localhost:8023/mcp` |

---

## Testing Jio ₹19 Recharge (Demo)

A **Jio Recharge MCP** (demo) is available. It simulates plan search and recharge. To test:

1. Start: `cd mcp-servers/jio_recharge && python server.py`
2. Add in Settings: `http://localhost:8023/mcp`
3. Ask: "Show me Jio plans for ₹19" or "Recharge my Jio number 9876543210 with ₹19 plan"

For **real** recharge, wire the MCP to a provider API (A1Topup, Enginify, etc.) and add your API key to `.env`.
