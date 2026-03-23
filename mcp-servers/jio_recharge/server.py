"""MCP Jio Recharge - search plans and recharge (demo). Wire to real API for production."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Jio Recharge", json_response=True, host="0.0.0.0", port=8023, stateless_http=True)

# Demo plans - in production, fetch from Jio/operator API
DEMO_PLANS = [
    {"id": "jio_19", "amount": 19, "validity": "1 day", "data": "100 MB", "description": "Jio ₹19 1-day plan"},
    {"id": "jio_149", "amount": 149, "validity": "28 days", "data": "2 GB", "description": "Jio ₹149 28-day plan"},
    {"id": "jio_299", "amount": 299, "validity": "28 days", "data": "2 GB/day", "description": "Jio ₹299 28-day plan"},
    {"id": "jio_399", "amount": 399, "validity": "56 days", "data": "1.5 GB/day", "description": "Jio ₹399 56-day plan"},
]


@mcp.tool()
def search_jio_plans(amount: int | None = None) -> str:
    """Search Jio prepaid plans. Pass amount (e.g. 19) to filter by price. Returns plan list with id, amount, validity, data."""
    if amount:
        filtered = [p for p in DEMO_PLANS if p["amount"] == amount]
    else:
        filtered = DEMO_PLANS
    if not filtered:
        return f"No Jio plans found for ₹{amount}. Try 19, 149, 299, or 399."
    lines = [f"- {p['id']}: ₹{p['amount']} | {p['validity']} | {p['data']} | {p['description']}" for p in filtered]
    return "Jio plans:\n" + "\n".join(lines)


@mcp.tool()
def recharge_jio(mobile: str, plan_id: str, amount: float) -> str:
    """Recharge a Jio prepaid number. Provide 10-digit mobile, plan_id (e.g. jio_19), and amount in rupees.
    In production, this would call Jio/recharge API with JIO_RECHARGE_API_KEY from env."""
    if len(mobile) != 10 or not mobile.isdigit():
        return "Error: mobile must be 10 digits."
    plan = next((p for p in DEMO_PLANS if p["id"] == plan_id), None)
    if not plan:
        return f"Error: plan_id '{plan_id}' not found. Use search_jio_plans to list plans."
    # Demo: simulate success. For real API, use: os.environ.get("JIO_RECHARGE_API_KEY")
    return f"[Demo] Recharge initiated for {mobile}: ₹{amount} ({plan['description']}). In production, wire to A1Topup/Enginify API."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
