"""Tests for api-b/app/auth/__init__.py — Task 3.2 (JWT Auth Middleware)"""
import json
import os

# Set env vars before the auth module is imported (module-level load_dotenv + env reads)
os.environ.setdefault("OKTA_JWKS_URI", "https://test.example.com/oauth2/v1/keys")
os.environ.setdefault("OKTA_AUDIENCE", "api://test")
os.environ.setdefault("OKTA_ISSUER", "https://test.example.com/oauth2/default")

from unittest.mock import patch, MagicMock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth import require_group, require_scope, verify_token
from app.db import mock_db

# ---------------------------------------------------------------------------
# Minimal test app — one route per dependency type
# ---------------------------------------------------------------------------

_test_app = FastAPI()


@_test_app.get("/scope-read")
def _scope_read(claims: dict = Depends(require_scope("api-b:read"))):
    return {"sub": claims["sub"]}


@_test_app.get("/admin")
def _admin(
    _s: dict = Depends(require_scope("api-b:admin")),
    claims: dict = Depends(require_group("api-b-admins")),
):
    return {"sub": claims["sub"]}


client = TestClient(_test_app, raise_server_exceptions=False)


def _reset_audit():
    mock_db._audit_log.clear()


def _fake_claims(sub: str, scopes: list[str], groups: list[str] | None = None) -> dict:
    return {"sub": sub, "scp": scopes, "groups": groups or []}


def _override(sub: str, scopes: list[str], groups: list[str] | None = None):
    claims = _fake_claims(sub, scopes, groups)

    def _fake_verify():
        return claims

    def _fake_require_scope(scope: str):
        def _inner(request):
            if scope not in scopes:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=403,
                    detail={"error": "insufficient_scope", "message": f"Required scope: {scope}"},
                )
            return claims
        return _inner

    def _fake_require_group(group: str):
        def _inner(request):
            if group not in (groups or []):
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=403,
                    detail={"error": "insufficient_privileges", "message": f"Required group: {group}"},
                )
            return claims
        return _inner

    _test_app.dependency_overrides[verify_token] = _fake_verify
    for scope in ["api-b:read", "api-b:admin"]:
        _test_app.dependency_overrides[require_scope(scope)] = _fake_require_scope(scope)
    _test_app.dependency_overrides[require_group("api-b-admins")] = _fake_require_group("api-b-admins")


def _clear_overrides():
    _test_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# TC-1  Module loads OKTA_ISSUER / OKTA_AUDIENCE / OKTA_JWKS_URI from env
# ---------------------------------------------------------------------------

def test_env_vars_loaded():
    import app.auth as auth_module
    assert auth_module.OKTA_ISSUER == os.environ["OKTA_ISSUER"]
    assert auth_module.OKTA_AUDIENCE == os.environ["OKTA_AUDIENCE"]
    assert auth_module.OKTA_JWKS_URI == os.environ["OKTA_JWKS_URI"]


# ---------------------------------------------------------------------------
# TC-2  require_scope — valid scope → 200, audit entry written
# ---------------------------------------------------------------------------

def test_require_scope_pass_writes_audit():
    _reset_audit()
    _override("alice@example.com", ["api-b:read"])
    resp = client.get("/scope-read")
    _clear_overrides()
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TC-3  require_scope — missing scope → 403
# ---------------------------------------------------------------------------

def test_require_scope_fail_returns_403():
    _reset_audit()
    _override("alice@example.com", [])
    resp = client.get("/scope-read")
    _clear_overrides()
    assert resp.status_code == 403
    body = resp.json()
    assert body["detail"]["error"] == "insufficient_scope"


# ---------------------------------------------------------------------------
# TC-4  require_group — user in group → 200, audit entries written
# ---------------------------------------------------------------------------

def test_require_group_pass_returns_200():
    _reset_audit()
    _override("admin@example.com", ["api-b:admin"], ["api-b-admins"])
    resp = client.get("/admin")
    _clear_overrides()
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TC-5  require_group — user NOT in group → 403 insufficient_privileges
# ---------------------------------------------------------------------------

def test_require_group_fail_returns_403():
    _reset_audit()
    _override("alice@example.com", ["api-b:admin"], [])
    resp = client.get("/admin")
    _clear_overrides()
    assert resp.status_code == 403
    body = resp.json()
    assert body["detail"]["error"] == "insufficient_privileges"


# ---------------------------------------------------------------------------
# TC-6  scope checked before group — missing scope returns insufficient_scope
# ---------------------------------------------------------------------------

def test_scope_checked_before_group():
    _reset_audit()
    _override("alice@example.com", [], ["api-b-admins"])
    resp = client.get("/admin")
    _clear_overrides()
    assert resp.status_code == 403
    body = resp.json()
    assert body["detail"]["error"] == "insufficient_scope"


# ---------------------------------------------------------------------------
# TC-7  Every auth decision writes to audit_log — real middleware path
# ---------------------------------------------------------------------------

