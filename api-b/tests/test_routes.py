"""Tests for api-b route handlers — Task 3.3"""
import os

os.environ.setdefault("OKTA_JWKS_URI", "https://test.example.com/oauth2/v1/keys")
os.environ.setdefault("OKTA_AUDIENCE", "api://test")
os.environ.setdefault("OKTA_ISSUER", "https://test.example.com/oauth2/default")

from fastapi.testclient import TestClient

from app.auth import require_group, require_scope, verify_token
from app.db import mock_db
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _reset():
    mock_db._config.clear()
    mock_db._config.update({
        "maintenance_mode": False,
        "log_level": "INFO",
        "feature_flags": {"dark_mode": True, "beta_features": False},
    })
    mock_db._audit_log.clear()


def _override(sub: str, scopes: list[str], groups: list[str] | None = None):
    claims = {"sub": sub, "scp": scopes, "groups": groups or []}

    def _fake_verify():
        return claims

    def _fake_scope(scope: str):
        def _inner(request):
            if scope not in scopes:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=403,
                    detail={"error": "insufficient_scope", "message": f"Required scope: {scope}"},
                )
            return claims
        return _inner

    def _fake_group(group: str):
        def _inner(request):
            if group not in (groups or []):
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=403,
                    detail={"error": "insufficient_privileges", "message": f"Required group: {group}"},
                )
            return claims
        return _inner

    app.dependency_overrides[verify_token] = _fake_verify
    for scope in ["api-b:read", "api-b:admin"]:
        app.dependency_overrides[require_scope(scope)] = _fake_scope(scope)
    app.dependency_overrides[require_group("api-b-admins")] = _fake_group("api-b-admins")


def _clear():
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# TC-1  GET /health — no token required
# ---------------------------------------------------------------------------

def test_health_no_auth():
    _clear()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_no_token_still_200():
    _clear()
    resp = client.get("/health")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TC-2  GET /api/analytics/summary — no token → 401
# ---------------------------------------------------------------------------

def test_analytics_no_token_returns_401():
    _clear()
    resp = client.get("/api/analytics/summary")
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"] == "invalid_token"


# ---------------------------------------------------------------------------
# TC-3  GET /api/analytics/summary — api-b:read scope → 200 with analytics data
# ---------------------------------------------------------------------------

def test_analytics_with_read_scope_returns_200():
    _override("alice@example.com", ["api-b:read"])
    resp = client.get("/api/analytics/summary")
    _clear()
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_users"] == 42
    assert body["active_sessions"] == 7
    assert "last_updated" in body


# ---------------------------------------------------------------------------
# TC-4  GET /api/config — api-b:admin scope, NOT in api-b-admins group → 403 insufficient_privileges
# ---------------------------------------------------------------------------

def test_config_get_admin_scope_no_group_returns_403():
    _override("alice@example.com", ["api-b:admin"], [])
    resp = client.get("/api/config")
    _clear()
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "insufficient_privileges"


# ---------------------------------------------------------------------------
# TC-5  GET /api/config — in api-b-admins group, missing api-b:admin scope → 403 insufficient_scope
# ---------------------------------------------------------------------------

def test_config_get_group_no_scope_returns_403_insufficient_scope():
    _override("alice@example.com", [], ["api-b-admins"])
    resp = client.get("/api/config")
    _clear()
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "insufficient_scope"


# ---------------------------------------------------------------------------
# TC-6  GET /api/config — admin token (scope + group) → 200 with config
# ---------------------------------------------------------------------------

def test_config_get_admin_token_returns_200():
    _reset()
    _override("admin@example.com", ["api-b:admin"], ["api-b-admins"])
    resp = client.get("/api/config")
    _clear()
    assert resp.status_code == 200
    body = resp.json()
    assert body["maintenance_mode"] is False
    assert body["log_level"] == "INFO"


# ---------------------------------------------------------------------------
# TC-7  GET /api/audit-log — admin token → 200
# ---------------------------------------------------------------------------

def test_audit_log_admin_token_returns_200():
    _reset()
    _override("admin@example.com", ["api-b:admin"], ["api-b-admins"])
    resp = client.get("/api/audit-log")
    _clear()
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# TC-8  POST /api/config — admin token, valid body → 200 with updated config
# ---------------------------------------------------------------------------

def test_config_post_updates_and_returns_new_config():
    _reset()
    _override("admin@example.com", ["api-b:admin"], ["api-b-admins"])
    resp = client.post("/api/config", json={"log_level": "DEBUG"})
    _clear()
    assert resp.status_code == 200
    assert resp.json()["log_level"] == "DEBUG"
    assert resp.json()["maintenance_mode"] is False  # unrelated key unchanged


