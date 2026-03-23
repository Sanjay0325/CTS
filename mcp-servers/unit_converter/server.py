"""MCP Unit Converter - convert between units."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Unit Converter", json_response=True, host="0.0.0.0", port=8008, stateless_http=True)


@mcp.tool()
def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """Convert between units. Examples: from_unit='km', to_unit='miles'; from_unit='celsius', to_unit='fahrenheit'."""
    from_unit = from_unit.lower().strip()
    to_unit = to_unit.lower().strip()

    # Length
    if from_unit in ("km", "kilometer") and to_unit in ("miles", "mi"):
        return f"{value} km = {value * 0.621371:.4f} miles"
    if from_unit in ("miles", "mi") and to_unit in ("km", "kilometer"):
        return f"{value} miles = {value * 1.60934:.4f} km"
    if from_unit == "m" and to_unit == "ft":
        return f"{value} m = {value * 3.28084:.4f} ft"

    # Temperature
    if from_unit in ("celsius", "c") and to_unit in ("fahrenheit", "f"):
        return f"{value}°C = {value * 9/5 + 32:.2f}°F"
    if from_unit in ("fahrenheit", "f") and to_unit in ("celsius", "c"):
        return f"{value}°F = {(value - 32) * 5/9:.2f}°C"

    # Weight
    if from_unit in ("kg", "kilogram") and to_unit in ("lb", "pounds"):
        return f"{value} kg = {value * 2.20462:.4f} lb"
    if from_unit in ("lb", "pounds") and to_unit in ("kg", "kilogram"):
        return f"{value} lb = {value / 2.20462:.4f} kg"

    return f"Unknown conversion: {from_unit} -> {to_unit}. Try km/miles, celsius/fahrenheit, kg/lb."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
