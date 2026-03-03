"""Optional JWT / Entra ID (Azure AD) authentication.

When AUTH_ENABLED=false (default for local dev) all /items endpoints are
open.  When AUTH_ENABLED=true every request to protected routes must carry a
valid Bearer token issued by the configured Entra ID tenant.

Token validation steps:
  1. Fetch JWKS from {issuer}/.well-known/openid-configuration (cached).
  2. Decode and verify the RS256 JWT (signature, exp, iss, aud).
  3. Return the decoded payload; downstream code may inspect claims.
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_bearer = HTTPBearer(auto_error=False)

# Simple in-memory JWKS cache (no TTL; acceptable for a starter – rotate by redeploying)
_jwks_cache: dict[str, Any] = {}


async def _fetch_jwks(issuer: str) -> dict[str, Any]:
    if issuer in _jwks_cache:
        return _jwks_cache[issuer]

    oidc_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    async with httpx.AsyncClient() as client:
        oidc_resp = await client.get(oidc_url, timeout=10)
        oidc_resp.raise_for_status()
        jwks_uri: str = oidc_resp.json()["jwks_uri"]

        jwks_resp = await client.get(jwks_uri, timeout=10)
        jwks_resp.raise_for_status()
        data: dict[str, Any] = jwks_resp.json()

    _jwks_cache[issuer] = data
    return data


async def _get_signing_key(token: str, issuer: str) -> Any:  # noqa: ANN401
    """Return the RSA public key that signed this token."""
    header = jwt.get_unverified_header(token)
    kid: str = header.get("kid", "")
    jwks = await _fetch_jwks(issuer)

    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            return jwk.construct(key_data)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to find matching JWK for token kid",
    )


async def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any] | None:
    """FastAPI dependency: validates Bearer JWT when AUTH_ENABLED=true.

    Returns the decoded token payload dict, or None when auth is disabled.
    """
    if not settings.auth_enabled:
        return None

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        signing_key = await _get_signing_key(token, settings.entra_issuer)
        payload: dict[str, Any] = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.entra_audience,
            issuer=settings.entra_issuer,
            options={"verify_at_hash": False},
        )
        return payload
    except JWTError as exc:
        logger.warning("auth.jwt_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
