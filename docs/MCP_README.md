# MCP (Model Context Protocol) Guide for CTS

Complete guide to using, creating, and maintaining MCP servers. **Tools used are stored in Supabase** (`message_metadata.tools_used`).

**Troubleshooting:** [MCP_TROUBLESHOOTING.md](MCP_TROUBLESHOOTING.md) – Why "Tools Available: 0", why `/mcp` doesn't open in browser, Jio recharge, public APIs.

**Public MCP Demo:** [MCP_PUBLIC_DEMO.md](MCP_PUBLIC_DEMO.md) – Step-by-step example of the LLM using a public MCP tool (Jio Recharge) with real output.

**Public APIs:** [PUBLIC_APIS_FOR_MCP.md](PUBLIC_APIS_FOR_MCP.md) – Popular APIs (Weather, Currency, Stocks, News) to wire to MCP, plus how to prompt the LLM so it uses tools.

**LiGo, Supabase, WhatsApp:** [EXTERNAL_MCP_SERVERS.md](EXTERNAL_MCP_SERVERS.md) – Connect LinkedIn (LiGo), Supabase MCP, WhatsApp Business – send messages, create posts, query DB.

---

## Table of Contents

1. [Using MCP in CTS](#using-mcp-in-cts)
2. [Creating a New MCP Server](#creating-a-new-mcp-server)
3. [Public MCP Specifications](#public-mcp-specifications)
4. [All MCP Servers (20+)](#all-mcp-servers-20)
5. [Tool Usage in Supabase](#tool-usage-in-supabase)
6. [Maintenance & Best Practices](#maintenance--best-practices)

---

## Using MCP in CTS

### Add an MCP Server

1. **Start the MCP server** (see port in table below):
  ```bash
   cd mcp-servers/<server-name>
   pip install mcp
   python server.py
  ```
2. **Open Settings** → **MCP Servers** tab.
3. **Add Server**:
  - **Friendly name:** e.g. `Flight Booking`
  - **Server URL:** `http://localhost:8XXX/mcp` (replace XXX with port)
4. Click **List Tools** to verify tools are discovered.

### Use Tools in Chat

Tools are wrapped as LangChain StructuredTools and passed to a LangGraph agent. Once added, the LLM sees available tools and can invoke them. Ask naturally:

- "Book a flight from NYC to London" → uses `search_flights`, `book_flight`
- "What's 15 * 27?" → uses `multiply`
- "Translate 'Hello' to Spanish" → uses `translate`

### Tool Usage Stored in Supabase

Each assistant response records:

- `tools_used`: JSON array of tool names available/used
- `external_dbs_used`: RAG collections searched
- `in_context_count`: messages in context

Query via `message_metadata` table.

---

## Creating a New MCP Server

### 1. Project Structure

```
mcp-servers/my-server/
├── server.py
├── pyproject.toml
└── README.md
```

### 2. Minimal `server.py`

```python
"""My MCP server - description."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My Server", json_response=True, host="0.0.0.0", port=8XXX)


@mcp.tool()
def my_tool(param1: str, param2: int = 10) -> str:
    """Clear description for the LLM. Be specific about params and return."""
    return f"Result: {param1} x {param2}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

### 3. `pyproject.toml`

```toml
[project]
name = "mcp-my-server"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["mcp>=1.0.0"]
```

### 4. Run

```bash
cd mcp-servers/my-server
pip install mcp
python server.py
```

### 5. Register in CTS

Settings → MCP Servers → Add `http://localhost:8XXX/mcp`

---

## Public MCP Specifications

Public MCPs are servers designed for common tasks, deployable by anyone. **Spec file:** [docs/public_mcp_specs.yaml](public_mcp_specs.yaml).

Specification format:


| Field          | Description                                        |
| -------------- | -------------------------------------------------- |
| **Name**       | Server display name                                |
| **Port**       | Default port                                       |
| **URL**        | `http://<host>:<port>/mcp`                         |
| **Tools**      | List of tools with name, description, input schema |
| **Auth**       | None / API key / OAuth                             |
| **Rate limit** | Requests per minute (if applicable)                |


### Example: Flight Booking MCP Specification

```yaml
name: Flight Booking
version: 1.0
port: 8010
transport: streamable-http
tools:
  - name: search_flights
    description: Search flights by origin, destination, date
    inputSchema:
      type: object
      properties:
        origin: { type: string, description: "IATA code e.g. JFK" }
        destination: { type: string, description: "IATA code e.g. LHR" }
        date: { type: string, format: date }
      required: [origin, destination, date]
  - name: book_flight
    description: Book a flight by flight_id and passenger details
    inputSchema:
      type: object
      properties:
        flight_id: { type: string }
        passenger_name: { type: string }
        passenger_email: { type: string }
```

---

## All MCP Servers (20+)

### Built-in (Local)


| #   | Server         | Port | URL                         | Tools                                       |
| --- | -------------- | ---- | --------------------------- | ------------------------------------------- |
| 1   | demo           | 8001 | `http://localhost:8001/mcp` | add, get_current_time, echo                 |
| 2   | calculator     | 8002 | `http://localhost:8002/mcp` | add, multiply, power                        |
| 3   | weather        | 8003 | `http://localhost:8003/mcp` | get_weather, get_forecast                   |
| 4   | notes          | 8004 | `http://localhost:8004/mcp` | save_note, list_notes                       |
| 5   | timezone       | 8005 | `http://localhost:8005/mcp` | get_time_in_timezone, list_common_timezones |
| 6   | search         | 8006 | `http://localhost:8006/mcp` | search                                      |
| 7   | translator     | 8007 | `http://localhost:8007/mcp` | translate, list_languages                   |
| 8   | unit_converter | 8008 | `http://localhost:8008/mcp` | convert_units                               |
| 9   | todo           | 8009 | `http://localhost:8009/mcp` | add_todo, list_todos, complete_todo         |
| 10  | flight_booking | 8010 | `http://localhost:8010/mcp` | search_flights, book_flight                 |
| 11  | hotel_booking  | 8011 | `http://localhost:8011/mcp` | search_hotels, book_hotel                   |
| 12  | currency       | 8012 | `http://localhost:8012/mcp` | convert_currency, get_rates                 |
| 13  | wikipedia      | 8013 | `http://localhost:8013/mcp` | search_wikipedia                            |
| 14  | email          | 8014 | `http://localhost:8014/mcp` | send_email                                  |
| 15  | calendar       | 8015 | `http://localhost:8015/mcp` | create_event, list_events                   |
| 16  | news           | 8016 | `http://localhost:8016/mcp` | get_news                                    |
| 17  | stocks         | 8017 | `http://localhost:8017/mcp` | get_quote, get_historical                   |
| 18  | reminder       | 8018 | `http://localhost:8018/mcp` | set_reminder, list_reminders                |
| 19  | qr_code        | 8019 | `http://localhost:8019/mcp` | generate_qr, decode_qr                      |
| 20  | json_tools     | 8020 | `http://localhost:8020/mcp` | parse_json, validate_json                   |
| 21  | hash           | 8021 | `http://localhost:8021/mcp` | hash_md5, hash_sha256                       |
| 22  | uuid           | 8022 | `http://localhost:8022/mcp` | generate_uuid                               |
| 23  | jio_recharge   | 8023 | `http://localhost:8023/mcp` | search_jio_plans, recharge_jio              |
| 24  | whatsapp_business | 8024 | `http://localhost:8024/mcp` | send_whatsapp_message, send_whatsapp_template |
| 25  | linkedin       | 8025 | `http://localhost:8025/mcp` | create_linkedin_post, draft_linkedin_post   |
| 26  | irctc          | 8026 | `http://localhost:8026/mcp` | search_trains_between_stations, check_seat_availability, get_station_code |


### Public MCPs (10+ for Common Tasks)


| #   | Public MCP         | Use Case            | Tools                               |
| --- | ------------------ | ------------------- | ----------------------------------- |
| 1   | **Flight Booking** | Search/book flights | search_flights, book_flight         |
| 2   | **Hotel Booking**  | Search/book hotels  | search_hotels, book_hotel           |
| 3   | **Currency**       | Convert currencies  | convert_currency, get_rates         |
| 4   | **Weather**        | Weather info        | get_weather, get_forecast           |
| 5   | **Translator**     | Translate text      | translate, list_languages           |
| 6   | **Wikipedia**      | Lookup facts        | search_wikipedia                    |
| 7   | **News**           | Get news            | get_news                            |
| 8   | **Stocks**         | Stock quotes        | get_quote, get_historical           |
| 9   | **Todo**           | Task management     | add_todo, list_todos, complete_todo |
| 10  | **Calendar**       | Events              | create_event, list_events           |
| 11  | **Email**          | Send emails         | send_email                          |
| 12  | **Search**         | Web search          | search                              |


---

## Tool Usage in Supabase

### Schema

```sql
-- message_metadata stores tools per response
CREATE TABLE message_metadata (
    message_id UUID REFERENCES messages(id),
    conversation_id UUID REFERENCES conversations(id),
    tools_used JSONB DEFAULT '[]',      -- ["search_flights", "book_flight"]
    external_dbs_used JSONB DEFAULT '[]',
    in_context_count INT
);
```

### Query Tools Used

```sql
-- Tools used in a conversation
SELECT m.content, mm.tools_used, mm.external_dbs_used
FROM messages m
JOIN message_metadata mm ON mm.message_id = m.id
WHERE m.conversation_id = 'xxx' AND m.role = 'assistant';
```

### Analytics

- **Most used tools**: Aggregate `tools_used` across all messages
- **Tools per conversation**: Group by `conversation_id`
- **External DB usage**: Track `external_dbs_used` for RAG

---

## Maintenance & Best Practices

### 1. Port Allocation

- 8001–8022: Reserved for built-in MCPs
- 8100+: Custom/user MCPs

### 2. Tool Naming

- Use `snake_case`
- Be descriptive: `search_flights` not `search`
- Prefix by domain if needed: `flight_search`, `flight_book`

### 3. Tool Descriptions

- Write for the LLM: clear, specific
- Include param types and examples
- State what the tool returns

### 4. Error Handling

```python
@mcp.tool()
def my_tool(x: str) -> str:
    """Do something with x."""
    try:
        return process(x)
    except ValueError as e:
        return f"Error: {e}"
```

### 5. Public MCP Deployment

- Use environment variables for API keys
- Add rate limiting for public endpoints
- Document auth requirements
- Version your API (e.g. `/v1/mcp`)

### 6. Health Check

Add a simple health endpoint for monitoring:

```python
# Optional: Add to server if needed
# MCP protocol handles /mcp - add /health for ops
```

### 7. Updating Tools

When you add/remove tools:

1. Restart the MCP server
2. In CTS, click **List Tools** to refresh
3. Tool list is cached 60s; wait or restart API

---

## Quick Start All Servers

```bash
# From project root - run each in separate terminal
for port in 8001 8002 8003 8004 8005 8006 8007 8008 8009 8010 8011 8012; do
  # cd to appropriate server and run
  echo "Start server on port $port"
done
```

Or use a process manager (e.g. `pm2`, `supervisord`) to run all MCPs.

---

---

## Flow – How MCP Integrates with CTS

```
User adds MCP server (Settings) → stored in mcp_servers table
         │
         ▼
Chat loads servers → tools/list per server → tools cached 60s
         │
         ▼
mcp_tools.build_mcp_tools() → MCP tools → LangChain StructuredTools
         │
         ▼
LangGraph agent → model returns tool_calls → ToolNode → call_tool(server_url, name, args)
         │
         ▼
POST {server_url}/mcp → tools/call → MCP server runs tool → result → ToolMessage → agent loop
```

Tool usage is stored in `message_metadata.tools_used`. See [TOOL_EXECUTION_FLOW.md](TOOL_EXECUTION_FLOW.md).

---

## Contribution – Extending MCP Support

| Change | Action |
|--------|--------|
| Add new MCP server | Create `mcp-servers/<name>/` with `server.py`, register in Settings |
| Add tool to existing server | Add `@mcp.tool()` in server, restart server, List Tools in CTS |
| Wire MCP to Supabase | Use `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in server; dual-write via `mcp_tools.py` |
| Update port table | Edit this doc and [MCP_TROUBLESHOOTING.md](MCP_TROUBLESHOOTING.md) |

---

## References

- [Model Context Protocol](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [CTS Main README](../README.md)

