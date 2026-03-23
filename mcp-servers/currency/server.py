"""MCP Currency - convert currencies and get rates (demo)."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Currency", json_response=True, host="0.0.0.0", port=8012, stateless_http=True)

# Demo rates - replace with real API (e.g. exchangerate-api.com)
_RATES = {"USD": 1.0, "EUR": 0.92, "GBP": 0.79, "INR": 83.0, "JPY": 149.0}


@mcp.tool()
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert amount between currencies. Params: amount (number), from_currency (ISO code), to_currency (ISO code).
    Use when: convert X to Y, exchange rate, USD to INR. Supported: USD, EUR, GBP, INR, JPY."""
    fc = from_currency.upper()
    tc = to_currency.upper()
    if fc not in _RATES or tc not in _RATES:
        return f"Unknown currency. Supported: {', '.join(_RATES)}"
    usd = amount / _RATES[fc]
    result = usd * _RATES[tc]
    return f"{amount} {fc} = {result:.2f} {tc}"


@mcp.tool()
def get_rates(base: str = "USD") -> str:
    """Get exchange rates for a base currency."""
    if base.upper() not in _RATES:
        return f"Unknown base. Supported: {', '.join(_RATES)}"
    b = _RATES[base.upper()]
    lines = [f"1 {base.upper()} = {_RATES[c]/b:.4f} {c}" for c in _RATES if c != base.upper()]
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
