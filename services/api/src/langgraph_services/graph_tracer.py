"""
Graph execution tracer - captures agent/tools flow for visualization.

Collects step-by-step execution from LangGraph astream_events:
- agent cycles (LLM calls)
- tool invocations with name, sanitized args, result preview
- Mermaid flowchart with detailed tool info (args, result)
"""

from typing import Any


MAX_RESULT_PREVIEW = 200


class GraphTracer:
    """Accumulates graph execution steps for prompt_trace visualization."""

    def __init__(self):
        self.steps: list[dict[str, Any]] = []
        self._current_tool: dict[str, Any] | None = None
        self._agent_round = 0
        self._tools_in_round = 0

    def on_event(self, event: dict) -> None:
        """Process a single astream_events item."""
        kind = event.get("event")
        if kind == "on_tool_start":
            if self._tools_in_round == 0:
                self._agent_round += 1
                self.steps.append({
                    "type": "agent",
                    "round": self._agent_round,
                    "label": f"Agent (LLM) round {self._agent_round}",
                })
            self._tools_in_round += 1
            data = event.get("data", {})
            args = data.get("input", {})
            name = event.get("name", "unknown")
            args_str = _format_args_for_label(args)
            self._current_tool = {
                "type": "tool",
                "name": name,
                "args_preview": _sanitize_for_trace(args),
                "args_label": args_str,
                "round": self._agent_round,
            }
        elif kind == "on_tool_end":
            self._tools_in_round = 0
            if self._current_tool:
                output = event.get("data", {}).get("output", "")
                raw = str(output).replace("[TOOL_OUTPUT: ", "").split("\n", 1)
                content = raw[1] if len(raw) > 1 else raw[0]
                self._current_tool["result_preview"] = _truncate(content, MAX_RESULT_PREVIEW)
                self.steps.append(self._current_tool)
                self._current_tool = None
        elif kind == "on_chat_model_stream":
            if not self.steps:
                self._agent_round = 1
                self.steps.append({
                    "type": "agent",
                    "round": 1,
                    "label": "Agent (LLM) - response",
                })

    def to_prompt_trace_extra(self) -> dict:
        """Return dict to merge into prompt_trace for storage."""
        if not self.steps:
            return {}
        steps = list(self.steps)
        if any(s.get("type") == "tool" for s in steps):
            steps.append({
                "type": "agent",
                "round": self._agent_round + 1,
                "label": "Agent (LLM) - final response",
            })
        return {
            "graph_steps": steps,
            "mermaid": _build_mermaid(steps),
        }


def _format_args_for_label(args: Any) -> str:
    """Format args as tool_name(a=b, c=d) for Mermaid label."""
    if not isinstance(args, dict) or not args:
        return ""
    parts = []
    for k, v in list(args.items())[:4]:  # max 4 params
        if k.lower() in ("api_key", "password", "secret", "user_id", "conversation_id"):
            continue
        val = _truncate(str(v), 25)
        if val:
            parts.append(f"{k}={val}")
    return ", ".join(parts) if parts else ""


def _sanitize_for_trace(obj: Any) -> str:
    """Sanitize args for trace (no API keys, reasonable length)."""
    if obj is None:
        return ""
    if isinstance(obj, dict):
        safe = {}
        for k, v in obj.items():
            if k.lower() in ("api_key", "password", "secret"):
                safe[k] = "***"
            else:
                safe[k] = _truncate(str(v), 80)
        return str(safe)
    return _truncate(str(obj), 150)


def _truncate(s: str, max_len: int) -> str:
    if not s or len(s) <= max_len:
        return s
    return s[:max_len] + "…"


def _escape_mermaid(s: str, max_len: int = 50) -> str:
    """Escape and truncate for Mermaid node label."""
    out = (
        str(s)
        .replace('"', "'")
        .replace("[", "(")
        .replace("]", ")")
        .replace("\n", " ")
        .replace("{", "(")
        .replace("}", ")")
        .replace("|", "-")
    )
    if len(out) > max_len:
        out = out[:max_len - 3] + "..."
    return out


def _build_mermaid(steps: list[dict]) -> str:
    """Build Mermaid flowchart with detailed tool info (name, args, result preview)."""
    lines = ["flowchart TD", "    Start((Start))"]
    node_id = 0
    prev = "Start"
    for s in steps:
        node_id += 1
        t = s.get("type", "")
        nid = f"N{node_id}"
        if t == "agent":
            label = s.get("label", f"Agent round {s.get('round', 1)}")
            safe = _escape_mermaid(label, 55)
            lines.append(f'    {nid}["{safe}"]')
        elif t == "tool":
            name = s.get("name", "tool")
            args_label = s.get("args_label", "")
            result = s.get("result_preview", "")
            if args_label:
                tool_label = f"{name}({args_label})"
            else:
                tool_label = name
            if result:
                tool_label += " → " + _truncate(result, 35)
            safe_tool = _escape_mermaid(tool_label, 60)
            lines.append(f'    {nid}["🔧 {safe_tool}"]')
        else:
            label = s.get("label", s.get("name", f"Step {node_id}"))
            safe = _escape_mermaid(str(label), 55)
            lines.append(f'    {nid}["{safe}"]')
        lines.append(f"    {prev} --> {nid}")
        prev = nid
    lines.append(f"    {prev} --> End((End))")
    return "\n".join(lines)
