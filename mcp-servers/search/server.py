"""MCP Search server - mock search for demo."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Search", json_response=True, host="0.0.0.0", port=8006, stateless_http=True)


@mcp.tool()
def search(query: str) -> str:
    """Search for information. Params: query (required). Demo - returns mock results. Add real search API for production."""
    return f"Search results for '{query}': [Demo result 1] [Demo result 2]. Add a real search API for production."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
