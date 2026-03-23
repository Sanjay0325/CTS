"""Tests for JSON-as-text tool-call fallback in chat_graph (Ollama/Llama)."""

import pytest

from src.langgraph_services.chat_graph import _try_parse_tool_call_from_text


def test_parse_save_note_json():
    """Model returns save_note as JSON in text (screenshot case)."""
    content = '{"function": "save_note", "name": "mcp server", "title": "confirm that", "content": "the thing I think about you"}'
    tool_map = {"save_note": "save_note", "add_todo": "add_todo"}
    out = _try_parse_tool_call_from_text(content, tool_map)
    assert out is not None
    assert out["name"] == "save_note"
    assert "title" in out["args"]
    assert out["args"]["title"] == "confirm that"
    assert "content" in out["args"]
    assert "name" not in out["args"]  # "mcp server" filtered out


def test_parse_name_and_kwargs_format():
    """Model returns {\"name\": \"save_note\", \"kwargs\": {...}} (new screenshot format)."""
    content = '{"name": "save_note", "kwargs": {"title": "mcp server", "content": "the thing you think about me"}}'
    tool_map = {"save_note": "save_note", "add_todo": "add_todo"}
    out = _try_parse_tool_call_from_text(content, tool_map)
    assert out is not None
    assert out["name"] == "save_note"
    assert out["args"]["title"] == "mcp server"
    assert out["args"]["content"] == "the thing you think about me"


def test_parse_add_todo_json():
    """Model returns add_todo as JSON."""
    content = '{"tool": "add_todo", "task": "Buy milk", "priority": "high"}'
    tool_map = {"save_note": "save_note", "add_todo": "add_todo"}
    out = _try_parse_tool_call_from_text(content, tool_map)
    assert out is not None
    assert out["name"] == "add_todo"
    assert out["args"]["task"] == "Buy milk"
    assert out["args"]["priority"] == "high"


def test_parse_json_in_code_block():
    """JSON wrapped in markdown code block."""
    content = '```json\n{"function": "save_note", "title": "Note", "content": "Hello"}\n```'
    tool_map = {"save_note": "save_note"}
    out = _try_parse_tool_call_from_text(content, tool_map)
    assert out is not None
    assert out["name"] == "save_note"
    assert out["args"]["title"] == "Note"
    assert out["args"]["content"] == "Hello"


def test_parse_unknown_tool_returns_none():
    """Unknown tool name returns None."""
    content = '{"function": "unknown_tool", "title": "x", "content": "y"}'
    tool_map = {"save_note": "save_note"}
    out = _try_parse_tool_call_from_text(content, tool_map)
    assert out is None


def test_parse_invalid_json_returns_none():
    """Invalid JSON returns None."""
    content = 'not json at all'
    tool_map = {"save_note": "save_note"}
    out = _try_parse_tool_call_from_text(content, tool_map)
    assert out is None


def test_parse_empty_content_returns_none():
    """Empty content returns None."""
    tool_map = {"save_note": "save_note"}
    assert _try_parse_tool_call_from_text("", tool_map) is None
    assert _try_parse_tool_call_from_text("   ", tool_map) is None
