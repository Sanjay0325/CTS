"""MCP Email - send emails. Demo mode by default; set SMTP env vars for real sending."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Email", json_response=True, host="0.0.0.0", port=8014, stateless_http=True)

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER or "noreply@example.com")


def _send_smtp(to: str, subject: str, body: str) -> tuple[bool, str]:
    """Send via SMTP. Returns (success, message)."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        return False, "SMTP not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASS in env."
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_FROM
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True, "Email sent."
    except Exception as e:
        return False, str(e)


@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email. Provide to address, subject, and body. Use when user says: email this to X, send an email, mail to someone.
    Set SMTP_HOST, SMTP_USER, SMTP_PASS in env for real sending. Otherwise returns demo message."""
    if SMTP_HOST and SMTP_USER and SMTP_PASS:
        ok, msg = _send_smtp(to, subject, body)
        return msg if ok else f"Failed: {msg}"
    return f"[Demo] Email would be sent to {to}, subject: {subject}. Set SMTP_HOST, SMTP_USER, SMTP_PASS for real sending."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
