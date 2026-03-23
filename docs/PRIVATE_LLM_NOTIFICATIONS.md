# Private LLM Notifications (Task 4)

**Goal:** When a prompt is executed and the output arrives, optionally send a private message to your phone (or another number)—e.g., SMS or WhatsApp—so you can see the result without staying in the app.

---

## Use Cases

1. **Notify self on completion** – Send a short summary of the response to your own number when the LLM finishes.
2. **Forward to another number** – Send the output (or summary) to a specified number, e.g. a colleague or your other phone.

---

## Architecture Options

### Option A: Backend-triggered after stream completes

```
Chat stream completes successfully
    → Backend checks user_settings: notify_on_complete, notification_phone
    → If enabled, call Twilio (SMS) or WhatsApp Cloud API
    → Send: "CTS: [First 100 chars of response]..." or custom template
```

**Pros:** Runs after every successful response.  
**Cons:** Needs Twilio/WhatsApp credentials and user config.

### Option B: LLM-invoked via MCP tools

```
User prompt: "When you're done, send the summary to +919876543210"
    → LLM finishes its response
    → LLM calls send_whatsapp_message(to="919876543210", message=<summary>)
```

**Pros:** No extra backend logic; uses existing WhatsApp MCP.  
**Cons:** User must include this in every prompt; number is in chat history.

### Option C: Hybrid – Settings + optional per-message override

- **Settings:** "Notify me when response is ready" + optional default phone number.
- **Per message:** Optional "Send result to: [number]" in the chat UI.
- Backend sends notification after successful stream using configured/default number.

---

## Recommended Implementation (Option C)

### 1. Database

```sql
-- Add to user_settings or new table
ALTER TABLE public.user_settings ADD COLUMN IF NOT EXISTS notify_on_complete BOOLEAN DEFAULT FALSE;
ALTER TABLE public.user_settings ADD COLUMN IF NOT EXISTS notification_phone TEXT;  -- E.164, e.g. 919876543210
```

### 2. Chat Request

Extend `ChatRequest`:

```python
# Optional; overrides user setting for this message only
notify_phone: str | None = None  # If set, send result to this number
```

### 3. Backend Logic (after successful stream)

```python
# In chat_service.py, after yielding "done"
if save_to_memory or notify_phone or user_setting_notify:
    phone = notify_phone or user_settings.get("notification_phone")
    if phone:
        summary = full_content[:160] + "…" if len(full_content) > 160 else full_content
        await send_sms_or_whatsapp(phone, f"CTS: {summary}")
```

### 4. Providers

| Provider | Use case | Env vars |
|----------|----------|----------|
| **Twilio** | SMS | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` |
| **WhatsApp Business API** | WhatsApp | `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` (already in MCP) |
| **Telegram Bot** | Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |

---

## UI Sketch

**Settings panel:**
- [ ] Notify me when response is ready
- Phone number: [_____________] (optional)
- Channel: SMS / WhatsApp

**Per message (optional):**
- [ ] Send result to: [_____________]

---

## Quick Start (WhatsApp – reuse existing MCP config)

You already have `mcp-servers/whatsapp_business` with `send_whatsapp_message`. For backend-triggered notifications:

1. Add a small helper in `chat_service.py` or a new `notification_service.py` that calls the same WhatsApp API (same env vars).
2. After `yield {"type": "done", ...}`, if user has `notify_on_complete` and `notification_phone`, call that helper.
3. Do not expose the phone number in the frontend stream; keep it server-side only.

---

## Privacy

- Store `notification_phone` only in `user_settings` with RLS so only the user can read/update it.
- Do not log phone numbers.
- Prefer WhatsApp over SMS if both are configured (more private, less cost).
- Allow users to disable notifications at any time.
