"""MCP Weather server - mock weather data for demo."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Weather", json_response=True, host="0.0.0.0", port=8003, stateless_http=True)


@mcp.tool()
def get_weather(city: str) -> str:
    """Get current weather for a city. Params: city (required, e.g. Chennai, London).
    Use when: weather in X, temperature in X, how's the weather, climate in city."""
    return f"Weather in {city}: Sunny, 72°F (22°C). Demo data. Add OpenWeatherMap API for real data."


@mcp.tool()
def get_forecast(city: str, days: int = 3) -> str:
    """Get weather forecast for a city. Params: city (required), days (optional, default 3).
    Use when: forecast, next few days weather."""
    return f"{days}-day forecast for {city}: Mostly sunny. Demo data."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
