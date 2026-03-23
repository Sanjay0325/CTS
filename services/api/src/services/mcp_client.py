"""
Unified MCP JSON-RPC client — single module for all MCP server communication.

Replaces duplicated JSON-RPC logic from chat_data_supabase.py, mcp_service_supabase.py,
and mcp_data_service.py. Uses a shared httpx.AsyncClient for connection reuse.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Default timeout for MCP calls
MCP_TIMEOUT = 30.0

# Shared httpx client — initialized at app startup via init_mcp_client(), closed at shutdown.
_shared_client: httpx.AsyncClient | None = None


def init_mcp_client() -> httpx.AsyncClient:
    """Create and cache the shared httpx client. Call once at app startup."""
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            timeout=MCP_TIMEOUT,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
    return _shared_client


async def close_mcp_client() -> None:
    """Close the shared client. Call at app shutdown."""
    global _shared_client
    if _shared_client and not _shared_client.is_closed:
        await _shared_client.aclose()
        _shared_client = None


def get_mcp_client() -> httpx.AsyncClient:
    """Get the shared httpx client. Auto-inits if needed."""
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        init_mcp_client()
    return _shared_client


def _mcp_url(server_url: str) -> str:
    """Ensure server URL ends with /mcp."""
    url = server_url.rstrip("/")
    return url if "/mcp" in url else f"{url}/mcp"


async def mcp_rpc(
    server_url: str,
    method: str,
    params: dict | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict:
    """
    Make a single JSON-RPC call to an MCP server.

    Returns the 'result' dict on success, or {'error': str} on failure.
    """
    http = client or get_mcp_client()
    url = _mcp_url(server_url)
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {},
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "mcp-protocol-version": "2025-03-26",
    }
    try:
        resp = await http.post(url, json=payload, headers=headers)
        data = resp.json() if resp.content else {}
        if "error" in data:
            err = data["error"]
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            logger.warning("MCP RPC error on %s %s: %s", url, method, msg)
            return {"error": msg}
        if resp.status_code != 200:
            logger.warning("MCP HTTP %d on %s %s", resp.status_code, url, method)
            return {"error": f"HTTP {resp.status_code}"}
        return data.get("result", {})
    except httpx.TimeoutException:
        logger.warning("MCP timeout on %s %s", url, method)
        return {"error": "MCP call timed out"}
    except httpx.RequestError as e:
        logger.warning("MCP connection error on %s %s: %s", url, method, e)
        return {"error": f"Connection error: {e!s}"}
    except Exception as e:
        logger.exception("MCP unexpected error on %s %s", url, method)
        return {"error": f"Unexpected error: {e!s}"}


# ─── High-level helpers ─────────────────────────────────────────────


async def list_tools(server_url: str) -> list[dict]:
    """List tools from an MCP server."""
    result = await mcp_rpc(server_url, "tools/list")
    if "error" in result:
        return []
    return result.get("tools", [])


async def list_resources(server_url: str) -> list[dict]:
    """List resources from an MCP server."""
    result = await mcp_rpc(server_url, "resources/list")
    if "error" in result:
        return []
    return result.get("resources", [])


async def list_prompts(server_url: str) -> list[dict]:
    """List prompts from an MCP server."""
    result = await mcp_rpc(server_url, "prompts/list")
    if "error" in result:
        return []
    return result.get("prompts", [])


async def call_tool(server_url: str, tool_name: str, arguments: dict) -> str | None:
    """
    Execute a tool on an MCP server via tools/call.
    Returns result text, error message, or None.
    """
    result = await mcp_rpc(
        server_url,
        "tools/call",
        {"name": tool_name, "arguments": dict(arguments) if arguments else {}},
    )
    if "error" in result:
        return f"Tool error: {result['error']}"
    if result.get("isError"):
        content = result.get("content", [])
        parts = [
            c.get("text", "")
            for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        ]
        return f"Tool reported error: {' '.join(parts) or 'Unknown'}"
    content = result.get("content", [])
    parts = []
    for c in content:
        if isinstance(c, dict) and c.get("type") == "text":
            parts.append(str(c.get("text", "")))
    return "\n".join(parts) if parts else str(result)


async def check_health(server_url: str) -> bool:
    """Quick health check — returns True if server responds to tools/list within 5s."""
    http = get_mcp_client()
    url = _mcp_url(server_url)
    try:
        resp = await http.post(
            url,
            json={"jsonrpc": "2.0", "id": 0, "method": "tools/list", "params": {}},
            headers={"Content-Type": "application/json"},
            timeout=5.0,
        )
        return resp.status_code == 200
    except Exception:
        return False
