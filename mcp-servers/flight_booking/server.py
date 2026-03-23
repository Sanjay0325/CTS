"""MCP Flight Booking - search and book flights (demo)."""

from datetime import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Flight Booking", json_response=True, host="0.0.0.0", port=8010, stateless_http=True)

_flights: list[dict] = []


@mcp.tool()
def search_flights(origin: str, destination: str, date: str) -> str:
    """Search flights by origin and destination IATA codes (e.g. JFK, LHR) and date (YYYY-MM-DD)."""
    # Demo: return mock results
    _flights.clear()
    _flights.extend([
        {"id": "FL001", "origin": origin, "dest": destination, "date": date, "price": 450, "airline": "DemoAir"},
        {"id": "FL002", "origin": origin, "dest": destination, "date": date, "price": 520, "airline": "MockAir"},
    ])
    return f"Found 2 flights: {origin}->{destination} on {date}. FL001: $450 (DemoAir), FL002: $520 (MockAir). Use book_flight for booking."


@mcp.tool()
def book_flight(flight_id: str, passenger_name: str, passenger_email: str) -> str:
    """Book a flight from search results. Provide flight_id, passenger name and email."""
    if _flights and any(f["id"] == flight_id for f in _flights):
        return f"Booking confirmed: {flight_id} for {passenger_name} ({passenger_email}). Confirmation: DEMO-{flight_id}-123."
    return f"Flight {flight_id} not found. Run search_flights first."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
