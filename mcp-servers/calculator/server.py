"""MCP Calculator server - math operations."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Calculator", json_response=True, host="0.0.0.0", port=8002, stateless_http=True)


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers. Use when user asks: X times Y, multiply A by B, product of."""
    return a * b


@mcp.tool()
def power(base: float, exponent: float) -> float:
    """Raise base to exponent."""
    return base ** exponent


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
