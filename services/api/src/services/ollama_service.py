"""Ollama service - list and use local Llama models (available to all users as 'default')."""

import logging

import httpx

from src.config import settings
from src.core.constants import OLLAMA_TOOL_CAPABLE_PATTERNS

logger = logging.getLogger(__name__)


def ollama_model_supports_tools(model_name: str) -> bool:
    """
    Return True if this Ollama model supports tool/function calling.
    Base llama3 and llama2 do NOT; use llama3.1, qwen3, etc. instead.
    """
    if not model_name or not isinstance(model_name, str):
        return False
    base = model_name.split(":")[0].lower()
    return any(p in base for p in OLLAMA_TOOL_CAPABLE_PATTERNS)


async def list_ollama_models() -> list[dict]:
    """
    List models available from local Ollama.
    Returns list of { name, size, digest, family } or [] if Ollama unreachable.
    """
    url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return []
            data = resp.json()
            models = data.get("models") or []
            result = []
            for m in models:
                name = m.get("name") or m.get("model") or ""
                if not name:
                    continue
                details = m.get("details") or {}
                result.append({
                    "name": name,
                    "size": m.get("size"),
                    "digest": m.get("digest"),
                    "family": details.get("family") or "unknown",
                    "parameter_size": details.get("parameter_size"),
                })
            return result
    except Exception as e:
        logger.debug("Ollama unavailable at %s: %s", url, e)
        return []


def get_ollama_default_model(models: list[dict]) -> str | None:
    """Pick default: env OLLAMA_DEFAULT_MODEL, or first tool-capable, or first Llama, or first any."""
    if settings.ollama_default_model:
        for m in models:
            if m.get("name") == settings.ollama_default_model:
                return settings.ollama_default_model
    # Prefer tool-capable models (llama3.1, qwen3, etc.) for MCP support
    for m in models:
        if ollama_model_supports_tools(m.get("name", "")):
            return m.get("name")
    # Then Llama family
    for m in models:
        family = (m.get("family") or "").lower()
        if "llama" in family:
            return m.get("name")
    return models[0].get("name") if models else None
