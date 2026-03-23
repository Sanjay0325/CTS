"""MCP News - get news (demo)."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("News", json_response=True, host="0.0.0.0", port=8016, stateless_http=True)


@mcp.tool()
def get_news(topic: str = "technology", limit: int = 5) -> str:
    """Get news articles. Topic: technology, business, etc. Use news API for production."""
    return f"[Demo] News for '{topic}': Add newsapi.org or similar for real news. Limit: {limit}."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
