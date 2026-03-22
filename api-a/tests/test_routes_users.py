"""
Tests for api-a route handlers (Task 2.4).

Strategy:
- Use FastAPI TestClient (no live server needed).
- Override auth dependencies via app.dependency_overrides to inject
  controlled claims without touching real JWT/JWKS logic.
- Reset mock_db._users before each test so state doesn't leak.
"""
import sys
import os
import copy
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("OKTA_JWKS_URI", "https://example.okta.com/oauth2/v1/keys")
os.environ.setdefault("OKTA_AUDIENCE", "api://okta-lab")
os.environ.setdefault("OKTA_ISSUER", "https://example.okta.com/oauth2/default")

from fastapi.testclient import TestClient
from app.main import app
from app.auth import require_scope, verify_token
import app.db.mock_db as mock_db

_SEED = [
    {"email": "alice@example.com", "name": "Alice Liddell", "department": "Engineering", "employee_number": "EMP001"},
    {"email": "admin@example.com", "name": "Admin User", "department": "IT", "employee_number": "EMP002"},
    {"email": "bob@example.com", "name": "Bob Smith", "department": "Sales", "employee_number": "EMP003"},
]

client = TestClient(app, raise_server_exceptions=False)


def _reset_db():
    mock_db._users.clear()
    mock_db._users.extend(copy.deepcopy(_SEED))


def _override_auth(sub: str, scopes: list[str], groups: list[str] | None = None):
    """Install dependency overrides that return controllable claims."""
    claims = {"sub": sub, "scp": scopes, "groups": groups or []}

    def _fake_verify():
        return claims

    def _fake_require(required_scope: str):
        def _inner():
            if required_scope not in scopes:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=403,
                    detail={"error": "insufficient_scope", "message": f"Required scope: {required_scope}"},
                )
            return claims
        return _inner

    app.dependency_overrides[verify_token] = _fake_verify
    # Override every require_scope variant used by routes
    for scope in ["api-a:read", "api-a:write"]:
        app.dependency_overrides[require_scope(scope)] = _fake_require(scope)


def _clear_overrides():
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
class TestHealth(unittest.TestCase):
    def test_health_returns_200_no_auth(self):
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})


