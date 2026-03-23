"""
LangGraph chat agent - tool-calling loop with model abstraction.

Flow: START → agent → [tools if tool_calls] → agent (loop) → END.
State: messages use add_messages reducer; ToolMessages append after AIMessage(tool_calls).
Tool output is in state when agent runs again, so the LLM gets results for final response.

Works for: API-key models (OpenAI, etc.) via native tool_calls; Ollama via JSON-as-text fallback.
Fallback: When Ollama/Llama returns tool calls as JSON ({"name":"save_note","kwargs":{...}} or similar),
we parse and convert to structured tool_calls so the graph routes to tools.
"""

import json
import logging
import re
import uuid
from typing import Annotated, Any, AsyncGenerator, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from src.langgraph_services.graph_tracer import GraphTracer
from src.langgraph_services.model_factory import create_chat_model_from_profile
from src.langgraph_services.mcp_tools import build_mcp_tools
from src.services.chat_data_supabase import ChatDataSupabase

logger = logging.getLogger(__name__)


def _try_parse_tool_call_from_text(content: str, tool_name_map: dict[str, str]) -> dict | None:
    """
    Parse JSON tool call from model text (Ollama/Llama sometimes returns tool calls as text).
    Supports formats:
      {"function":"save_note","title":"x","content":"y"}
      {"name":"save_note","kwargs":{"title":"x","content":"y"}}
      {"tool":"save_note","args":{...}}
    tool_name_map: normalized name -> actual tool name.
    Returns {"name": str, "args": dict} if valid, else None.
    """
    if not content or not isinstance(content, str):
        return None
    text = content.strip()
    block_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if block_match:
        text = block_match.group(1)
    if "{" not in text:
        return None
    start = text.index("{")
    depth = 0
    end = -1
    for i, c in enumerate(text[start:], start):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end < 0:
        return None
    try:
        obj = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    raw_name = (
        obj.get("function")
        or obj.get("tool")
        or obj.get("tool_name")
        or obj.get("name")  # e.g. {"name":"save_note","kwargs":{...}}
    )
    if not raw_name or not isinstance(raw_name, str):
        return None
    normalized = raw_name.strip().lower().replace(" ", "_")
    actual_name = tool_name_map.get(normalized)
    if not actual_name:
        return None
    meta = {"function", "tool", "tool_name", "name"}
    if isinstance(obj.get("kwargs"), dict):
        args = dict(obj["kwargs"])
    elif isinstance(obj.get("args"), dict):
        args = dict(obj["args"])
        args.update({k: v for k, v in obj.items() if k not in meta and k != "args" and v is not None})
    else:
        args = {k: v for k, v in obj.items() if k not in meta and v is not None}
    args = {k: v for k, v in args.items() if not (k == "name" and str(v).strip().lower() == "mcp server")}
    return {"name": actual_name, "args": args}


