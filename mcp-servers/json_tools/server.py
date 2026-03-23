"""MCP JSON Tools - parse and validate JSON."""

import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("JSON Tools", json_response=True, host="0.0.0.0", port=8020, stateless_http=True)


@mcp.tool()
def parse_json(text: str) -> str:
    """Parse JSON string and return formatted result or error."""
    try:
        obj = json.loads(text)
        return json.dumps(obj, indent=2)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"


@mcp.tool()
def validate_json(text: str) -> str:
    """Validate if string is valid JSON."""
    try:
        json.loads(text)
        return "Valid JSON"
    except json.JSONDecodeError as e:
        return f"Invalid: {e}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
