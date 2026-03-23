"""MCP LinkedIn - create and schedule posts via LinkedIn API (LiGo-compatible)."""

import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("LinkedIn", json_response=True, host="0.0.0.0", port=8025, stateless_http=True)

ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")


def _get_me_urn() -> str:
    """Get current user URN from LinkedIn API."""
    if not ACCESS_TOKEN:
        return ""
    import httpx
    try:
        r = httpx.get(
            "https://api.linkedin.com/v2/me",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("id", "")
    except Exception:
        pass
    return ""


@mcp.tool()
def create_linkedin_post(text: str) -> str:
    """Create and publish a LinkedIn post. Use when user asks to post on LinkedIn, share on LinkedIn, write LinkedIn post.
    Provide the full post text. Supports line breaks and hashtags."""
    if not ACCESS_TOKEN:
        return "[Config] Add LINKEDIN_ACCESS_TOKEN to .env. Get from LiGo (ligosocial.com) or LinkedIn Developer Console OAuth flow."
    import httpx
    urn = _get_me_urn()
    if not urn:
        return "Failed to get LinkedIn profile. Check access token and w_member_social scope."
    author = urn if urn.startswith("urn:") else f"urn:li:person:{urn}"
    payload = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    try:
        r = httpx.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json=payload,
            timeout=15,
        )
        if r.status_code in (200, 201):
            data = r.json()
            return f"Post published. ID: {data.get('id', '')}"
        return f"Failed: {r.status_code} - {r.text[:200]}"
    except Exception as e:
        return f"Failed: {e}"


@mcp.tool()
def draft_linkedin_post(text: str) -> str:
    """Draft a LinkedIn post without publishing. Returns the draft text for review."""
    return f"Draft saved:\n\n{text}\n\nUse create_linkedin_post when ready to publish."


@mcp.tool()
def get_linkedin_profile() -> str:
    """Get current LinkedIn profile info. Use to verify connection."""
    if not ACCESS_TOKEN:
        return "Add LINKEDIN_ACCESS_TOKEN to .env."
    import httpx
    try:
        r = httpx.get(
            "https://api.linkedin.com/v2/me",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            timeout=10,
        )
        if r.status_code == 200:
            d = r.json()
            return f"Connected as: {d.get('localizedFirstName', '')} {d.get('localizedLastName', '')}"
        return f"Failed: {r.status_code}"
    except Exception as e:
        return f"Failed: {e}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
