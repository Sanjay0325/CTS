"""MCP WhatsApp Business - send messages via WhatsApp Cloud API."""

import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("WhatsApp Business", json_response=True, host="0.0.0.0", port=8024, stateless_http=True)

ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
API_VERSION = os.environ.get("WHATSAPP_API_VERSION", "v21.0")


def _call_whatsapp_api(to: str, body: str, preview_url: bool = False) -> dict:
    """Call WhatsApp Cloud API to send a text message."""
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        return {"error": "Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env"}
    import httpx
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to.lstrip("+").replace(" ", "").replace("-", ""),
        "type": "text",
        "text": {"body": body, "preview_url": preview_url},
    }
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=15.0)
        data = resp.json()
        if resp.status_code == 200 and "messages" in data:
            return {"success": True, "message_id": data["messages"][0]["id"]}
        return {"error": data.get("error", {}).get("message", resp.text)}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def send_whatsapp_message(to: str, message: str) -> str:
    """Send a WhatsApp text message to a phone number. Use when user asks to send WhatsApp message, text someone on WhatsApp.
    Provide 'to' as phone number with country code (e.g. 919876543210) and 'message' as the text to send."""
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        return "[Config] Add WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID to .env. Get from Meta Developer Console > WhatsApp > API Setup."
    result = _call_whatsapp_api(to, message)
    if result.get("success"):
        return f"Message sent to {to}. Message ID: {result.get('message_id', '')}"
    return f"Failed: {result.get('error', 'Unknown error')}"


@mcp.tool()
def send_whatsapp_template(to: str, template_name: str, language_code: str = "en", components: str = "{}") -> str:
    """Send a pre-approved WhatsApp template message. Use for notifications, reminders.
    Provide to (phone with country code), template_name (e.g. hello_world), language_code, and optional components as JSON string."""
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        return "[Config] Add WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID to .env."
    import json
    import httpx
    try:
        comp = json.loads(components) if components else []
    except json.JSONDecodeError:
        comp = []
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to.lstrip("+").replace(" ", "").replace("-", ""),
        "type": "template",
        "template": {"name": template_name, "language": {"code": language_code}, "components": comp},
    }
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=15.0)
        data = resp.json()
        if resp.status_code == 200 and "messages" in data:
            return f"Template sent to {to}."
        return f"Failed: {data.get('error', {}).get('message', resp.text)}"
    except Exception as e:
        return f"Failed: {e}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
