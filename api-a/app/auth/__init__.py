import json
import logging
import os
from datetime import datetime, timezone

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


# --- Structured auth decision logger (INV-23) ---

class _AuthJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return record.getMessage()


_auth_handler = logging.StreamHandler()
_auth_handler.setFormatter(_AuthJsonFormatter())

_auth_logger = logging.getLogger(f"{__name__}.decisions")
_auth_logger.addHandler(_auth_handler)
_auth_logger.setLevel(logging.INFO)
_auth_logger.propagate = False


def _log_auth_decision(subject: str, route: str, required_scope: str, outcome: str) -> None:
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subject": subject,
        "route": route,
        "required_scope": required_scope,
        "outcome": outcome,
    }
    _auth_logger.info(json.dumps(log_entry))


# --- JWT validation dependency ---

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


# --- Scope-checking dependency factory (INV-12) ---

def require_scope(required_scope: str):
    def check_scope(claims: dict = Depends(verify_token)) -> dict:
        token_scopes = claims.get("scp", [])
        if isinstance(token_scopes, str):
            token_scopes = token_scopes.split()
        if required_scope not in token_scopes:
            _log_auth_decision(claims.get("sub", "anonymous"), "scope_check", required_scope, "fail")
            raise HTTPException(
                status_code=403,
                detail={"error": "insufficient_scope", "message": f"Required scope: {required_scope}"},
            )
        _log_auth_decision(claims.get("sub", "anonymous"), "scope_check", required_scope, "pass")
        return claims
    return check_scope
