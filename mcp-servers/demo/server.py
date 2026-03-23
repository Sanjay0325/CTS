"""Sample MCP server exposing demo tools for CTS."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("CTS Demo Server", json_response=True, host="0.0.0.0", port=8001, stateless_http=True)


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


@mcp.tool()
def get_current_time() -> str:
    """Get the current date and time as a string."""
    from datetime import datetime
    return datetime.now().isoformat()


@mcp.tool()
def echo(message: str) -> str:
    """Echo back the given message."""
    return f"Echo: {message}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
