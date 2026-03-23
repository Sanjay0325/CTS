# Universal API Key Setup

CTS supports **any OpenAI-compatible** or **Gemini** API. Add your API key like plugging into a USB port—works with OpenAI, Groq, OpenRouter, Gemini, Qwen, Kimi, and more.

---

## Quick Start (On First Open)

1. Open CTS and sign in.
2. If you see **"Add your first API key"**, click **Add API Key →**.
3. In Settings → Model Profiles, pick a preset (e.g. **Groq**, **OpenRouter**).
4. Paste your API key.
5. Click **Add Profile**.
6. Select the model in chat and start chatting.

---

## Provider Presets

| Preset | Base URL | Example Model | Get API Key |
|--------|----------|---------------|-------------|
| **OpenAI** | `https://api.openai.com` | gpt-4o-mini | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| **Gemini** | `https://generativelanguage.googleapis.com/v1beta` | gemini-2.0-flash | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| **Groq** | `https://api.groq.com/openai` | llama-3.1-70b-versatile | [console.groq.com/keys](https://console.groq.com/keys) |
| **Grok** (via Groq) | `https://api.groq.com/openai` | openai/gpt-oss-120b | [console.groq.com/keys](https://console.groq.com/keys) |
| **OpenRouter** | `https://openrouter.ai/api` | openai/gpt-4o-mini | [openrouter.ai/keys](https://openrouter.ai/keys) |
| **Together** | `https://api.together.xyz` | meta-llama/Llama-3.2-3B-Instruct-Turbo | [api.together.xyz/settings/api-keys](https://api.together.xyz/settings/api-keys) |
| **Fireworks** | `https://api.fireworks.ai/inference` | accounts/fireworks/models/llama-v3p3-70b-instruct | [fireworks.ai/dashboard](https://fireworks.ai/dashboard) |
| **Anthropic** (via OpenRouter) | `https://openrouter.ai/api` | anthropic/claude-3.5-sonnet | [openrouter.ai/keys](https://openrouter.ai/keys) |
| **Qwen** (via OpenRouter) | `https://openrouter.ai/api` | qwen/qwen-2.5-72b-instruct | [openrouter.ai/keys](https://openrouter.ai/keys) |
| **Kimi** (via OpenRouter) | `https://openrouter.ai/api` | moonshotai/kimi-k2 | [openrouter.ai/keys](https://openrouter.ai/keys) |

---

## How to Add Correctly

### 1. Choose a preset

Click a preset button (OpenAI, Groq, OpenRouter, etc.) to fill **Provider URL** and **Model name** automatically.

### 2. Set display name

Optional. Used in the model dropdown (e.g. "My Groq", "Claude via OpenRouter").

### 3. Paste API key

Copy the key from the provider dashboard. Ensure:

- No extra spaces at start or end
- Key is pasted as a single string

### 4. Optionally change model

Each preset suggests a default model. For OpenRouter/aggregators you can use:

- `anthropic/claude-3.5-sonnet`
- `google/gemma-2-27b-it`
- `meta-llama/llama-3.1-70b-instruct`
- `openai/gpt-4o-mini`
- `qwen/qwen-2.5-72b-instruct`
- See [OpenRouter models](https://openrouter.ai/models) for the full list

### 5. Add profile

Click **Add Profile**. The key is stored securely in Supabase.

---

## Groq / Grok (GPT-OSS) Example

Groq provides fast inference. The Grok model uses a `provider/model` format:

- **Provider URL:** `https://api.groq.com/openai`
- **Model:** `openai/gpt-oss-120b` (or `llama-3.1-70b-versatile`)
- **API Key:** From [console.groq.com](https://console.groq.com/keys)

Use the **Grok** preset in CTS for `openai/gpt-oss-120b`.

---

## OpenRouter – Access Many Models

OpenRouter proxies 100+ models (Anthropic, Google, Meta, etc.) through one OpenAI-compatible API:

- One API key from [openrouter.ai/keys](https://openrouter.ai/keys)
- Model format: `provider/model` (e.g. `anthropic/claude-3.5-sonnet`)
- Same base URL for all: `https://openrouter.ai/api`

---

## Custom Provider

For any other OpenAI-compatible API:

1. Click **Custom** or leave Provider URL blank and fill manually.
2. **Provider URL:** Base URL without `/v1/chat/completions` (CTS appends it).
   - Example: `https://your-api.com` → CTS calls `https://your-api.com/v1/chat/completions`
3. **Model:** Provider-specific model ID.
4. **API Key:** Provider’s key.
5. **API style:** Leave as `openai` (default) for OpenAI-compatible endpoints.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| 401 Unauthorized | Check API key, no spaces, correct provider dashboard |
| 429 Rate limit | Quota exceeded; add billing or wait |
| Connection refused | Provider URL wrong; ensure it’s the base URL |
| Model not found | Verify model ID on provider’s docs; OpenRouter list: openrouter.ai/models |

---

---

## Flow – Where API Keys Fit

```
User adds profile (Settings) → API key stored in model_profile_secrets (Supabase Vault)
         │
         ▼
Chat request → profile_id → ProfileService.get_profile_with_api_key()
         │
         ▼
model_factory.create_chat_model_from_profile() → ChatOpenAI/ChatGoogleGenerativeAI with api_key
         │
         ▼
LangGraph agent → LLM calls (OpenAI, Gemini, Groq, etc.)
```

Keys are never returned to the frontend after creation. See [README.md](../README.md) for full flow.

---

## Contribution – Adding New Providers

| Change | Where to edit |
|--------|----------------|
| New preset (provider + default model) | `apps/web/src/components/SettingsPanel.tsx` – preset buttons |
| New API style in backend | `services/api/src/models.py` – `api_style` pattern; `model_factory.py` – new branch |
| This doc | Add row to provider table, update troubleshooting |

---

## Security

- API keys are stored in `model_profile_secrets` (Supabase).
- Keys are never returned to the frontend after creation.
- Use Supabase RLS so each user only accesses their own profiles.
