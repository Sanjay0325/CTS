"""MCP service using Supabase REST API."""

import logging
from datetime import datetime
from uuid import UUID, uuid4

from src.models import MCPServerResponse
from src.services import mcp_client

logger = logging.getLogger(__name__)


class MCPServiceSupabase:
    """MCP server management via Supabase REST."""

    def __init__(self, supabase_client):
        self.sb = supabase_client

    def list_servers(self, user_id: str) -> list[MCPServerResponse]:
        """List MCP servers for user."""
        r = (
            self.sb.table("mcp_servers")
            .select("id, name, server_url, transport, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        rows = r.data or []
        return [
            MCPServerResponse(
                id=row["id"],
                name=row["name"],
                server_url=row["server_url"],
                transport=row["transport"],
                created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            )
            for row in rows
        ]

    def register_server(
        self,
        user_id: str,
        name: str,
        server_url: str,
        transport: str = "streamable-http",
    ) -> MCPServerResponse:
        """Register an MCP server."""
        server_id = str(uuid4())
        row_data = {
            "id": server_id,
            "user_id": user_id,
            "name": name,
            "server_url": server_url.rstrip("/"),
            "transport": transport,
        }
        r = self.sb.table("mcp_servers").insert(row_data).execute()
        if not r.data or len(r.data) == 0:
            raise ValueError("Failed to create MCP server")
        row = r.data[0]
        logger.info("Registered MCP server '%s' at %s for user %s", name, server_url, user_id)
        return MCPServerResponse(
            id=row["id"],
            name=row["name"],
            server_url=row["server_url"],
            transport=row["transport"],
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
        )

    def delete_server(self, server_id: UUID, user_id: str) -> bool:
        """Delete an MCP server."""
        r = (
            self.sb.table("mcp_servers")
            .delete()
            .eq("id", str(server_id))
            .eq("user_id", user_id)
            .execute()
        )
        return bool(r.data and len(r.data) > 0)

    def _get_server_url(self, server_id: UUID, user_id: str) -> str | None:
        """Get server_url for a server owned by user."""
        r = (
            self.sb.table("mcp_servers")
            .select("server_url")
            .eq("id", str(server_id))
            .eq("user_id", user_id)
            .execute()
        )
        if not r.data or len(r.data) == 0:
            return None
        return (r.data[0].get("server_url") or "").rstrip("/") or None

    async def list_tools(self, server_id: UUID, user_id: str) -> list[dict]:
        """List tools from an MCP server via shared httpx client."""
        url = self._get_server_url(server_id, user_id)
        if not url:
            return []
        return await mcp_client.list_tools(url)

    async def list_resources(self, server_id: UUID, user_id: str) -> list[dict]:
        """List resources from an MCP server via shared httpx client."""
        url = self._get_server_url(server_id, user_id)
        if not url:
            return []
        return await mcp_client.list_resources(url)

    async def list_prompts(self, server_id: UUID, user_id: str) -> list[dict]:
        """List prompts from an MCP server via shared httpx client."""
        url = self._get_server_url(server_id, user_id)
        if not url:
            return []
        return await mcp_client.list_prompts(url)

