#!/usr/bin/env python3
"""
Run migration 002 and test profile creation.
Requires: psycopg2 or asyncpg, httpx, python-dotenv
"""
import asyncio
import os
import sys

# Load .env from project root
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(root)
env_path = os.path.join(root, ".env")
if os.path.exists(env_path):
    for line in open(env_path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k.strip(), v)

DATABASE_URL = os.environ.get("DATABASE_URL")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
EMAIL = os.environ.get("TEST_EMAIL", "sanjaysmpmuruga02@gmail.com")
PASSWORD = os.environ.get("TEST_PASSWORD", "12345678")
GEMINI_KEY = os.environ.get("TEST_GEMINI_KEY", "AIzaSyAM_-hsk7SBXQDiwd-BhTL0jQC035eKiMw")


async def run_migration():
    """Run migration 002 via direct SQL."""
    import asyncpg
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set")
        return False
    migration_sql = """
    ALTER TABLE public.model_profile_secrets ALTER COLUMN vault_secret_id DROP NOT NULL;
    ALTER TABLE public.model_profile_secrets ADD COLUMN IF NOT EXISTS api_key_plain TEXT;
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute(migration_sql)
        await conn.close()
        print("Migration 002 applied successfully")
        return True
    except Exception as e:
        print(f"Migration failed (may already be applied): {e}")
        return False


async def test_add_profile():
    """Test adding a Gemini profile."""
    import httpx
    if not all([SUPABASE_URL, SUPABASE_ANON_KEY]):
        print("ERROR: SUPABASE_URL and SUPABASE_ANON_KEY required")
        return False

    async with httpx.AsyncClient(timeout=30) as c:
        # 1. Sign in
        r = await c.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
            json={"email": EMAIL, "password": PASSWORD},
        )
        if r.status_code != 200:
            print(f"Sign in failed: {r.status_code} - {r.text[:200]}")
            return False
        token = r.json().get("access_token")
        print("Signed in OK")

        # 2. Add profile
        r2 = await c.post(
            "http://localhost:8000/profiles",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "display_name": "gemini",
                "provider_base_url": "https://generativelanguage.googleapis.com/v1beta",
                "api_key": GEMINI_KEY,
                "api_style": "gemini",
                "model_name": "gemini-2.0-flash",
            },
        )
        if r2.status_code == 200:
            print("SUCCESS: Profile added")
            return True
        print(f"Add profile failed: {r2.status_code}")
        try:
            err = r2.json()
            print(f"Detail: {err.get('detail', err)}")
        except Exception:
            print(f"Response: {r2.text[:500]}")
        return False


async def main():
    print("1. Running migration 002...")
    await run_migration()
    print("\n2. Testing profile creation...")
    success = await test_add_profile()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
