# Ollama (llama3:latest) Setup Guide

Ollama runs Llama and other models **locally on your laptop** — no API keys, no rate limits, no cloud. You can host and use the model entirely on your machine.

---

## 1. Install Ollama

**Windows:**
- Download from [ollama.com](https://ollama.com) → Install
- Or: `winget install Ollama.Ollama`

**macOS:**
- `brew install ollama` or download from ollama.com

**Linux:**
- `curl -fsSL https://ollama.com/install.sh | sh`

---

## 2. Start Ollama (required before CTS chat)

**Ollama must be running** for CTS to use it. You do **not** need `ollama run llama3` in a separate console — CTS calls the API on demand.

**Pull model (if needed):**
```bash
ollama pull llama3:latest
```

**Start Ollama:**
- **Windows:** Ollama usually auto-starts; check system tray.
- **macOS/Linux:** `ollama serve` or run `ollama run llama3:latest` once (press `Ctrl+D` to exit; service keeps running).

---

## 3. Verify Ollama is Running

```bash
ollama list
```

You should see `llama3:latest` in the list.

Check the API:

```bash
curl http://localhost:11434/api/tags
```

---

## 4. Use in CTS Chat

1. Ensure **Ollama is running** (Step 2) — no separate `ollama run` console needed.
2. Start CTS (API + Web).
3. In the model dropdown, choose **default (llama3:latest)**.
4. Chat — no API key; model loads on first message.

---

## 5. Configuration (Optional)

In `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_DEFAULT_MODEL` | `llama3:latest` | Model to use for "default" |

---

## 6. Troubleshooting

### "Ollama model not found"
- Run: `ollama pull llama3:latest`
- Check: `ollama list`

### "Ollama error" / Connection refused
- Ensure Ollama is running: `ollama serve` (or start from system tray / menu)
- Or: `ollama run llama3:latest` (starts service if needed)

### "Rate limited" or empty response (fixed)
- Previously, connection errors were incorrectly shown as "Rate limited". This is fixed — you'll now see the actual error (e.g. connection refused).
- Ensure **default (llama3:latest)** is selected and Ollama is running: `ollama run llama3:latest`.

### Ollama runs on a different port
- Set `OLLAMA_BASE_URL=http://localhost:PORT` in `.env`.

---

## 7. MCP Tools & RAG with Ollama

**Tool support:** Base `llama3` and `llama2` do **not** support tool/function calling. For MCP tools (notes, todos, etc.), use a tool-capable model:

```bash
ollama pull llama3.1    # Recommended for tools
ollama pull qwen3
ollama pull mistral-nemo
```

With `llama3:latest`, CTS runs **without MCP tools** (no 400 error) and shows a hint in the debug panel.

- **RAG (document search):** Works — your selected collections are used as context.
- **Save to memory:** Works.
- **MCP tools:** Require llama3.1, qwen3, mistral-nemo, or similar.

**Required for save_note/add_todo:**
1. Start Notes server: `cd mcp-servers/notes && python server.py`
2. Add in Settings → MCP Servers: Name `Notes`, URL `http://localhost:8004/mcp`
3. Click **Add Server**. Without this, tool prompts will not invoke save_note.

---

## 8. Other Models

```bash
ollama pull llama3.1      # Tool calling support
ollama pull llama3.2
ollama pull qwen3         # Tool calling support
ollama pull mistral-nemo  # Tool calling support
ollama pull codellama
```

CTS lists all installed Ollama models under "default (local Llama)" in the dropdown. For MCP tools (notes, todos), use llama3.1 or qwen3.
