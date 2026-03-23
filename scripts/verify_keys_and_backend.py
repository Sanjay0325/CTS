#!/usr/bin/env python3
"""
Verify API keys, Supabase, and backend.
Run: python scripts/verify_keys_and_backend.py
Reads keys from .env (OPENAI_API_KEY, GEMINI_API_KEY or TEST_GEMINI_KEY, etc.)
"""
import asyncio
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(root)

# Load .env
env_path = os.path.join(root, ".env")
if os.path.exists(env_path):
    for line in open(env_path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k.strip(), v)

# Keys to test (from env - user can override via env vars)
OPENAI_KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_KEY")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or os.environ.get("TEST_GEMINI_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON = os.environ.get("SUPABASE_ANON_KEY")
SUPABASE_SERVICE = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")


async def test_openai():
    """Test OpenAI API key - minimal request."""
    if not OPENAI_KEY:
        return "SKIP", "OPENAI_API_KEY not set in .env"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
                json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 5},
            )
            if r.status_code == 200:
                return "OK", "Key valid, quota available"
            if r.status_code == 401:
                return "FAIL", "Invalid API key (401)"
            if r.status_code == 429:
                err = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                msg = err.get("error", {}).get("message", r.text[:200])
                return "QUOTA", f"Key valid but quota exceeded: {msg[:150]}"
            return "FAIL", f"{r.status_code}: {r.text[:150]}"
    except Exception as e:
        return "ERR", str(e)


async def test_gemini():
    """Test Gemini API key - minimal request."""
    if not GEMINI_KEY:
        return "SKIP", "GEMINI_API_KEY / GOOGLE_API_KEY not set in .env"
    try:
        import httpx
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                url,
                headers={"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json"},
                json={
                    "contents": [{"role": "user", "parts": [{"text": "Hi"}]}],
                    "generationConfig": {"maxOutputTokens": 5},
                },
            )
            if r.status_code == 200:
                return "OK", "Key valid, quota available"
            if r.status_code == 403:
                return "FAIL", "Invalid API key or API not enabled (403)"
            if r.status_code == 429:
                err = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                msg = err.get("error", {}).get("message", r.text[:200])
                return "QUOTA", f"Key valid but quota exceeded. Retry later. {msg[:120]}"
            return "FAIL", f"{r.status_code}: {r.text[:150]}"
    except Exception as e:
        return "ERR", str(e)


async def test_supabase():
    """Test Supabase connection."""
    if not all([SUPABASE_URL, SUPABASE_ANON]):
        return "SKIP", "SUPABASE_URL or SUPABASE_ANON_KEY not set"
    try:
        from supabase import create_client
        sb = create_client(SUPABASE_URL, SUPABASE_ANON)
        # Simple query - list tables or health
        r = sb.table("model_profiles").select("id").limit(1).execute()
        return "OK", "Supabase connected, profiles table accessible"
    except Exception as e:
        return "FAIL", str(e)[:150]


async def test_api_backend():
    """Test if CTS API is running and healthy."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get("http://localhost:8000/health")
            if r.status_code == 200:
                return "OK", "API running"
            return "FAIL", f"API returned {r.status_code}"
    except Exception as e:
        return "WARN", f"API not reachable (is it running?): {e}"




async def main():
    print("=" * 60)
    print("CTS - API Keys & Backend Verification")
    print("=" * 60)

    # Check what keys we have
    print("\n[Keys in .env]")
    print(f"  OPENAI_API_KEY: {'set' if OPENAI_KEY else 'NOT SET'} ({'***' + OPENAI_KEY[-4:] if OPENAI_KEY else ''})")
    print(f"  GEMINI_API_KEY: {'set' if GEMINI_KEY else 'NOT SET'} ({'***' + GEMINI_KEY[-4:] if GEMINI_KEY else ''})")
    print(f"  SUPABASE_URL:   {'set' if SUPABASE_URL else 'NOT SET'}")
    print(f"  SUPABASE_ANON:  {'set' if SUPABASE_ANON else 'NOT SET'}")

    print("\n[Tests]")
    for name, coro in [
        ("OpenAI", test_openai()),
        ("Gemini", test_gemini()),
        ("Supabase", test_supabase()),
        ("API Backend", test_api_backend()),
    ]:
        status, msg = await coro
        emoji = {"OK": "[OK]", "SKIP": "[--]", "QUOTA": "[!!]", "FAIL": "[X]", "ERR": "[X]", "WARN": "[!]"}.get(status, "?")
        print(f"  {emoji} {name}: {msg}")

    print("\n" + "=" * 60)
    print("QUOTA 429 FIX:")
    print("  • OpenAI: Add payment method at https://platform.openai.com/account/billing")
    print("  • Gemini: Free tier has daily/min limits. Wait or enable billing at")
    print("    https://aistudio.google.com/apikey - or create new project for fresh quota")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
