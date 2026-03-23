"""Test: sign in and add Gemini profile. Run after API is up. Set EMAIL, PASSWORD, GEMINI_KEY in env."""
import asyncio
import os
import sys

# Add project root for .env
root = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, root)
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

import httpx

async def main():
    url = os.environ["SUPABASE_URL"]
    anon = os.environ["SUPABASE_ANON_KEY"]
    email = os.environ.get("TEST_EMAIL", "")
    password = os.environ.get("TEST_PASSWORD", "")
    gemini_key = os.environ.get("TEST_GEMINI_KEY", "")

    if not all([email, password, gemini_key]):
        print("Set TEST_EMAIL, TEST_PASSWORD, TEST_GEMINI_KEY to run this test")
        return 1

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{url}/auth/v1/token?grant_type=password",
            headers={"apikey": anon, "Content-Type": "application/json"},
            json={"email": email, "password": password})
        if r.status_code != 200:
            print("Sign in failed:", r.status_code, r.text[:200])
            return 1
        token = r.json().get("access_token")
        print("Signed in OK")

        r2 = await c.post("http://localhost:8000/profiles",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "display_name": "geminii",
                "provider_base_url": "https://generativelanguage.googleapis.com/v1beta",
                "api_key": gemini_key,
                "api_style": "gemini",
                "model_name": "gemini-1.5-flash",
            })
        if r2.status_code == 200:
            print("SUCCESS: Profile added")
            return 0
        print("Add profile failed:", r2.status_code, r2.text[:300])
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
