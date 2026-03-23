"""MCP Stocks - get stock quotes (demo)."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Stocks", json_response=True, host="0.0.0.0", port=8017, stateless_http=True)

_DEMO_QUOTES = {"AAPL": 175.50, "GOOGL": 140.20, "MSFT": 378.90}


@mcp.tool()
def get_quote(symbol: str) -> str:
    """Get current stock quote. Params: symbol (required, e.g. AAPL, GOOGL, MSFT)."""
    s = symbol.upper()
    if s in _DEMO_QUOTES:
        return f"{s}: ${_DEMO_QUOTES[s]} (demo data)"
    return f"[Demo] {s}: Use yfinance or Alpha Vantage for real quotes."


@mcp.tool()
def get_historical(symbol: str, days: int = 30) -> str:
    """Get historical stock data for symbol."""
    return f"[Demo] Historical {symbol} for {days} days. Add yfinance for real data."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
