# Notes & Todo Prompts – Best Practices

How to reliably add content to notes and/or todos, including "add to both notes and todo".

---

## Common Prompts

| User Intent | Recommended Phrasing | What Happens |
|-------------|----------------------|--------------|
| Save to note only | "Save this to a note" / "Remember this" | `save_note` |
| Add to todo only | "Add this to my todo" / "Add to my task list" | `add_todo` |
| **Both** | "Add this to notes AND todo" / "Save to notes as well as todo" | `save_note` + `add_todo` |
| Long content | "Save the above/below to a note with title X" | `save_note(title="X", content="...")` |

---

## Backend Handling

The backend normalizes tool arguments so `content` and `task` are always strings:

- **Lists** (e.g. from some LLM schemas) → joined with newlines
- **Content blocks** (e.g. `[{"type":"text","text":"..."}]`) → extracted as text

This avoids `can only concatenate str (not "list") to str` errors.

---

## MCP Servers Required

1. **Notes**: `cd mcp-servers/notes && python server.py` (port 8004)
2. **Todo**: `cd mcp-servers/todo && python server.py` (port 8009)
3. Add both in **Settings → MCP Servers**:
   - Notes: `http://localhost:8004/mcp`
   - Todo: `http://localhost:8009/mcp`

---

## With Ollama (default model)

Ollama uses text-based tool output. The system prompt instructs the model to emit JSON for tool calls. If tools are not triggered:

1. Use an API model (Gemini, Groq, OpenAI) for better tool use.
2. Or rephrase: "Save a note titled 'Day 3 Plan' with content: [paste content]".
3. Ensure Notes and Todo MCP servers are added and running.
