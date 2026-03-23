"""
MCP tools adapter - wrap MCP server tools as LangChain tools for agent use.

Handles user context injection and result truncation. MCP server is single source
for notes/todos (no dual-write to avoid duplicates). Uses explicit args_schema
for save_note/add_todo so the LLM sends correct params (title, content, task).
"""

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.services.chat_data_supabase import ChatDataSupabase

# Truncate tool results > this to speed up LLM parsing and avoid context overflow
MAX_TOOL_RESULT_LENGTH = 12000

# Tools that need user_id and conversation_id injected
_USER_CONTEXT_TOOLS = {
    "save_note", "list_notes", "list_notes_json", "get_notes_summary",
    "add_todo", "list_todos", "list_todos_json", "complete_todo",
    "set_reminder", "list_reminders", "list_reminders_json",
}


def _ensure_str(val: Any) -> str:
    """Convert value to string. Handles list (e.g. content blocks from LLM) or dict."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        parts = []
        for item in val:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(val)


# Aliases: LLMs sometimes send wrong param names - map to correct keys
_SAVE_NOTE_TITLE_ALIASES = ("title", "name", "subject", "label")
_SAVE_NOTE_CONTENT_ALIASES = ("content", "text", "body", "description", "note")
_ADD_TODO_TASK_ALIASES = ("task", "item", "todo", "text", "content", "description", "title")

# Tool-specific param aliases: model may send wrong keys; normalize before MCP call
_TOOL_ARG_ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    "get_weather": {"city": ("city", "location", "place", "loc")},
    "get_forecast": {"city": ("city", "location", "place"), "days": ("days", "day", "num_days")},
    "convert_currency": {
        "from_currency": ("from_currency", "from", "source", "fromCurrency"),
        "to_currency": ("to_currency", "to", "target", "toCurrency"),
        "amount": ("amount", "value", "quantity"),
    },
    "get_rates": {"base": ("base", "currency", "from")},
    "search": {"query": ("query", "q", "search", "search_term")},
    "search_wikipedia": {"query": ("query", "q", "search", "term")},
    "get_quote": {"symbol": ("symbol", "stock", "ticker", "stock_symbol")},
    "get_historical": {"symbol": ("symbol", "stock", "ticker"), "days": ("days", "day")},
    "search_flights": {
        "origin": ("origin", "from", "from_city", "departure"),
        "destination": ("destination", "to", "to_city", "arrival"),
        "date": ("date", "travel_date", "departure_date"),
    },
    "translate": {"text": ("text", "content", "input"), "target_lang": ("target_lang", "to", "language")},
}


def _get_first_non_empty(d: dict, keys: tuple[str, ...], default: str = "") -> str:
    """Get first non-empty value for any of the keys. Used for param aliasing."""
    for k in keys:
        v = d.get(k)
        s = _ensure_str(v).strip()
        if s:
            return s
    return default


def _normalize_tool_args(name: str, args: dict) -> dict:
    """Apply param aliases so model output maps to MCP tool schema (location->city, etc.)."""
    aliases = _TOOL_ARG_ALIASES.get(name)
    if not aliases:
        return args
    out = {}
    alias_keys = {ak for keys in aliases.values() for ak in keys}
    for canonical, alt_keys in aliases.items():
        val = _get_first_non_empty(args, alt_keys)
        if val:
            # Preserve numeric types where needed
            if canonical in ("amount", "days"):
                try:
                    out[canonical] = int(val) if "." not in str(val) else float(val)
                except (ValueError, TypeError):
                    out[canonical] = val
            else:
                out[canonical] = val
    for k, v in args.items():
        if k not in out and k not in alias_keys:
            out[k] = v
    return out if out else args


def _inject_user_context(name: str, args: dict, user_id: str, conversation_id: str | None) -> dict:
    """Inject user_id and conversation_id. Normalize and alias content/task/title."""
    args = _normalize_tool_args(name, args)
    if name not in _USER_CONTEXT_TOOLS:
        return args
    out = dict(args)
    out.setdefault("user_id", user_id)
    if conversation_id:
        out.setdefault("conversation_id", conversation_id)
    if name == "save_note":
        content = _get_first_non_empty(out, _SAVE_NOTE_CONTENT_ALIASES)
        title = _get_first_non_empty(out, _SAVE_NOTE_TITLE_ALIASES)
        if content and not title:
            title = (content[:50] + "…") if len(content) > 50 else content
        out["title"] = title or "Note"
        out["content"] = content
    elif name == "add_todo":
        out["task"] = _get_first_non_empty(out, _ADD_TODO_TASK_ALIASES)
    return out


def _create_mcp_tool(
    server_url: str,
    tool_def: dict,
    data: ChatDataSupabase,
    user_id: str,
    conversation_id: str | None,
) -> StructuredTool:
    """Create a single LangChain StructuredTool that invokes an MCP tool."""

    name = tool_def.get("name") or "unknown"
    desc = tool_def.get("description") or "No description"

    async def _invoke(**kwargs: Any) -> str:
        args = _inject_user_context(name, kwargs, user_id, conversation_id)
        # Skip MCP call if critical content is empty (avoids "Untitled" / empty records)
        if name == "save_note":
            title, content = args.get("title", ""), args.get("content", "")
            if not content or not str(content).strip():
                return (
                    "Error: save_note requires non-empty 'content'. "
                    "Do NOT retry. Respond to the user in text: ask for their name and what to save, or explain you need more info."
                )
        elif name == "add_todo":
            task = args.get("task", "")
            if not task or not str(task).strip():
                return (
                    "Error: add_todo requires non-empty 'task'. "
                    "Do NOT retry. Respond to the user in text asking for the task details."
                )
        result = await data.call_tool(server_url, name, args)
        # MCP server is the single source of truth; no dual-write to avoid duplicates
        raw = result or f"Tool {name} failed."
        # Truncate very long results for faster LLM parsing and to avoid context overflow
        if len(raw) > MAX_TOOL_RESULT_LENGTH:
            raw = raw[:MAX_TOOL_RESULT_LENGTH] + f"\n\n[Result truncated; original {len(raw)} chars]"
        # Clear prefix so agent knows: your tool ran, here's output, now respond or call next tool
        return f"[TOOL_OUTPUT: {name}]\n{raw}"

    # Explicit schema for key tools so LLM sends correct params; aliases handle model variations
    args_schema = None
    if name == "save_note":
        class SaveNoteSchema(BaseModel):
            title: str = Field(description="Short title for the note (e.g. 'Meeting notes', 'Day 3 Plan')")
            content: str = Field(description="Full note content/text to save. REQUIRED - must not be empty.")
        args_schema = SaveNoteSchema
    elif name == "add_todo":
        class AddTodoSchema(BaseModel):
            task: str = Field(description="The task to add. REQUIRED - must not be empty. For multiple tasks, call add_todo once per task.")
            priority: str = Field(default="medium", description="Priority: low, medium, or high")
        args_schema = AddTodoSchema
    elif name == "get_weather":
        class GetWeatherSchema(BaseModel):
            city: str = Field(description="City name (e.g. Chennai, London, Mumbai). REQUIRED.")
        args_schema = GetWeatherSchema
    elif name == "get_forecast":
        class GetForecastSchema(BaseModel):
            city: str = Field(description="City name. REQUIRED.")
            days: int = Field(default=3, description="Number of forecast days (default 3).")
        args_schema = GetForecastSchema
    elif name == "convert_currency":
        class ConvertCurrencySchema(BaseModel):
            amount: float = Field(description="Amount to convert. REQUIRED.")
            from_currency: str = Field(description="Source currency ISO code (USD, EUR, INR, etc.). REQUIRED.")
            to_currency: str = Field(description="Target currency ISO code. REQUIRED.")
        args_schema = ConvertCurrencySchema
    elif name == "search":
        class SearchSchema(BaseModel):
            query: str = Field(description="Search query. REQUIRED.")
        args_schema = SearchSchema
    elif name == "get_quote":
        class GetQuoteSchema(BaseModel):
            symbol: str = Field(description="Stock symbol (e.g. AAPL, GOOGL). REQUIRED.")
        args_schema = GetQuoteSchema

    return StructuredTool.from_function(
        coroutine=_invoke,
        name=name,
        description=desc,
        args_schema=args_schema,
        return_direct=False,
    )


def build_mcp_tools(
    tools_with_server: list[tuple[str, dict]],
    data: ChatDataSupabase,
    user_id: str,
    conversation_id: str | None,
) -> list[StructuredTool]:
    """
    Convert MCP tools (server_url, tool_def) to LangChain StructuredTools.
    Each tool, when invoked, calls the MCP server via data.call_tool().
    """
    tools: list[StructuredTool] = []
    seen: set[str] = set()
    for server_url, t in tools_with_server:
        name = t.get("name") or "unknown"
        if name in seen:
            continue
        seen.add(name)
        tools.append(_create_mcp_tool(server_url, t, data, user_id, conversation_id))
    return tools
