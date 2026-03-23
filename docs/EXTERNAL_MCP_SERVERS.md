# Connecting LiGo, Supabase, and WhatsApp Business MCP Servers

How to connect CTS with popular external MCP servers: **LiGo (LinkedIn)**, **Supabase**, and **WhatsApp Business**.

---

## Overview

| MCP | Purpose | CTS Integration |
|-----|---------|-----------------|
| **WhatsApp Business** | Send messages, templates | Built-in MCP (port 8024) + env keys |
| **LinkedIn (LiGo)** | Create, schedule LinkedIn posts | Built-in MCP (port 8025) or LiGo hosted |
| **Supabase** | Query DB, deploy functions | External: `https://mcp.supabase.com/mcp` |

---

## 1. WhatsApp Business (Built-in)

**Start server:**
```bash
cd mcp-servers/whatsapp_business
pip install mcp httpx
python server.py
```

**Add in CTS:** Settings → MCP Servers → **+ WhatsApp Business** (or Manual: `http://localhost:8024/mcp`)

**Configure `.env`:**
```
WHATSAPP_ACCESS_TOKEN=your_meta_graph_api_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_API_VERSION=v21.0
```

**Get credentials:**
1. [Meta for Developers](https://developers.facebook.com/) → Create App → Add WhatsApp product
2. WhatsApp → API Setup → Copy Access Token and Phone Number ID
3. For production: use System User token with `whatsapp_business_messaging` permission

**Example prompts:**
- "Send WhatsApp message to 919876543210: Hi, your order is ready"
- "Text John on WhatsApp: Meeting at 3pm"

**Tools:** `send_whatsapp_message`, `send_whatsapp_template`

---

## 2. LinkedIn (Built-in or LiGo)

### Option A: CTS Built-in LinkedIn MCP (port 8025)

**Start server:**
```bash
cd mcp-servers/linkedin
pip install mcp httpx
python server.py
```

**Add in CTS:** **+ LinkedIn** or `http://localhost:8025/mcp`

**Configure `.env`:**
```
LINKEDIN_ACCESS_TOKEN=your_oauth_access_token
```

**Get token:** Use [LiGo](https://ligosocial.com) OAuth flow or [LinkedIn Developer Console](https://www.linkedin.com/developers/) with `w_member_social` scope.

### Option B: LiGo (Hosted LinkedIn MCP)

LiGo provides a hosted LinkedIn MCP for Claude/ChatGPT.

1. Go to [ligosocial.com/integrations](https://ligosocial.com/integrations) or [ligo.ertiqah.com](https://ligo.ertiqah.com)
2. Generate installation command (includes your API key)
3. If LiGo exposes an HTTP endpoint, add it in CTS: Settings → Add MCP Server (Manual) → paste URL
4. Otherwise use LiGo via their Custom GPT or Claude integration

**Example prompts:**
- "Post on LinkedIn: Excited to share our new product launch..."
- "Draft a LinkedIn post about AI trends"
- "Create a LinkedIn post for my blog update"

**Tools:** `create_linkedin_post`, `draft_linkedin_post`, `get_linkedin_profile`

---

## 3. Supabase (External MCP)

Supabase hosts an MCP server at **`https://mcp.supabase.com/mcp`**.

**Add in CTS:** Settings → MCP Servers → Add Manual:
- **Name:** `Supabase`
- **URL:** `https://mcp.supabase.com/mcp`

**Project-scoped (recommended):**
```
https://mcp.supabase.com/mcp?project_ref=YOUR_PROJECT_REF&read_only=true
```
Get `project_ref` from Supabase Dashboard → Project Settings → General.

**OAuth:** On first tools/list or tools/call, you may be prompted to sign in via browser. The Supabase MCP uses OAuth for authentication.

**Tools (examples):** Query tables, run SQL, deploy Edge Functions, view logs, generate TypeScript types.

**Example prompts:**
- "Query the users table from Supabase"
- "Deploy my edge function"
- "Show Supabase project logs"

---

## Making the LLM Use These Tools

The system prompt includes trigger hints. For best results, prompt explicitly:

| Goal | Prompt example |
|------|-----------------|
| Send WhatsApp | "Send a WhatsApp message to 919876543210 saying Order confirmed" |
| LinkedIn post | "Create a LinkedIn post: Excited to announce our new feature..." |
| Supabase query | "Query the messages table from Supabase for user 123" |

---

## Troubleshooting

- **Tools Available: 0** – Ensure MCP server is running and added in Settings
- **WhatsApp "Failed"** – Check token, Phone Number ID, and recipient format (country code, no +)
- **LinkedIn "Failed"** – Token may have expired. Re-run OAuth.
- **Supabase 401** – Complete OAuth sign-in when prompted
