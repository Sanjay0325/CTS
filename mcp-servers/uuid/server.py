"""MCP UUID - generate UUIDs."""

import uuid
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("UUID", json_response=True, host="0.0.0.0", port=8022, stateless_http=True)


@mcp.tool()
def generate_uuid() -> str:
    """Generate a random UUID v4."""
    return str(uuid.uuid4())


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
