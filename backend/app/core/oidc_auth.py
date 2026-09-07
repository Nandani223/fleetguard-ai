"""
Verifies Microsoft ID tokens (from MSAL on the frontend) for SSO login.

Adapted from the Meridian ESOP portal's oidc_auth.py — same verification
mechanics (JWKS signature check, audience/issuer validation), reused
as-is since token verification is provider logic, not app-specific.

Requires in .env:
  AZURE_TENANT_ID - your Azure AD tenant ID (a GUID)
  AZURE_CLIENT_ID - the Application (client) ID of the App Registration
"""
import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, status

from app.core.config import settings

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not settings.azure_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AZURE_TENANT_ID is not configured on the server.",
            )
        jwks_uri = f"https://login.microsoftonline.com/{settings.azure_tenant_id}/discovery/v2.0/keys"
        _jwks_client = PyJWKClient(jwks_uri)
    return _jwks_client


def verify_oidc_token(token: str) -> dict:
    """Verifies a Microsoft ID token and returns its claims (name, email, etc.)."""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Microsoft token")
    if not settings.azure_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AZURE_CLIENT_ID is not configured on the server.",
        )
    try:
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token, signing_key.key, algorithms=["RS256"],
            audience=settings.azure_client_id,
            issuer=f"https://login.microsoftonline.com/{settings.azure_tenant_id}/v2.0",
        )
        return claims
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid Microsoft token: {e}")
