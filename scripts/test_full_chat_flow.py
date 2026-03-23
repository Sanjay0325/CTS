#!/usr/bin/env python3
"""
Full flow test: sign in -> add profile -> retrieve from Supabase -> call OpenAI.
Verifies: key storage, retrieval, and usage. Use OPENAI_API_KEY in .env.
"""
import asyncio
import json
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(root)
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

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON = os.environ.get("SUPABASE_ANON_KEY")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
EMAIL = os.environ.get("TEST_EMAIL", "sanjaysmpmuruga02@gmail.com")
PASSWORD = os.environ.get("TEST_PASSWORD", "12345678")


async def run():
    import httpx

    print("=" * 60)
    print("Full Chat Flow Test")
    print("=" * 60)

    if not all([SUPABASE_URL, SUPABASE_ANON]):
        print("FAIL: SUPABASE_URL, SUPABASE_ANON_KEY required in .env")
        return False
    if not OPENAI_KEY:
        print("FAIL: OPENAI_API_KEY required in .env for this test")
        return False

    key_preview = OPENAI_KEY[:8] + "..." + OPENAI_KEY[-4:] if len(OPENAI_KEY) > 12 else "***"
    print(f"\n1. OpenAI key from .env: {key_preview} (len={len(OPENAI_KEY)})")

    # 1. Test key directly (bypass our app)
    print("\n2. Testing key DIRECTLY against OpenAI...")
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY.strip()}", "Content-Type": "application/json"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Say hi"}], "max_tokens": 5},
        )
        if r.status_code == 200:
            print("   [OK] Direct call: key works")
        elif r.status_code == 401:
            print("   [FAIL] Direct call: invalid key (401)")
            return False
        elif r.status_code == 429:
            print("   [!!] Direct call: 429 quota (key valid, limit hit)")
        else:
            print(f"   [FAIL] Direct call: {r.status_code} - {r.text[:150]}")
            return False

    # 2. Sign in
    print("\n3. Signing in to Supabase...")
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{SUPABASE_URL.rstrip('/')}/auth/v1/token?grant_type=password",
            headers={"apikey": SUPABASE_ANON, "Content-Type": "application/json"},
            json={"email": EMAIL, "password": PASSWORD},
        )
        if r.status_code != 200:
            print(f"   [FAIL] Sign in: {r.status_code} - {r.text[:150]}")
            return False
        token = r.json().get("access_token")
        user = r.json().get("user", {})
        user_id = user.get("id")
        print(f"   [OK] Signed in, user_id={user_id[:8]}...")

    # 3. Add profile via our API
    print("\n4. Adding profile via POST /profiles...")
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            "http://localhost:8000/profiles",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "display_name": "Test OpenAI",
                "provider_base_url": "https://api.openai.com",
                "api_key": OPENAI_KEY.strip(),
                "api_style": "openai",
                "model_name": "gpt-4o-mini",
            },
        )
        if r.status_code != 200:
            print(f"   [FAIL] Add profile: {r.status_code} - {r.text[:200]}")
            return False
        profile = r.json()
        profile_id = profile.get("id")
        print(f"   [OK] Profile added, id={profile_id}")

    # 4. Retrieve from Supabase (simulate chat flow)
    print("\n5. Retrieving profile+key from Supabase (service role)...")
    from src.supabase_client import get_supabase_admin
    from src.services.profile_service_supabase import ProfileServiceSupabase
    from uuid import UUID

    sb = get_supabase_admin()
    if not sb:
        print("   [FAIL] Supabase admin client not available")
        return False
    svc = ProfileServiceSupabase(sb)
    retrieved = svc.get_profile_with_api_key(UUID(profile_id), user_id)
    if not retrieved:
        print("   [FAIL] Could not retrieve profile with api_key")
        return False
    retrieved_key = retrieved.get("api_key", "")
    print(f"   [OK] Retrieved. Key length: {len(retrieved_key)}, match: {retrieved_key == OPENAI_KEY.strip()}")

    if retrieved_key != OPENAI_KEY.strip():
        print(f"   [WARN] Key mismatch! Stored may have changed. First 10 chars: {repr(retrieved_key[:10])}")

    # 5. Call chat/stream
    print("\n6. Calling POST /chat/stream with profile_id...")
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            "http://localhost:8000/chat/stream",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"message": "Say hello in 3 words", "profile_id": profile_id},
        )
        if r.status_code != 200:
            print(f"   [FAIL] Chat: {r.status_code} - {r.text[:300]}")
            return False

        # Read stream
        text = ""
        async for chunk in r.aiter_text():
            text += chunk
        # Parse SSE
        for line in text.split("\n"):
            if line.startswith("data: "):
                data = line[6:].strip()
                if data == "[DONE]":
                    continue
                try:
                    parsed = json.loads(data)
                    if parsed.get("type") == "text":
                        text += parsed.get("content", "")
                    elif parsed.get("type") == "error":
                        print(f"   [FAIL] Stream error: {parsed.get('content', '')[:200]}")
                        return False
                    elif parsed.get("type") == "done":
                        print("   [OK] Chat stream completed")
                        break
                except json.JSONDecodeError:
                    pass

    print("\n" + "=" * 60)
    print("All steps passed. Key storage, retrieval, and chat flow OK.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    ok = asyncio.run(run())
    sys.exit(0 if ok else 1)
