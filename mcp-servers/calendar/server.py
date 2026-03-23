"""MCP Calendar - create and list events (demo)."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Calendar", json_response=True, host="0.0.0.0", port=8015, stateless_http=True)

_events: list[dict] = []


@mcp.tool()
def create_event(title: str, start: str, end: str, description: str = "") -> str:
    """Create a calendar event. Dates: YYYY-MM-DD. Times: HH:MM."""
    _events.append({"title": title, "start": start, "end": end, "description": description})
    return f"Created event: {title} ({start} - {end})"


@mcp.tool()
def list_events(start_date: str = "", end_date: str = "") -> str:
    """List calendar events. Optional date range: YYYY-MM-DD."""
    if not _events:
        return "No events."
    return "\n".join(f"- {e['title']}: {e['start']} to {e['end']}" for e in _events)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
