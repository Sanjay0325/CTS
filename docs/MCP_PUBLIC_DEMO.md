# Public MCP Demo: Real Example

This guide shows how the LLM uses a public MCP tool end-to-end, with a real example (Jio Recharge).

---

## Setup

1. **Start MCP servers:**
   ```powershell
   pnpm dev:mcp:all
   ```

2. **Add servers in CTS:** Settings → MCP Servers → click **+ Jio Recharge** (or **Add All**)

3. **Ensure a Model Profile** (OpenAI or Gemini) is configured in Settings.

---

## Demo: Jio ₹19 Recharge

### User prompt
```
Show me Jio plans for ₹19 and how to recharge
```

### Step-by-step flow

#### 1. User sends message
The chat API receives the message and loads:
- User's MCP servers (including Jio Recharge at `http://localhost:8023/mcp`)
- Tools from each server via `tools/list`

#### 2. Backend fetches tools
```
GET/POST http://localhost:8023/mcp
{"method":"tools/list","params":{}}
→ Response: [
  {"name":"search_jio_plans","description":"Search Jio prepaid plans..."},
  {"name":"recharge_jio","description":"Recharge a Jio prepaid number..."}
]
```

#### 3. LLM receives system prompt with tools
```
You have access to these tools. USE them when the user asks for actions:
- search_jio_plans: Search Jio prepaid plans. Pass amount (e.g. 19) to filter by price...
- recharge_jio: Recharge a Jio prepaid number. Provide 10-digit mobile, plan_id...
```

#### 4. LLM decides to call a tool
The model (e.g. GPT-4o) returns a **tool call**:
```json
{
  "tool_calls": [{
    "id": "call_abc123",
    "function": {
      "name": "search_jio_plans",
      "arguments": "{\"amount\": 19}"
    }
  }]
}
```

#### 5. Backend executes the tool
```
POST http://localhost:8023/mcp
{"method":"tools/call","params":{"name":"search_jio_plans","arguments":{"amount":19}}}
→ Response: {
  "result": {
    "content": [{"type":"text","text":"Jio plans:\n- jio_19: ₹19 | 1 day | 100 MB | Jio ₹19 1-day plan"}]
  }
}
```

#### 6. Result injected, LLM continues
The backend sends the tool result back to the LLM:
```
[Tool result]: Jio plans:
- jio_19: ₹19 | 1 day | 100 MB | Jio ₹19 1-day plan
```

#### 7. LLM formulates final response
The model uses the tool output and replies in natural language:

---

### Example output (what the user sees)

> **Jio Plans for ₹19**
>
> Here are the Jio prepaid plans available for ₹19:
>
> | Plan ID  | Amount | Validity | Data   | Description          |
> |----------|--------|----------|--------|----------------------|
> | jio_19   | ₹19    | 1 day    | 100 MB | Jio ₹19 1-day plan   |
>
> **How to recharge:**
> 1. Share your 10-digit Jio mobile number
> 2. I can use the `recharge_jio` tool with plan_id `jio_19` and amount 19
> 3. Or recharge via Jio app / MyJio / USSD *333#
>
> Would you like me to initiate a recharge for your number? (Demo mode will simulate it.)

---

## Another example: Calculator

**User:** `What is 15 * 27?`

1. Backend loads Calculator tools: `add`, `multiply`, `power`
2. LLM calls `multiply(a=15, b=27)`
3. MCP returns `405`
4. LLM responds: **405**

---

## Debug info (Memory Used)

After each response, the chat shows:
- **Tools Available:** number of tools from your MCP servers
- **Tools Used:** only tools the LLM actually **executed** (e.g. `search_jio_plans`). Shows `0` when no tools were called.

The system prompt includes query-type hints (weather → get_weather, currency → convert_currency, etc.) so the LLM reliably chooses tools. See [PUBLIC_APIS_FOR_MCP.md](PUBLIC_APIS_FOR_MCP.md) for prompt tips.

---

## Production: Real Jio Recharge

To perform real recharges:

1. Sign up with a recharge API (e.g. [A1Topup](https://a1topup.com), [Enginify](https://docs.enginify.in))
2. Add API key to `.env`:
   ```
   JIO_RECHARGE_API_KEY=your_key
   ```
3. Update `mcp-servers/jio_recharge/server.py` to call the API instead of returning demo text.