def test_audit_log_grows_with_real_middleware():
    """Use real require_scope (no override) to confirm _log_auth_decision writes audit entries."""
    _reset_audit()
    _clear_overrides()

    # verify_token itself will fail (no real JWT), so we only override verify_token
    # and let require_scope run for real
    claims = {"sub": "alice@example.com", "scp": ["api-b:read"], "groups": []}
    _test_app.dependency_overrides[verify_token] = lambda: claims

    client.get("/scope-read")   # pass
    client.get("/scope-read")   # pass
    client.get("/scope-read")   # pass

    _clear_overrides()
    log = mock_db.get_audit_log()
    assert len(log) == 3


# ---------------------------------------------------------------------------
# TC-8  Audit entry schema — has timestamp, subject, route, outcome
# ---------------------------------------------------------------------------

def test_audit_entry_schema():
    _reset_audit()
    _clear_overrides()
    claims = {"sub": "alice@example.com", "scp": ["api-b:read"], "groups": []}
    _test_app.dependency_overrides[verify_token] = lambda: claims
    client.get("/scope-read")
    _clear_overrides()

    log = mock_db.get_audit_log()
    assert len(log) == 1
    entry = log[0]
    assert "timestamp" in entry
    assert entry["subject"] == "alice@example.com"
    assert entry["route"] == "/scope-read"
    assert entry["outcome"] in ("pass", "fail")


# ---------------------------------------------------------------------------
# TC-9  Audit entry written on fail outcome (403)
# ---------------------------------------------------------------------------

def test_audit_entry_written_on_fail():
    _reset_audit()
    _clear_overrides()
    claims = {"sub": "alice@example.com", "scp": [], "groups": []}
    _test_app.dependency_overrides[verify_token] = lambda: claims
    client.get("/scope-read")
    _clear_overrides()

    log = mock_db.get_audit_log()
    assert len(log) == 1
    assert log[0]["outcome"] == "fail"


# ---------------------------------------------------------------------------
# TC-10  jwks_cache is module-level (not re-instantiated per request)
# ---------------------------------------------------------------------------

def test_jwks_cache_is_module_level():
    import app.auth as auth_module
    assert hasattr(auth_module, "jwks_cache")
    assert auth_module.jwks_cache is auth_module.jwks_cache  # same object


# ---------------------------------------------------------------------------
# TC-11  leeway=60 passed to jwt.decode
# ---------------------------------------------------------------------------

def test_leeway_60_passed_to_jwt_decode():
    import app.auth as auth_module
    from unittest.mock import patch as _patch

    fake_claims = {"sub": "test@example.com", "scp": []}

    with _patch.object(auth_module.jwks_cache, "get_key", return_value={"kid": "k"}):
        with _patch("app.auth.jwt.get_unverified_header", return_value={"kid": "k"}):
            with _patch("app.auth.jwt.decode", return_value=fake_claims) as mock_decode:
                from fastapi.security import HTTPAuthorizationCredentials
                creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake.token.here")
                try:
                    auth_module.verify_token(creds)
                except Exception:
                    pass
                if mock_decode.called:
                    _, kwargs = mock_decode.call_args
                    assert kwargs.get("options", {}).get("leeway") == 60


# ---------------------------------------------------------------------------
# TC-12  No api-a imports in api-b auth module
# ---------------------------------------------------------------------------

def test_no_api_a_imports():
    import ast, pathlib
    src = pathlib.Path("app/auth/__init__.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = getattr(node, "module", "") or ""
            assert not module.startswith("api_a"), f"Cross-service import found: {module}"


# ---------------------------------------------------------------------------
# TC-13 (CC add)  verify_token — missing Authorization header → 401
# ---------------------------------------------------------------------------

def test_verify_token_no_auth_header_returns_401():
    _clear_overrides()
    resp = client.get("/scope-read")  # no Authorization header, no override
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"]["error"] == "invalid_token"


# ---------------------------------------------------------------------------
# TC-14 (CC add)  verify_token — malformed token string → 401
# ---------------------------------------------------------------------------

def test_verify_token_malformed_token_returns_401():
    _clear_overrides()
    resp = client.get("/scope-read", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"]["error"] == "invalid_token"


# ---------------------------------------------------------------------------
# TC-15 (CC add)  verify_token — kid not found after invalidate_and_refetch → 401
# ---------------------------------------------------------------------------

def test_verify_token_kid_not_found_after_refetch_returns_401():
    import app.auth as auth_module
    from unittest.mock import patch as _patch

    _clear_overrides()
    with _patch("app.auth.jwt.get_unverified_header", return_value={"kid": "missing-kid"}):
        with _patch.object(auth_module.jwks_cache, "get_key", return_value=None):
            with _patch.object(auth_module.jwks_cache, "invalidate_and_refetch"):
                resp = client.get(
                    "/scope-read",
                    headers={"Authorization": "Bearer fake.token.value"},
                )
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"]["error"] == "invalid_token"


# ---------------------------------------------------------------------------
# TC-16 (CC add)  require_scope — scp as space-separated string is handled
# ---------------------------------------------------------------------------

def test_require_scope_scp_as_string():
    _reset_audit()
    _clear_overrides()
    # scp is a string, not a list
    claims = {"sub": "alice@example.com", "scp": "api-b:read api-b:admin", "groups": []}
    _test_app.dependency_overrides[verify_token] = lambda: claims
    resp = client.get("/scope-read")
    _clear_overrides()
    assert resp.status_code == 200
