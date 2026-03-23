"""MCP Timezone server - time and timezone utilities."""

from datetime import datetime
from zoneinfo import ZoneInfo

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Timezone", json_response=True, host="0.0.0.0", port=8005, stateless_http=True)


@mcp.tool()
def get_time_in_timezone(timezone: str = "UTC") -> str:
    """Get current time in a timezone (e.g. America/New_York, Europe/London)."""
    try:
        tz = ZoneInfo(timezone)
        return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return f"Invalid timezone: {timezone}"


@mcp.tool()
def list_common_timezones() -> str:
    """List common timezone identifiers."""
    return "UTC, America/New_York, America/Los_Angeles, Europe/London, Europe/Paris, Asia/Tokyo, Asia/Kolkata"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
