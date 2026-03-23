"""Chat service - streaming LLM with memory and MCP tools via LangChain/LangGraph."""

import json
import logging
import threading
import time
from typing import AsyncGenerator

import httpx

from src.config import settings as app_settings
from src.core.constants import GEMINI_MODEL_ALIASES
from src.langgraph_services.chat_graph import create_chat_graph, stream_chat_with_graph
from src.langgraph_services.graph_tracer import GraphTracer
from src.services.chat_data_supabase import ChatDataSupabase
from src.services.ollama_service import list_ollama_models, ollama_model_supports_tools
from src.tool_trigger_hints import PRIMARY_TOOLS_BLOCK, TOOL_TRIGGER_HINTS

logger = logging.getLogger(__name__)


class LLMRateLimitError(Exception):
    """Raised when LLM API returns 429. Carries retry_after_seconds for UI countdown."""
    def __init__(self, message: str, status_code: int = 429, retry_after_seconds: int | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds or 60


def _parse_retry_after(resp: httpx.Response, default: int = 60) -> int:
    """Extract Retry-After from response. Returns seconds (default 60)."""
    val = resp.headers.get("retry-after", "").strip()
    if not val:
        return default
    if val.isdigit():
        return min(300, max(1, int(val)))
    return default

# In-context window size
MAX_CONTEXT_MESSAGES = 20

# In-Cache Memory: Thread-safe KV-style reuse of prior computation.
_cache_lock = threading.Lock()
_tool_list_cache: dict = {}
_cache_ttl = 300
_memory_cache: dict = {}
_memory_cache_ttl = 120


def _cache_get(cache: dict, key: str, ttl: int) -> tuple[bool, any]:
    """Thread-safe cache get. Returns (hit, value)."""
    with _cache_lock:
        entry = cache.get(key)
        if entry and (time.time() - entry["ts"]) < ttl:
            return True, entry["data"]
    return False, None


def _cache_set(cache: dict, key: str, data: any) -> None:
    """Thread-safe cache set."""
    with _cache_lock:
        cache[key] = {"data": data, "ts": time.time()}

def _infer_priority_tools(message: str, tool_names: set[str]) -> list[str]:
    """Infer from user message which tools to surface first. Model sees these first; no hardcode."""
    m = (message or "").lower()
    priority: list[str] = []
    if any(w in m for w in ("save", "note", "remember", "store", "mcp notes", "notes server")) and "save_note" in tool_names:
        priority.append("save_note")
    if any(w in m for w in ("todo", "task", "remind")) and "add_todo" in tool_names:
        priority.append("add_todo")
    if any(w in m for w in ("list notes", "my notes", "show notes")) and "list_notes" in tool_names:
        priority.append("list_notes")
    return priority


def _infer_relevant_tool_hint(message: str, tool_names: set[str]) -> str:
    """Infer from user message which tools may be relevant. Returns a prompt hint for the model."""
    m = (message or "").lower()
    hints = []
    if any(w in m for w in ("save", "note", "remember", "store", "mcp notes", "notes server")) and "save_note" in tool_names:
        hints.append(
            "save_note is available. Extract title (e.g. name in quotes, or explicit title=) and content from user message. "
            "If user says 'what you think', write one brief thought. Call save_note with both params."
        )
    if any(w in m for w in ("todo", "task", "remind")) and "add_todo" in tool_names:
        hints.append("add_todo is available. Extract the task from the message and call it.")
    if any(w in m for w in ("list notes", "my notes", "show notes")) and "list_notes" in tool_names:
        hints.append("list_notes is available.")
    if not hints:
        return ""
    return "RELEVANT: " + " ".join(hints)


def _build_agent_tool_prompt(
    tool_list: str,
    tool_list_primary: str,
    is_ollama: bool,
    user_message: str,
    tool_names: set[str],
) -> str:
    """Build agent tool-usage prompt. Few-shot examples + dynamic hint. Model does the work."""
    s = "\n\n[TOOLS] You have tools. Call them when the user requests an action. Never refuse.\n\n"
    s += "EXAMPLE 1 - User: 'save my name Alex as title and what you think as content'\n"
    s += "→ You call save_note with title='Alex', content='<one sentence about the user>'\n\n"
    s += "EXAMPLE 2 - User: 'save in notes with MCP server notes, title=Meeting, content=Discussion points'\n"
    s += "→ You call save_note(title='Meeting', content='Discussion points')\n\n"
    s += PRIMARY_TOOLS_BLOCK
    s += TOOL_TRIGGER_HINTS
    hint = _infer_relevant_tool_hint(user_message, tool_names)
    if hint:
        s += f"\n\n{hint}\n\n"
    s += f"\n{tool_list_primary}\n\n[ALL TOOLS]\n{tool_list}"
    s += "\n\nAfter calling a tool you get [TOOL_OUTPUT: name]. Then confirm to the user."
    if is_ollama:
        s += (
            '\n\nTo call a tool: output ONLY valid JSON, e.g. {"name":"save_note","kwargs":{"title":"X","content":"Y"}}. '
            "No other text. We execute it automatically."
        )
    else:
        s += " Use native tool calls when available."
    return s


class ChatService:
    """Chat service with streaming, memory, and MCP tools. Uses Supabase REST (no direct Postgres)."""

    @staticmethod
    async def _generate_chat_title(
        client: httpx.AsyncClient,
        base_url: str,
        model: str,
        api_key: str,
        api_style: str,
        first_message: str,
        assistant_preview: str,
    ) -> str | None:
        """Ask LLM to generate a short chat title. Returns None on failure."""
        prompt = (
            "Generate a short chat title (max 6 words) for this conversation. "
            "Reply with ONLY the title, no quotes, no punctuation at end.\n\n"
            f"User: {first_message[:200]}\n\n"
            f"Assistant (preview): {assistant_preview[:150]}"
        )
        try:
            if api_style == "gemini":
                model = GEMINI_MODEL_ALIASES.get(model, model)
                url = f"{base_url.rstrip('/')}/models/{model}:generateContent"
                payload = {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 50},
                }
                resp = await client.post(
                    url,
                    headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                    json=payload,
                )
                if resp.status_code != 200:
                    return None
                data = resp.json()
                text = ""
                for c in data.get("candidates", []):
                    for p in c.get("content", {}).get("parts", []):
                        text += p.get("text", "")
                title = text.strip()[:60] if text else None
                return title if title else None
            else:
                resp = await client.post(
                    f"{base_url.rstrip('/')}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 50,
                        "temperature": 0.3,
                    },
                    timeout=15.0,
                )
                if resp.status_code != 200:
                    return None
                data = resp.json()
                text = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
                return text[:60] if text else None
        except Exception:
            return None

    @staticmethod
    def _openai_to_gemini_contents(messages: list[dict]) -> list[dict]:
        """Convert OpenAI message format to Gemini contents format."""
        contents = []
        for m in messages:
            role = m.get("role", "user")
            text = m.get("content", "")
            if role == "system":
                continue  # Handled via systemInstruction
            gemini_role = "user" if role == "user" else "model"
            contents.append({"role": gemini_role, "parts": [{"text": text}]})
        return contents

    @staticmethod
    async def _call_gemini(
        client: httpx.AsyncClient,
        base_url: str,
        model: str,
        api_key: str,
        messages: list[dict],
    ) -> str:
        """Call Gemini API (non-streaming). Uses profile's api_key, base_url, model (with alias for deprecated)."""
        model = GEMINI_MODEL_ALIASES.get(model, model)
        base_url = base_url.rstrip("/")
        system_prompt = next((m["content"] for m in messages if m.get("role") == "system"), "")
        contents = ChatService._openai_to_gemini_contents([m for m in messages if m.get("role") != "system"])
        if not contents:
            return ""
        url = f"{base_url}/models/{model}:generateContent"
        payload = {
            "contents": contents,
            "generationConfig": {"temperature": 0.7},
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        resp = await client.post(
            url,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if resp.status_code != 200:
            if resp.status_code == 429:
                raise LLMRateLimitError(
                    f"Rate limit exceeded (429): {resp.text[:200]}",
                    status_code=429,
                    retry_after_seconds=_parse_retry_after(resp),
                )
            raise ValueError(f"Gemini API error: {resp.status_code} - {resp.text}")
        data = resp.json()
        text = ""
        for c in data.get("candidates", []):
            for p in c.get("content", {}).get("parts", []):
                text += p.get("text", "")
        return text

    @staticmethod
    async def _call_ollama(
        client: httpx.AsyncClient,
        base_url: str,
        model: str,
        messages: list[dict],
    ) -> str:
        """Non-streaming call to Ollama. Returns full response text for tool parsing."""
        resp = await client.post(
            f"{base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json={"model": model, "messages": messages, "stream": False},
        )
        if resp.status_code != 200:
            err = resp.text[:300]
            raise ValueError(f"Ollama error: {err}. Ensure Ollama is running: ollama run {model}")
        data = resp.json()
        content = (data.get("choices", [{}])[0].get("message", {}) or {}).get("content", "") or ""
        return content

    @staticmethod
    async def _stream_openai(
        client: httpx.AsyncClient,
        base_url: str,
        model: str,
        api_key: str,
        messages: list[dict],
        is_ollama: bool = False,
    ) -> AsyncGenerator[str, None]:
        """Stream from OpenAI-compatible API."""
        async with client.stream(
            "POST",
            f"{base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "messages": messages, "stream": True},
        ) as resp:
            if resp.status_code != 200:
                err = await resp.aread()
                err_txt = err.decode()[:300]
                if resp.status_code == 429 and not is_ollama:
                    raise LLMRateLimitError(
                        f"Rate limit exceeded (429): {err_txt}",
                        status_code=429,
                        retry_after_seconds=_parse_retry_after(resp),
                    )
                if is_ollama:
                    raise ValueError(f"Ollama error: {err_txt}. Ensure Ollama is running (ollama run {model}) and model is pulled.")
                raise ValueError(f"LLM API error: {resp.status_code} - {err_txt}")
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        pass

    @staticmethod
    async def _call_openai_with_tools(
        client: httpx.AsyncClient,
        base_url: str,
        model: str,
        api_key: str,
        messages: list[dict],
        tools: list[dict],
        is_ollama: bool = False,
    ) -> dict:
        """Call OpenAI-compatible API (non-streaming) with tools. Returns full message dict."""
        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        resp = await client.post(
            f"{base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if resp.status_code != 200:
            err_txt = resp.text[:300]
            if resp.status_code == 429 and not is_ollama:
                raise LLMRateLimitError(
                    f"Rate limit exceeded (429): {err_txt}",
                    status_code=429,
                    retry_after_seconds=_parse_retry_after(resp),
                )
            if is_ollama:
                raise ValueError(f"Ollama error: {err_txt}. Ensure Ollama is running (ollama run {model}) and model is pulled.")
            raise ValueError(f"LLM API error: {resp.status_code} - {err_txt}")
        data = resp.json()
        msg = data.get("choices", [{}])[0].get("message", {})
        return msg

    @staticmethod
    async def stream_chat(
        data: ChatDataSupabase,
        user_id: str,
        message: str,
        conversation_id: str | None = None,
        profile_id: str | None = None,
        ollama_model: str | None = None,
        save_to_memory: bool = False,
        memory_kind: str = "fact",
        collection_ids: list[str] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream chat response using Supabase REST. Yields SSE events with:
        - text: chunk of response
        - debug: memory/cache info
        - done: final metadata
        Uses profile's api_key, provider_base_url, model_name, api_style.
        When ollama_model is set, uses local Ollama (available to all users as "default").
        """
        profile: dict | None = None

        if ollama_model:
            # Use local Ollama - no API key, available to all users
            models = await list_ollama_models()
            if not models or not any(m.get("name") == ollama_model for m in models):
                raise ValueError(f"Ollama model '{ollama_model}' not found. Run: ollama pull {ollama_model}")
            profile = {
                "provider_base_url": app_settings.ollama_base_url,
                "model_name": ollama_model,
                "api_style": "openai",
                "api_key": "ollama",  # Ollama ignores Bearer; non-empty for downstream
            }
        else:
            # 1. Resolve profile (api_key, provider_base_url, model)
            if not profile_id:
                profile_id = data.get_active_profile_id(user_id)
            if not profile_id:
                raise ValueError("No model profile selected. Add one in Settings or select 'default' for local Llama.")

            profile = data.get_profile_with_api_key(str(profile_id), user_id)
            if not profile or not profile.get("api_key"):
                raise ValueError("Model profile not found or API key missing.")

        is_ollama = bool(ollama_model)

        # 2. Get or create conversation (track if we created it for error rollback)
        conv_id = conversation_id
        created_new = not bool(conv_id)
        if not conv_id:
            conv_id = data.create_conversation(user_id)

        # 3. Persist user message
        data.insert_message(conv_id, user_id, "user", message)

        # 3b. RAG search (if user selected collections)
        rag_results = []
        external_db_names = []
        if collection_ids:
            try:
                rag_results = data.search_rag(user_id, collection_ids, message, limit=5)
                from src.services.document_service_supabase import DocumentServiceSupabase
                from src.supabase_client import get_supabase_admin
                sb = get_supabase_admin()
                if sb:
                    doc_svc = DocumentServiceSupabase(sb)
                    external_db_names = doc_svc.get_collection_names(user_id, collection_ids)
            except Exception as e:
                logger.warning("RAG search failed: %s", e)

        # 4. External memory (with cache - In-Cache Memory)
        cache_key = f"mem:{user_id}"
        memory_cache_hit, memory_items = _cache_get(_memory_cache, cache_key, _memory_cache_ttl)
        if not memory_cache_hit:
            memory_items = data.get_recent_memory(user_id, limit=10)
            _cache_set(_memory_cache, cache_key, memory_items)
        if memory_items is None:
            memory_items = []

        memory_context = ""
        if memory_items:
            memory_context = "\n\n[External memory - from previous sessions]:\n"
            for m in memory_items:
                memory_context += f"- [{m['kind']}] {m['text']}\n"

        # 5. In-context memory - recent messages
        msg_rows = data.get_messages(conv_id, MAX_CONTEXT_MESSAGES + 1)
        messages_for_llm = [{"role": r["role"], "content": r["content"]} for r in msg_rows]

        # 6. Get MCP tools, resources, prompts (with cache)
        servers = data.get_user_servers(user_id)
        all_tools: list[dict] = []
        tools_with_server: list[tuple[str, dict]] = []  # (server_url, tool)
        all_resources: list[dict] = []
        all_prompts: list[dict] = []
        tool_cache_hits = 0
        for srv in servers:
            srv_id = str(srv["id"])
            srv_url = (srv.get("server_url") or "").rstrip("/")
            if not srv_url:
                continue
            try:
                cache_key = f"tools:{srv_id}"
                hit, cached_tools = _cache_get(_tool_list_cache, cache_key, _cache_ttl)
                if hit:
                    tools = cached_tools
                    tool_cache_hits += 1
                else:
                    tools = await data.list_tools_for_server(srv_url)
                    _cache_set(_tool_list_cache, cache_key, tools)
                all_tools.extend(tools)
                for t in tools:
                    tools_with_server.append((srv_url, t))
                resources = await data.list_resources_for_server(srv_url)
                all_resources.extend(resources)
                prompts_list = await data.list_prompts_for_server(srv_url)
                all_prompts.extend(prompts_list)
            except Exception as e:
                logger.warning("Failed to load MCP tools from server %s: %s", srv_url, e)

        # Build tool_name -> server_url map for execution
        tool_to_server: dict[str, str] = {}
        for srv_url, t in tools_with_server:
            name = t.get("name") or ""
            if name and name not in tool_to_server:
                tool_to_server[name] = srv_url

        # Ollama: base llama3/llama2 do NOT support tools - skip MCP to avoid 400
        model = profile.get("model_name") or ""
        ollama_tools_disabled_msg: str | None = None
        if is_ollama and tools_with_server and not ollama_model_supports_tools(model):
            tools_with_server = []
            all_tools = []
            tool_to_server = {}
            ollama_tools_disabled_msg = (
                f"Ollama model '{model}' does not support tools. "
                "For MCP tools, use: llama3.1, qwen3, mistral-nemo, or similar."
            )

        # Build system prompt. Put static content first for prompt/KV cache reuse where supported.
        system_prompt = """You are a helpful AI assistant with agentic memory.
MEMORY: In-context (recent msgs), external (past sessions), in-weights (knowledge). Prefer tools for live data."""
        if all_resources:
            res_list = "\n".join(f"- {r.get('uri', '')}: {r.get('name', '') or r.get('description', '')}" for r in all_resources)
            system_prompt += f"\n\n[Available resources - use when relevant]:\n{res_list}"
        if all_prompts:
            pr_list = "\n".join(f"- {p.get('name', '')}: {p.get('description', '')}" for p in all_prompts)
            system_prompt += f"\n\n[Available prompts]:\n{pr_list}"
        cache_key_prefix: str | None = None
        if all_tools:
            tool_names = {t.get("name", "") for t in all_tools if t.get("name")}
            # Dynamic tool order: inferred from user message first, then notes/todos, then rest
            _BASE_PRIORITY = ("save_note", "list_notes", "list_notes_json", "get_notes_summary", "add_todo", "list_todos", "list_todos_json", "complete_todo", "set_reminder", "list_reminders")
            inferred = _infer_priority_tools(message, tool_names)
            def _sort_key(t: dict) -> tuple:
                name = (t.get("name") or "").lower()
                if name in inferred:
                    return (0, inferred.index(name))  # Message-relevant tools first
                try:
                    return (1, _BASE_PRIORITY.index(name)) if name in _BASE_PRIORITY else (2, 0)
                except ValueError:
                    return (2, 0)
            ordered = sorted(all_tools, key=_sort_key)
            # Reorder tools_with_server so LangGraph/bind_tools sees same order (model sees inferred tools first)
            name_to_pair = {(t.get("name") or ""): (srv, t) for srv, t in tools_with_server}
            tools_with_server = [name_to_pair[t.get("name")] for t in ordered if (t.get("name") or "") in name_to_pair]
            tool_list = "\n".join(
                f"- {t.get('name', '?')}: {t.get('description', 'No description')}"
                for t in ordered
            )
            tool_list_primary = "\n".join(
                f"- {t.get('name', '?')}: {t.get('description', '')}"
                for t in ordered[:12]  # First 12 for compact primary block
            )
            base_url = (profile.get("provider_base_url") or "").lower()
            is_ollama_like = is_ollama or "ollama" in base_url or "11434" in base_url
            system_prompt += _build_agent_tool_prompt(
                tool_list, tool_list_primary, is_ollama_like, message, tool_names
            )
            cache_key_prefix = f"tools:{tool_list[:2000]}" if tool_list else None

        # Variable context last (helps prompt/KV cache hit on static prefix)
        if memory_context:
            system_prompt += memory_context
        if rag_results:
            rag_context = "\n\n[RAG - user documents]:\n"
            for r in rag_results:
                rag_context += f"- {r.get('content', '')[:300]}...\n"
            system_prompt += rag_context

        # 7. Call LLM via LangGraph (unified model + tool handling)
        model = profile["model_name"]
        base_url = (profile.get("provider_base_url") or "").rstrip("/")

        if save_to_memory:
            messages_for_llm = list(messages_for_llm)
            for i in range(len(messages_for_llm) - 1, -1, -1):
                if messages_for_llm[i].get("role") == "user":
                    m = dict(messages_for_llm[i])
                    m["content"] = (m.get("content", "") +
                        "\n\n[User requested: save the key information from this message to memory]")
                    messages_for_llm[i] = m
                    break

        full_content = ""
        tools_executed: list[str] = []
        tracer = GraphTracer()
        try:
            graph = create_chat_graph(
                profile, tools_with_server, data, user_id, conv_id, cache_key_prefix
            )
            async for event in stream_chat_with_graph(
                graph, system_prompt, messages_for_llm, tools_executed, tracer=tracer
            ):
                yield event
                try:
                    d = json.loads(event.get("data", "{}"))
                    if d.get("type") == "tool_start":
                        full_content = ""
                    elif d.get("type") == "text":
                        full_content += d.get("content", "")
                except Exception:
                    pass
        except LLMRateLimitError as e:
            if created_new and conv_id:
                try:
                    data.delete_conversation(conv_id, user_id)
                except Exception:
                    pass
            else:
                try:
                    data.delete_last_user_message(conv_id, user_id)
                except Exception:
                    pass
            payload = {"type": "error", "content": str(e)}
            yield {"data": json.dumps(payload)}
            return
        except Exception as e:
            if created_new and conv_id:
                try:
                    data.delete_conversation(conv_id, user_id)
                except Exception:
                    pass
            else:
                try:
                    data.delete_last_user_message(conv_id, user_id)
                except Exception:
                    pass
            err_msg = str(e)
            try:
                from langgraph.errors import GraphRecursionError
                if isinstance(e, GraphRecursionError):
                    err_msg = (
                        "The AI hit a limit while using tools. "
                        "Try a simpler prompt or rephrase (e.g. provide your name and what to save explicitly)."
                    )
            except ImportError:
                if "recursion limit" in err_msg.lower():
                    err_msg = (
                        "The AI hit a limit while using tools. "
                        "Try a simpler prompt or rephrase (e.g. provide your name and what to save explicitly)."
                    )
            if is_ollama:
                err_lower = err_msg.lower()
                if "connect" in err_lower or "connection" in err_lower or "refused" in err_lower or "reset" in err_lower:
                    err_msg = (
                        f"Ollama connection failed: {err_msg}. "
                        f"Ensure Ollama is running: ollama run {ollama_model or 'llama3:latest'}"
                    )
            payload = {"type": "error", "content": err_msg}
            yield {"data": json.dumps(payload)}
            return

        # 8. Persist assistant message (fallback: if tools ran but agent gave no text, use confirmation)
        to_persist = full_content or ""
        if not to_persist and tools_executed:
            to_persist = f"Executed: {', '.join(tools_executed)}."
        msg_id = data.insert_message(conv_id, user_id, "assistant", to_persist)

        # 8a. Update conversation title - AI-generated for new chats, fallback to truncated
        if created_new and message:
            title = None
            try:
                api_key = (profile.get("api_key") or "").strip()
                api_style = profile.get("api_style", "openai")
                async with httpx.AsyncClient(timeout=15.0) as client:
                    title = await ChatService._generate_chat_title(
                        client, base_url, model, api_key, api_style,
                        first_message=message,
                        assistant_preview=to_persist[:200] if to_persist else "",
                    )
            except Exception:
                pass
            if not title or len(title) > 80:
                trimmed = message.strip()
                title = (trimmed[:50] + "…") if len(trimmed) > 50 else trimmed
            if title:
                try:
                    data.update_conversation_title(conv_id, user_id, title)
                except Exception:
                    pass

        # 8b. Save message metadata and prompt trace (for visualization)
        if msg_id:
            prompt_trace = {
                "system_prompt_preview": system_prompt[:500] + ("..." if len(system_prompt) > 500 else ""),
                "rag_chunks": len(rag_results),
                "memory_items": len(memory_items),
                "tools_available": len(all_tools),
                "memory_cache_hit": memory_cache_hit,
            }
            # Merge graph execution steps for flow visualization
            extra = tracer.to_prompt_trace_extra()
            if extra:
                prompt_trace.update(extra)
            data.save_message_metadata(
                msg_id,
                conv_id,
                tools_used=tools_executed,
                external_dbs_used=external_db_names,
                in_context_count=len(messages_for_llm),
                prompt_trace=prompt_trace,
                model_used=model,
            )

        # 9. Save to memory if requested
        if save_to_memory and to_persist:
            data.create_memory_item(user_id, memory_kind, to_persist[:500], conv_id)

        # 10. Yield debug info (memory indicators - distinguishable in chat)
        debug_payload: dict = {
            "type": "debug",
            "memory": {
                "in_context_messages": len(messages_for_llm),
                "external_memory_items": len(memory_items),
                "memory_cache_hit": memory_cache_hit,
                "tool_cache_hits": tool_cache_hits,
                "tools_available": len(all_tools),
                "tools_used": tools_executed,
                "external_dbs_used": external_db_names,
                "rag_chunks_retrieved": len(rag_results),
            },
        }
        if ollama_tools_disabled_msg:
            debug_payload["memory"]["ollama_tools_disabled"] = ollama_tools_disabled_msg
        yield {"data": json.dumps(debug_payload)}
        yield {"data": json.dumps({"type": "done", "conversation_id": conv_id})}