# ---------------------------------------------------------------------------
# GET /api/users
# ---------------------------------------------------------------------------
class TestGetAllUsers(unittest.TestCase):
    def setUp(self):
        _reset_db()
        _override_auth("alice@example.com", ["api-a:read"])

    def tearDown(self):
        _clear_overrides()

    def test_returns_all_users(self):
        resp = client.get("/api/users", headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 3)

    def test_missing_token_returns_401(self):
        _clear_overrides()
        resp = client.get("/api/users")
        self.assertEqual(resp.status_code, 401)

    def test_insufficient_scope_returns_403(self):
        _override_auth("alice@example.com", ["api-b:read"])
        resp = client.get("/api/users", headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"]["error"], "insufficient_scope")


# ---------------------------------------------------------------------------
# GET /api/users/{user_email}
# ---------------------------------------------------------------------------
class TestGetUser(unittest.TestCase):
    def setUp(self):
        _reset_db()

    def tearDown(self):
        _clear_overrides()

    def test_user_can_get_own_record(self):
        _override_auth("alice@example.com", ["api-a:read"])
        resp = client.get("/api/users/alice@example.com", headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["email"], "alice@example.com")

    def test_user_cannot_get_another_users_record(self):
        _override_auth("alice@example.com", ["api-a:read"])
        resp = client.get("/api/users/bob@example.com", headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_get_any_record(self):
        _override_auth("admin@example.com", ["api-a:read"], groups=["api-b-admins"])
        resp = client.get("/api/users/alice@example.com", headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["email"], "alice@example.com")

    def test_not_found_returns_404(self):
        _override_auth("nobody@example.com", ["api-a:read"], groups=["api-b-admins"])
        resp = client.get("/api/users/nobody@example.com", headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 404)

    def test_non_admin_own_email_not_in_db_returns_404(self):
        # Ownership check passes (sub == path), but record absent from DB
        _override_auth("ghost@example.com", ["api-a:read"])
        resp = client.get("/api/users/ghost@example.com", headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 404)

    def test_ownership_violation_403_has_structured_body(self):
        _override_auth("alice@example.com", ["api-a:read"])
        resp = client.get("/api/users/bob@example.com", headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 403)
        body = resp.json()["detail"]
        self.assertEqual(body["error"], "insufficient_scope")
        self.assertIn("message", body)

    def test_missing_token_returns_401(self):
        resp = client.get("/api/users/alice@example.com")
        self.assertEqual(resp.status_code, 401)

    def test_insufficient_scope_returns_403(self):
        _override_auth("alice@example.com", ["api-b:read"])
        resp = client.get("/api/users/alice@example.com", headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# POST /api/users
# ---------------------------------------------------------------------------
class TestCreateUser(unittest.TestCase):
    def setUp(self):
        _reset_db()
        _override_auth("admin@example.com", ["api-a:write"])

    def tearDown(self):
        _clear_overrides()

    def test_create_new_user_returns_201(self):
        new_user = {"email": "charlie@example.com", "name": "Charlie Brown", "department": "Finance", "employee_number": "EMP004"}
        resp = client.post("/api/users", json=new_user, headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["email"], "charlie@example.com")

    def test_duplicate_email_returns_409(self):
        resp = client.post("/api/users", json={"email": "alice@example.com", "name": "Dup"}, headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"]["error"], "conflict")

    def test_missing_token_returns_401(self):
        _clear_overrides()
        resp = client.post("/api/users", json={"email": "x@x.com"})
        self.assertEqual(resp.status_code, 401)

    def test_insufficient_scope_returns_403(self):
        _override_auth("alice@example.com", ["api-a:read"])
        resp = client.post("/api/users", json={"email": "y@y.com"}, headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 403)

    def test_missing_email_key_triggers_global_handler_500(self):
        # No "email" key → KeyError in mock_db → global handler → 500 + safe JSON (INV-21)
        resp = client.post("/api/users", json={"name": "No Email"}, headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 500)
        body = resp.json()
        self.assertEqual(body["error"], "internal_error")
        self.assertNotIn("Traceback", str(body))


# ---------------------------------------------------------------------------
# PUT /api/users/{user_email}
# ---------------------------------------------------------------------------
class TestUpdateUser(unittest.TestCase):
    def setUp(self):
        _reset_db()
        _override_auth("admin@example.com", ["api-a:write"])

    def tearDown(self):
        _clear_overrides()

    def test_update_existing_user(self):
        resp = client.put("/api/users/alice@example.com", json={"department": "Platform"}, headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["department"], "Platform")

    def test_update_nonexistent_user_returns_404(self):
        resp = client.put("/api/users/ghost@example.com", json={"department": "X"}, headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"]["error"], "not_found")

    def test_email_key_in_body_is_ignored(self):
        resp = client.put("/api/users/alice@example.com", json={"email": "hacked@example.com", "department": "Platform"}, headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 200)
        # email should remain unchanged
        self.assertEqual(resp.json()["email"], "alice@example.com")

    def test_put_with_only_email_key_is_noop(self):
        # safe_updates = {} after stripping email → user.update({}) → record unchanged
        resp = client.put("/api/users/alice@example.com", json={"email": "hacked@example.com"}, headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["department"], "Engineering")

    def test_missing_token_returns_401(self):
        _clear_overrides()
        resp = client.put("/api/users/alice@example.com", json={"department": "X"})
        self.assertEqual(resp.status_code, 401)

    def test_insufficient_scope_returns_403(self):
        _override_auth("alice@example.com", ["api-a:read"])
        resp = client.put("/api/users/alice@example.com", json={"department": "X"}, headers={"Authorization": "Bearer fake"})
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
class TestCors(unittest.TestCase):
    def test_options_preflight_from_allowed_origin_returns_200(self):
        resp = client.options(
            "/api/users",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(resp.status_code, 200)

    def test_cors_header_present_for_allowed_origin(self):
        _override_auth("alice@example.com", ["api-a:read"])
        resp = client.get("/api/users", headers={"Authorization": "Bearer fake", "Origin": "http://localhost:3000"})
        _clear_overrides()
        self.assertIn("access-control-allow-origin", resp.headers)
        self.assertEqual(resp.headers["access-control-allow-origin"], "http://localhost:3000")

    def test_cors_header_absent_for_disallowed_origin(self):
        _override_auth("alice@example.com", ["api-a:read"])
        resp = client.get("/api/users", headers={"Authorization": "Bearer fake", "Origin": "http://evil.com"})
        _clear_overrides()
        # Server must not echo back a disallowed origin as ACAO
        acao = resp.headers.get("access-control-allow-origin", "")
        self.assertNotEqual(acao, "http://evil.com")


if __name__ == "__main__":
    unittest.main(verbosity=2)
