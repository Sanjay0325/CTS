"""MCP Hash - generate hashes."""

import hashlib
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Hash", json_response=True, host="0.0.0.0", port=8021, stateless_http=True)


@mcp.tool()
def hash_md5(text: str) -> str:
    """Generate MD5 hash of text."""
    return hashlib.md5(text.encode()).hexdigest()


@mcp.tool()
def hash_sha256(text: str) -> str:
    """Generate SHA-256 hash of text."""
    return hashlib.sha256(text.encode()).hexdigest()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
