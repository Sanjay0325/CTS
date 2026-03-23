"""MCP Hotel Booking - search and book hotels (demo)."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Hotel Booking", json_response=True, host="0.0.0.0", port=8011, stateless_http=True)

_hotels: list[dict] = []


@mcp.tool()
def search_hotels(city: str, check_in: str, check_out: str, guests: int = 1) -> str:
    """Search hotels in a city. Dates: YYYY-MM-DD. Returns available hotels."""
    _hotels.clear()
    _hotels.extend([
        {"id": "HT001", "name": "Grand Plaza", "city": city, "price": 120, "rating": 4.5},
        {"id": "HT002", "name": "City Inn", "city": city, "price": 85, "rating": 4.0},
    ])
    return f"Found 2 hotels in {city}: Grand Plaza $120/night (4.5★), City Inn $85/night (4.0★). Use book_hotel to book."


@mcp.tool()
def book_hotel(hotel_id: str, guest_name: str, guest_email: str, nights: int = 1) -> str:
    """Book a hotel. Provide hotel_id from search, guest name, email, and number of nights."""
    if _hotels and any(h["id"] == hotel_id for h in _hotels):
        h = next(h for h in _hotels if h["id"] == hotel_id)
        total = h["price"] * nights
        return f"Booked {h['name']} for {guest_name} ({nights} nights). Total: ${total}. Confirmation: DEMO-{hotel_id}."
    return f"Hotel {hotel_id} not found. Run search_hotels first."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