# ---------------------------------------------------------------------------
# TC-9  Audit log grows after multiple protected route requests
# ---------------------------------------------------------------------------

def test_audit_log_grows_after_multiple_requests():
    _reset()
    # Use real middleware (only override verify_token) so require_scope writes audit entries
    claims = {"sub": "alice@example.com", "scp": ["api-b:read"], "groups": []}
    app.dependency_overrides[verify_token] = lambda: claims

    client.get("/api/analytics/summary")
    client.get("/api/analytics/summary")
    client.get("/api/analytics/summary")

    _clear()
    assert len(mock_db.get_audit_log()) == 3


# ---------------------------------------------------------------------------
# TC-10  POST /api/config — no token → 401
# ---------------------------------------------------------------------------

def test_config_post_no_token_returns_401():
    _clear()
    resp = client.post("/api/config", json={"log_level": "DEBUG"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# TC-11  GET /api/audit-log — no token → 401
# ---------------------------------------------------------------------------

def test_audit_log_no_token_returns_401():
    _clear()
    resp = client.get("/api/audit-log")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# TC-12  CORS — request from allowed origin includes ACAO header
# ---------------------------------------------------------------------------

def test_cors_allowed_origin():
    _clear()
    resp = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


# ---------------------------------------------------------------------------
# TC-13  CORS — request from disallowed origin has no ACAO header
# ---------------------------------------------------------------------------

def test_cors_disallowed_origin():
    _clear()
    resp = client.get("/health", headers={"Origin": "http://evil.com"})
    assert resp.headers.get("access-control-allow-origin") != "http://evil.com"


# ---------------------------------------------------------------------------
# TC-14  Global exception handler — unhandled exception → 500 structured JSON
# ---------------------------------------------------------------------------

def test_global_exception_handler_returns_500():
    _clear()

    def _boom():
        raise RuntimeError("unexpected")

    app.dependency_overrides[verify_token] = _boom
    # analytics route depends on verify_token via require_scope
    claims = {"sub": "x", "scp": ["api-b:read"], "groups": []}
    # override require_scope to use _boom as verify_token stand-in
    from app.auth import require_scope as _rs
    original_rs = app.dependency_overrides.copy()
    app.dependency_overrides.clear()

    # Inject a route-level dep that raises directly
    from fastapi import Depends
    saved = app.dependency_overrides.copy()

    # Simplest approach: override verify_token with a raiser, no scope override
    app.dependency_overrides[verify_token] = _boom
    resp = client.get("/api/analytics/summary", headers={"Authorization": "Bearer x"})
    _clear()
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"] == "internal_error"
    assert "message" in body


# ---------------------------------------------------------------------------
# TC-16 (CC add)  POST /api/config — scope only, no group → 403 insufficient_privileges
# ---------------------------------------------------------------------------

def test_config_post_scope_no_group_returns_403():
    _override("alice@example.com", ["api-b:admin"], [])
    resp = client.post("/api/config", json={"log_level": "DEBUG"})
    _clear()
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "insufficient_privileges"


# ---------------------------------------------------------------------------
# TC-17 (CC add)  POST /api/config — group only, no scope → 403 insufficient_scope
# ---------------------------------------------------------------------------

def test_config_post_group_no_scope_returns_403_insufficient_scope():
    _override("alice@example.com", [], ["api-b-admins"])
    resp = client.post("/api/config", json={"log_level": "DEBUG"})
    _clear()
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "insufficient_scope"


# ---------------------------------------------------------------------------
# TC-18 (CC add)  POST /api/config — empty body → no-op, config unchanged
# ---------------------------------------------------------------------------

def test_config_post_empty_body_is_noop():
    _reset()
    _override("admin@example.com", ["api-b:admin"], ["api-b-admins"])
    resp = client.post("/api/config", json={})
    _clear()
    assert resp.status_code == 200
    assert resp.json()["log_level"] == "INFO"
    assert resp.json()["maintenance_mode"] is False


# ---------------------------------------------------------------------------
# TC-19 (CC add)  GET /api/analytics/summary — admin-only scope, no api-b:read → 403
# ---------------------------------------------------------------------------

def test_analytics_admin_scope_without_read_returns_403():
    _override("admin@example.com", ["api-b:admin"], ["api-b-admins"])
    resp = client.get("/api/analytics/summary")
    _clear()
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "insufficient_scope"


# ---------------------------------------------------------------------------
# TC-20 (CC add)  OPTIONS preflight on protected route → 200 (INV-20)
# ---------------------------------------------------------------------------

def test_options_preflight_returns_200():
    _clear()
    resp = client.options(
        "/api/analytics/summary",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
