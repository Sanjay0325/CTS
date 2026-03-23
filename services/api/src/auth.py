"""JWT verification and authentication utilities."""

import time
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from jose.utils import base64url_decode

# JWKS cache
_jwks_cache: dict = {}
_jwks_cache_expiry: float = 0
JWKS_CACHE_TTL = 600  # 10 minutes


async def fetch_jwks() -> dict:
    """Fetch JWKS from Supabase and cache for 10 minutes."""
    global _jwks_cache, _jwks_cache_expiry
    if time.time() < _jwks_cache_expiry and _jwks_cache:
        return _jwks_cache

    from src.config import settings
    jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            _jwks_cache_expiry = time.time() + JWKS_CACHE_TTL
            return _jwks_cache
    except Exception:
        return {}


def get_signing_key(jwks: dict, kid: str) -> Optional[dict]:
    """Extract signing key from JWKS by key ID."""
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


async def verify_supabase_jwt(token: str) -> Optional[dict]:
    """
    Verify Supabase JWT. Tries in order:
    1. HS256 with SUPABASE_JWT_SECRET (Supabase default)
    2. JWKS (RS256)
    3. /auth/v1/user fallback
    """
    from src.config import settings

    if not token or len(token.split(".")) != 3:
        return None

    # 1. HS256 with JWT secret (Supabase's primary method)
    if settings.supabase_jwt_secret:
        try:
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_aud": True},
            )
            return payload
        except JWTError:
            pass

    # 2. JWKS (RS256)
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        jwks = await fetch_jwks()
        if jwks and kid:
            key = get_signing_key(jwks, kid)
            if key:
                payload = jwt.decode(
                    token,
                    key,
                    algorithms=["RS256"],
                    audience="authenticated",
                    options={"verify_aud": True},
                )
                return payload
    except JWTError:
        pass

    # 3. Fallback: verify via Supabase /auth/v1/user
    if settings.supabase_url and settings.supabase_anon_key:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "apikey": settings.supabase_anon_key,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {"sub": data.get("id")} if data.get("id") else None
        except Exception:
            pass
    return None


security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Dependency to get current authenticated user from JWT."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )
    payload = await verify_supabase_jwt(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    return {"id": user_id, "payload": payload}
