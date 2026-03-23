"""MCP Wikipedia - search Wikipedia (demo)."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Wikipedia", json_response=True, host="0.0.0.0", port=8013, stateless_http=True)


@mcp.tool()
def search_wikipedia(query: str, limit: int = 3) -> str:
    """Search Wikipedia for a topic. Returns summary. Use real API for production."""
    return f"Wikipedia search for '{query}': [Demo] Add wikipedia-api or requests to fetch real summaries. Limit: {limit} results."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
