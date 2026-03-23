"""MCP QR Code - generate and decode QR codes (demo)."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("QR Code", json_response=True, host="0.0.0.0", port=8019, stateless_http=True)


@mcp.tool()
def generate_qr(data: str) -> str:
    """Generate QR code for text/URL. Returns base64 or file path. Add qrcode lib for production."""
    return f"[Demo] QR for '{data[:50]}...'. Add qrcode package for real generation."


@mcp.tool()
def decode_qr(image_path: str) -> str:
    """Decode QR code from image path."""
    return f"[Demo] Decode from {image_path}. Add pyzbar for real decoding."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