def _content_to_str(content: Any) -> str:
    """Normalize LLM content to string. Handles str or list of content blocks (e.g. Gemini)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif "text" in block:
                    parts.append(block["text"])
        return "".join(parts)
    return str(content)


class GraphState(TypedDict):
    """State for the chat agent graph."""
    messages: Annotated[list[BaseMessage], add_messages]


# Max tool rounds to prevent infinite loops (e.g. Llama 3.1 retrying save_note on error)
MAX_TOOL_ROUNDS = 6


def _should_continue(state: GraphState):
    """Route to tools node if last message has tool_calls, else end. Cap tool rounds to prevent recursion limit."""
    messages = state.get("messages", [])
    if not messages:
        return END
    tool_count = sum(1 for m in messages if isinstance(m, ToolMessage))
    if tool_count >= MAX_TOOL_ROUNDS:
        return END  # Force stop to avoid recursion limit
    last = messages[-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    return END


def create_chat_graph(
    profile: dict,
    tools_with_server: list[tuple[str, dict]],
    data: ChatDataSupabase,
    user_id: str,
    conversation_id: str | None,
    cache_key_prefix: str | None = None,
):
    """
    Create a LangGraph chat agent with tool-calling support.
    Returns compiled graph ready for invoke/stream.
    """
    llm = create_chat_model_from_profile(
        profile, streaming=True, request_timeout=300.0, cache_key_prefix=cache_key_prefix
    )
    tools = build_mcp_tools(tools_with_server, data, user_id, conversation_id)
    llm_with_tools = llm.bind_tools(tools) if tools else llm
    tool_name_map = {t.name.lower().replace(" ", "_"): t.name for t in tools} if tools else {}

    async def agent_node(state: GraphState) -> dict:
        """Call LLM with messages; returns AIMessage (possibly with tool_calls)."""
        messages = state.get("messages", [])
        response = await llm_with_tools.ainvoke(messages)
        # Fallback: Ollama/Llama sometimes returns tool calls as JSON in text instead of tool_calls
        if tools and tool_name_map and not getattr(response, "tool_calls", None):
            content_str = _content_to_str(response.content)
            if content_str:
                parsed = _try_parse_tool_call_from_text(content_str, tool_name_map)
                if parsed:
                    tool_name = parsed["name"]
                    tool_args = parsed["args"]
                    tc_id = f"call_{uuid.uuid4().hex[:12]}"
                    logger.info("Parsed Ollama JSON tool call: %s", tool_name)
                    response = AIMessage(
                        content="",  # Don't echo JSON as text
                        tool_calls=[{
                            "id": tc_id,
                            "name": tool_name,
                            "args": tool_args,
                        }],
                    )
        return {"messages": [response]}

    tool_node = ToolNode(tools) if tools else None

    builder = StateGraph(GraphState)

    def _route_after_agent(state: GraphState):
        return _should_continue(state)

    builder.add_node("agent", agent_node)
    if tool_node:
        builder.add_node("tools", tool_node)

    builder.add_edge(START, "agent")
    if tool_node:
        builder.add_conditional_edges("agent", _route_after_agent)
        builder.add_edge("tools", "agent")
    else:
        builder.add_edge("agent", END)

    return builder.compile()


async def stream_chat_with_graph(
    graph,
    system_prompt: str,
    messages_for_llm: list[dict],
    tools_used_callback: list[str] | None = None,
    tracer: GraphTracer | None = None,
) -> AsyncGenerator[dict, None]:
    """
    Stream chat using LangGraph. Yields SSE-style events.
    tools_used_callback: list to append tool names as they execute.
    tracer: optional GraphTracer to capture execution steps for visualization.
    When tools execute, the agent loops back; tool output is in state and agent gets it for final response.
    """
    lc_messages: list[BaseMessage] = []
    if system_prompt:
        lc_messages.append(SystemMessage(content=system_prompt))
    for m in messages_for_llm:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))

    config = {"recursion_limit": 50}
    full_content = ""

    async for event in graph.astream_events(
        {"messages": lc_messages},
        config=config,
        version="v2",
    ):
        if tracer:
            tracer.on_event(event)

        kind = event.get("event")
        if kind == "on_tool_start":
            full_content = ""
            tool_name = event.get("name", "")
            if tools_used_callback is not None:
                tools_used_callback.append(tool_name)
            yield {"data": json.dumps({"type": "tool_start", "tool": tool_name})}
        elif kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk", {})
            if hasattr(chunk, "content") and chunk.content:
                text = _content_to_str(chunk.content)
                if text:
                    full_content += text
                    yield {"data": json.dumps({"type": "text", "content": text})}
        elif kind == "on_tool_end":
            yield {"data": json.dumps({"type": "tool_done", "tool": event.get("name", "")})}

    if not full_content:
        final = await graph.ainvoke({"messages": lc_messages}, config=config)
        for m in reversed(final.get("messages", [])):
            if isinstance(m, AIMessage) and m.content:
                text = _content_to_str(m.content)
                if text:
                    yield {"data": json.dumps({"type": "text", "content": text})}
                break
