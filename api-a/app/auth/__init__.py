import os

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.auth.jwks_cache import JWKSCache

load_dotenv()

OKTA_JWKS_URI = os.environ["OKTA_JWKS_URI"]
OKTA_AUDIENCE = os.environ["OKTA_AUDIENCE"]
OKTA_ISSUER = os.environ["OKTA_ISSUER"]

jwks_cache = JWKSCache(jwks_uri=OKTA_JWKS_URI)

security = HTTPBearer(auto_error=False)


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "message": "Authorization header missing"},
        )

    token = credentials.credentials

    # Decode header without verification to extract kid
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "message": "Token validation failed"},
        )

    kid = header.get("kid")
    if not kid:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "message": "Token validation failed"},
        )

    # Fetch key from cache; on miss invalidate and retry once (INV-09)
    key = jwks_cache.get_key(kid)
    if key is None:
        jwks_cache.invalidate_and_refetch()
        key = jwks_cache.get_key(kid)

    if key is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "message": "Signing key not found"},
        )

    # Validate JWT — leeway=60 seconds (INV-10)
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=OKTA_AUDIENCE,
            issuer=OKTA_ISSUER,
            options={"leeway": 60},
        )
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "message": "Token validation failed"},
        )

    return claims
