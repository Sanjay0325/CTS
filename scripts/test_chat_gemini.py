#!/usr/bin/env python3
"""
Test chat with Gemini - verifies api_key, model, base_url are used correctly.
Run: python scripts/test_chat_gemini.py
"""
import asyncio
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "services", "api"))

# Load .env
env_path = os.path.join(root, ".env")
if os.path.exists(env_path):
    for line in open(env_path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k.strip(), v)


async def test_gemini_direct():
    """Test Gemini API directly with correct model, base_url, api_key."""
    import httpx

    api_key = os.environ.get("TEST_GEMINI_KEY", "AIzaSyAM_-hsk7SBXQDiwd-BhTL0jQC035eKiMw")
    base_url = "https://generativelanguage.googleapis.com/v1beta"
    model = "gemini-2.0-flash"  # Use current model, not deprecated gemini-1.5-flash

    url = f"{base_url}/models/{model}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": "Say hello in 5 words."}]}],
        "generationConfig": {"temperature": 0.7},
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json=payload,
        )
        if resp.status_code != 200:
            print(f"FAIL: {resp.status_code} - {resp.text[:300]}")
            return False
        data = resp.json()
        text = ""
        for c in data.get("candidates", []):
            for p in c.get("content", {}).get("parts", []):
                text += p.get("text", "")
        print(f"OK: Gemini responded: {text[:100]}")
        return True


async def test_chat_service_alias():
    """Test that model alias maps gemini-1.5-flash -> gemini-2.0-flash."""
    from src.services.chat_service import GEMINI_MODEL_ALIASES

    assert GEMINI_MODEL_ALIASES.get("gemini-1.5-flash") == "gemini-2.0-flash"
    print("OK: Model alias configured")
    return True


if __name__ == "__main__":
    async def main():
        print("1. Testing model alias...")
        await test_chat_service_alias()
        print("\n2. Testing Gemini API (api_key, model, base_url)...")
        ok = await test_gemini_direct()
        sys.exit(0 if ok else 1)

    asyncio.run(main())
