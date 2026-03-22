# EXECUTION_PLAN.md — Okta Identity Lab

**PBVI Phase:** 3 — Execution Planning
**Status:** Draft — awaiting engineer review
**Engineer:** Naveen
**Date:** March 2026
**Derived from:** ARCHITECTURE.md (locked) + INVARIANTS.md (signed off, 28 invariants)

---

## Open Questions Confirmation

All open questions from ARCHITECTURE.md are resolved. No unresolved questions remain. Proceeding to plan generation.

---

## Resolved Decisions Table

| # | Open Question | Resolution |
|---|---|---|
| OQ-1 | M2M token scope assignment | API A explicitly requests `scope=api-b:read` in the client credentials grant POST body. The Okta policy for `okta-lab-api-a` must permit this scope. Scope is not auto-granted. (INV-17) |
| OQ-2 | Refresh token storage | Refresh tokens stored in an `httpOnly` cookie. Not accessible to JavaScript. Silent refresh reads the cookie implicitly via the browser's cookie jar on the Okta token endpoint call. (INV-03) |
| OQ-3 | JWKS cache sharing | Each service (API A, API B) maintains its own independent JWKS cache. Key rotation is tested per-service, not in a coordinated scenario. (INV-08, INV-09) |
| OQ-4 | Fine-grained auth data model | User email is the record identifier. `GET /api/users/:id` uses email as the route parameter. Fine-grained check compares `token.sub` (Okta user email) to `record.email`. `employee_number` field retained in data model for learning only — not the auth join key. (INV-14) |

---

## Requirements Traceability Check

| Requirement (Brief) | Owner in Architecture | Status |
|---|---|---|
| Auth Code + PKCE SPA flow | Decision 5 — React 18 + Vite + @okta/okta-react | ✅ Covered |
| Custom Authorization Server with scopes and claims | Decision 7 | ✅ Covered |
| API A — CRUD endpoints + JWT validation | Decision 1 (FastAPI), Decision 2 (independent service) | ✅ Covered |
| API B — Admin endpoints + group auth | Decision 1, Decision 2 | ✅ Covered |
| M2M Client Credentials flow | OQ-1 resolved | ✅ Covered |
| Token Inspector Panel | Decision 5, INV-25 | ✅ Covered |
| Token Refresh Demo Panel | INV-26 | ✅ Covered |
| API Tester Panel | INV-24, INV-27 | ✅ Covered |
| JWKS caching + key rotation | Decision 3 (manual), INV-08, INV-09 | ✅ Covered |
| CORS lockdown | INV-20 | ✅ Covered |
| Structured auth logging | INV-23 | ✅ Covered |
| Audit log (API B) | INV-15, data model | ✅ Covered |
| Silent token refresh (proactive, 60s) | INV-05, OQ-2 resolved | ✅ Covered |
| Okta System Log walkthrough | Phase 6 verification activity — not a code task; documented below | ✅ Noted |
| Event Hook (bonus) | Parking lot in ARCHITECTURE.md — explicitly deferred | ✅ Deferred |
| Mock DB shared across APIs | Consciously violated per Decision 4 — per-service in-memory dict | ✅ Documented deviation |

---

## Session Overview

| # | Session Name | Goal | Tasks | Est. Duration |
|---|---|---|---|---|
| 1 | Scaffold & Okta Setup | Repo structure, venvs, dependencies installed; all three Okta apps registered; custom AuthServer live with scopes and claims | 4 | ~3 hrs |
| 2 | API A — Core Auth | API A running with JWKS validation middleware, scope-based auth, all five endpoints, structured logging | 5 | ~3 hrs |
| 3 | API B — Admin Auth | API B running with group-based auth, fine-grained audit log write, all five endpoints | 4 | ~2.5 hrs |
| 4 | Frontend SPA | React app with PKCE login, Token Inspector, API Tester, silent refresh, Token Refresh Demo | 6 | ~4 hrs |
| 5 | M2M Flow | API A client credentials implementation, `/api/internal/pull-analytics` endpoint, end-to-end test | 3 | ~2 hrs |
| 6 | Enterprise Hardening | CORS lockdown both APIs, JWKS key rotation test, Okta System Log walkthrough | 3 | ~2 hrs |
| 7 | System Sign-Off | All Definition of Done scenarios, deliberate breakage tests, VERIFICATION_CHECKLIST.md | 1 | ~1 hr |

---

## Session 1 — Scaffold & Okta Setup

**Session goal:** The repository exists with the correct directory structure. All Python dependencies install cleanly into isolated virtual environments. All three Okta applications are registered. The custom Authorization Server is live with all five custom scopes, three custom claims, and three user groups. Two test users exist and are assigned to groups. `curl` to the JWKS endpoint returns a valid key set.

**Integration check:**
```bash
# Confirm JWKS endpoint is reachable and returns keys from the custom AuthServer
curl -s https://<OKTA_DOMAIN>/oauth2/<AUTH_SERVER_ID>/v1/keys | python3 -m json.tool | grep '"keys"'
# Confirm both API virtual environments are isolated
ls api-a/.venv/lib/ && ls api-b/.venv/lib/
# Confirm frontend node_modules exist
ls frontend/node_modules/@okta
```

---

### Task 1.1 — Repository Scaffold

**Description:** Initialise the monorepo directory structure. Create all top-level directories and placeholder files. No application code yet.

**CC prompt:**
```
Create the following directory and file structure for the Okta Identity Lab project.
Do not write any application logic — only create the structure and empty placeholder files.

Root directory: okta-identity-lab/
├── api-a/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # empty FastAPI app skeleton only
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   └── jwks_cache.py   # empty module, class stub only
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── users.py        # empty module
│   │   │   └── internal.py     # empty module
│   │   └── db/
│   │       ├── __init__.py
│   │       └── mock_db.py      # empty module
│   ├── requirements.txt     # list dependencies only, do not install
│   ├── .env.example
│   └── README.md
├── api-b/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   └── jwks_cache.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── analytics.py
│   │   │   ├── config.py
│   │   │   └── audit.py
│   │   └── db/
│   │       ├── __init__.py
│   │       └── mock_db.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
├── frontend/
│   └── (empty — Vite scaffold created in Task 1.2)
├── .gitignore           # must include: .env, .venv/, __pycache__/, node_modules/, dist/
└── README.md

For requirements.txt in both api-a/ and api-b/, include exactly:
fastapi==0.111.0
uvicorn[standard]==0.29.1
python-jose[cryptography]==3.3.0
httpx==0.27.0
python-dotenv==1.0.1

Do not run pip install. Do not create virtual environments. Do not write application logic.
Do not include any Okta credentials in any file.
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | Directory structure matches spec | All 20+ files/dirs exist at correct paths |
| TC-2 | .gitignore covers secrets | `.env` and `.venv/` appear in .gitignore |
| TC-3 | requirements.txt contains exact packages | `cat api-a/requirements.txt` shows all 5 packages |
| TC-4 | No credentials in any file | `grep -r "OKTA\|client_secret\|client_id" --include="*.py" .` returns nothing |

**Verification command:**
```bash
find okta-identity-lab -type f | sort && grep ".env" okta-identity-lab/.gitignore
```

**Invariant flag:** INV-22 (no credentials hardcoded). Code review: confirm `.env` is in `.gitignore` before any Okta values are written.

---

### Task 1.2 — Frontend Vite Scaffold

**Description:** Create the React 18 + Vite project in `frontend/`. Install Okta SDK dependencies. Confirm the dev server starts.

**CC prompt:**
```
From the okta-identity-lab/ root, scaffold a React 18 + Vite frontend project.

Run:
  npm create vite@latest frontend -- --template react
  cd frontend && npm install
  npm install @okta/okta-auth-js @okta/okta-react react-router-dom

After installing, create frontend/.env.example with these keys (empty values):
  VITE_OKTA_DOMAIN=
  VITE_OKTA_CLIENT_ID=
  VITE_OKTA_ISSUER=
  VITE_OKTA_REDIRECT_URI=

Create frontend/.gitignore (if not already present) that includes .env and dist/.

Do not create any React components beyond what Vite generates.
Do not connect to Okta yet.
Do not add any Okta configuration values.
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | Dev server starts | `npm run dev` in frontend/ starts without errors |
| TC-2 | Okta packages installed | `ls frontend/node_modules/@okta` shows both packages |
| TC-3 | .env.example present | File exists with all 4 keys |

**Verification command:**
```bash
cd okta-identity-lab/frontend && npm run dev -- --port 3000 &
sleep 3 && curl -s http://localhost:3000 | grep -i "vite\|react" && kill %1
```

**Invariant flag:** INV-22. No Okta credentials written yet.

---

### Task 1.3 — Python Virtual Environments

**Description:** Create and activate virtual environments for API A and API B. Install all dependencies. Confirm both `uvicorn` and `jose` are importable.

**CC prompt:**
```
From the okta-identity-lab/ root, set up isolated Python virtual environments for both APIs.

For api-a/:
  python3 -m venv api-a/.venv
  source api-a/.venv/bin/activate
  pip install -r api-a/requirements.txt
  deactivate

For api-b/:
  python3 -m venv api-b/.venv
  source api-b/.venv/bin/activate
  pip install -r api-b/requirements.txt
  deactivate

Do not modify any .py files. Do not start any servers.
Do not install anything beyond what is in requirements.txt.
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | api-a venv imports cleanly | `api-a/.venv/bin/python -c "from jose import jwt; import httpx; import fastapi"` exits 0 |
| TC-2 | api-b venv imports cleanly | Same check for api-b venv |
| TC-3 | Venvs are isolated | `which python` from root does not point into either .venv |

**Verification command:**
```bash
okta-identity-lab/api-a/.venv/bin/python -c "from jose import jwt; import httpx; import fastapi; print('api-a OK')"
okta-identity-lab/api-b/.venv/bin/python -c "from jose import jwt; import httpx; import fastapi; print('api-b OK')"
```

**Invariant flag:** None. Dependency task only.

---

### Task 1.4 — Okta Configuration (Manual — Engineer-Executed)

**Description:** This task is executed by the engineer in the Okta admin console. Claude Code is not involved. It produces the `.env` values consumed by all subsequent tasks.

> **Note:** This is a human-executed task. There is no CC prompt. The engineer completes the Okta setup and records the output values in `.env` files before Session 2 begins.

**Steps the engineer executes:**

1. Create Okta Developer account at developer.okta.com (if not already done)
2. Register three applications:
   - `okta-lab-spa`: OIDC SPA, Auth Code + PKCE, redirect URIs: `http://localhost:3000`, `http://localhost:3000/login/callback`
   - `okta-lab-api-a`: OIDC Web App (for M2M), Client Credentials grant enabled
   - `okta-lab-api-b`: OIDC Web App (M2M recipient), Client Credentials grant enabled
3. Create custom Authorization Server named `okta-lab-authserver`, audience `api://okta-lab`, access token lifetime 1 hour
4. Define custom scopes: `api-a:read`, `api-a:write`, `api-b:read`, `api-b:admin`, `offline_access`
5. Add custom claims to Access Token:
   - `groups`: `getFilteredGroups(groupAllowList, "group.name", 10)` — include groups in Access Token
   - `department`: `user.department`
   - `employee_id`: `user.employeeNumber`
6. Create groups: `api-a-users`, `api-b-viewers`, `api-b-admins`
7. Create authorization server policy and rules granting scopes to groups
8. Create two test users: `alice@example.com` (assigned to `api-a-users`, `api-b-viewers`) and `admin@example.com` (assigned to all three groups including `api-b-admins`)
9. Set `department` and `employeeNumber` profile attributes on both users
10. Populate `.env` files in `api-a/`, `api-b/`, and `frontend/` with real values

**Values to populate:**
```
# api-a/.env
OKTA_DOMAIN=https://dev-XXXXXXX.okta.com
OKTA_ISSUER=https://dev-XXXXXXX.okta.com/oauth2/<AUTH_SERVER_ID>
OKTA_JWKS_URI=https://dev-XXXXXXX.okta.com/oauth2/<AUTH_SERVER_ID>/v1/keys
OKTA_AUDIENCE=api://okta-lab
OKTA_CLIENT_ID=<okta-lab-api-a client ID>
OKTA_CLIENT_SECRET=<okta-lab-api-a client secret>
OKTA_TOKEN_ENDPOINT=https://dev-XXXXXXX.okta.com/oauth2/<AUTH_SERVER_ID>/v1/token

# api-b/.env
OKTA_DOMAIN=https://dev-XXXXXXX.okta.com
OKTA_ISSUER=https://dev-XXXXXXX.okta.com/oauth2/<AUTH_SERVER_ID>
OKTA_JWKS_URI=https://dev-XXXXXXX.okta.com/oauth2/<AUTH_SERVER_ID>/v1/keys
OKTA_AUDIENCE=api://okta-lab

# frontend/.env
VITE_OKTA_DOMAIN=https://dev-XXXXXXX.okta.com
VITE_OKTA_CLIENT_ID=<okta-lab-spa client ID>
VITE_OKTA_ISSUER=https://dev-XXXXXXX.okta.com/oauth2/<AUTH_SERVER_ID>
VITE_OKTA_REDIRECT_URI=http://localhost:3000/login/callback
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | JWKS endpoint accessible | `curl https://<OKTA_DOMAIN>/oauth2/<AUTH_SERVER_ID>/v1/keys` returns JSON with `keys` array |
| TC-2 | SPA app redirect URIs match | Okta app settings show both localhost:3000 URIs |
| TC-3 | Both test users exist | Admin console shows alice and admin users with group assignments |
| TC-4 | .env files not committed | `git status` shows .env files as untracked (in .gitignore) |

**Verification command:**
```bash
# Engineer runs this after completing Okta setup
source api-a/.env 2>/dev/null || (set -a && . api-a/.env && set +a)
curl -s $OKTA_JWKS_URI | python3 -m json.tool | grep '"kid"'
```

**Invariant flag:** INV-22 (env vars, never hardcoded). INV-19 (client secret in env only). Code review: confirm `.env` files do not appear in `git status` tracked files.

---

## Session 2 — API A: Core Auth

**Session goal:** API A starts on port 3001, serves all five endpoints, validates Okta JWTs offline via a JWKS cache with TTL and rotation handling, enforces scope-based auth (403 on missing scope, 401 on missing/invalid/expired token), emits structured JSON auth logs on every decision, and the health endpoint returns 200 with no auth required.

**Integration check:**
```bash
# Start API A
cd okta-identity-lab/api-a && source .venv/bin/activate && uvicorn app.main:app --port 3001 &
sleep 2

# Health check — no auth
curl -s http://localhost:3001/health | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='ok', d"

# Missing token → 401
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3001/api/users)
[ "$STATUS" = "401" ] && echo "INV-16 PASS" || echo "INV-16 FAIL: got $STATUS"

# Malformed token → 401
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer not.a.jwt" http://localhost:3001/api/users)
[ "$STATUS" = "401" ] && echo "malformed token PASS" || echo "malformed token FAIL: got $STATUS"

kill %1
```

---

### Task 2.1 — Mock Database (API A)

**Description:** Implement the in-memory Python dict database for API A. Seed three user records. Expose read/write functions used by route handlers.

**CC prompt:**
```
In api-a/app/db/mock_db.py, implement the in-memory mock database for API A.

The data store is a Python dict — not SQLite, not a file, not any external DB.

Implement:

DATA STRUCTURE:
  _users: list[dict] — module-level variable, initialised at import time

SEED DATA — exactly three records:
  {"email": "alice@example.com", "name": "Alice Liddell", "department": "Engineering", "employee_number": "EMP001"}
  {"email": "admin@example.com", "name": "Admin User", "department": "IT", "employee_number": "EMP002"}
  {"email": "bob@example.com", "name": "Bob Smith", "department": "Sales", "employee_number": "EMP003"}

FUNCTIONS to implement (exact signatures):
  def get_all_users() -> list[dict]:
      """Return all user records."""

  def get_user_by_email(email: str) -> dict | None:
      """Return the user record with matching email, or None if not found."""

  def create_user(user: dict) -> dict:
      """Append user dict to _users. Return the created record."""

  def update_user(email: str, updates: dict) -> dict | None:
      """Find user by email, apply updates, return updated record. Return None if not found."""

Do not add any auth logic. Do not import fastapi or jose. Do not read from any file or environment variable.
Do not expose _users directly — only through the four functions above.
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | get_all_users returns seed data | Returns list of 3 dicts |
| TC-2 | get_user_by_email — found | Returns matching dict |
| TC-3 | get_user_by_email — not found | Returns None |
| TC-4 | create_user appends correctly | New record retrievable via get_user_by_email |
| TC-5 | update_user — found | Updated fields reflected in subsequent get |
| TC-6 | update_user — not found | Returns None |

**Verification command:**
```bash
cd okta-identity-lab && api-a/.venv/bin/python -c "
from api_a.app.db.mock_db import get_all_users, get_user_by_email, create_user, update_user
assert len(get_all_users()) == 3
assert get_user_by_email('alice@example.com')['name'] == 'Alice Liddell'
assert get_user_by_email('nobody@x.com') is None
create_user({'email': 'new@x.com', 'name': 'New', 'department': 'X', 'employee_number': 'EMP999'})
assert get_user_by_email('new@x.com') is not None
assert update_user('new@x.com', {'department': 'Y'})['department'] == 'Y'
assert update_user('ghost@x.com', {}) is None
print('mock_db OK')
"
```

**Invariant flag:** INV-14 (fine-grained auth joins on email field). Code review: confirm `email` field name is consistent with `token.sub` comparison in route handler (Task 2.4).

---

### Task 2.2 — JWKS Cache (API A)

**Description:** Implement the JWKS cache class with TTL, `kid`-based key lookup, forced invalidation on rotation, and observable structured logging on all state transitions. This is the core manual implementation per Decision 3.

**CC prompt:**
```
In api-a/app/auth/jwks_cache.py, implement the JWKSCache class.

Read OKTA_JWKS_URI from environment (via os.environ — do not use python-dotenv here;
the calling app will have loaded .env before importing this module).

Requirements:

CLASS: JWKSCache
  __init__(self, jwks_uri: str, ttl_seconds: int = 600)
    - stores jwks_uri and ttl_seconds
    - initialises _keys: dict = {} (kid → full key dict)
    - initialises _fetched_at: float = 0.0

  def get_key(self, kid: str) -> dict | None
    - If cache is empty OR age > ttl_seconds: fetch and refresh (log: "JWKS_CACHE_MISS")
    - If kid found in cache: return key dict (log: "JWKS_CACHE_HIT")
    - If kid NOT found after fetch: return None (log: "JWKS_KID_NOT_FOUND")

  def invalidate_and_refetch(self) -> None
    - Clears _keys and _fetched_at = 0.0
    - Calls _fetch() immediately
    - Logs: "JWKS_CACHE_INVALIDATED_REFETCH"

  def _fetch(self) -> None
    - Uses httpx.get() to fetch the JWKS URI (timeout=10s)
    - Parses response JSON: { "keys": [ { "kid": "...", ... } ] }
    - Stores each key dict in _keys keyed by kid
    - Sets _fetched_at = time.time()
    - Logs: "JWKS_CACHE_REFRESHED" with key count

LOGGING: Use Python's logging module (structured JSON lines via a custom formatter).
All log lines must include: timestamp, event (the string codes above), key_count where applicable, kid where applicable.

Do not raise exceptions from get_key — return None on all failure paths.
Do not use any jwks library. Use only httpx and the standard library.
Do not add FastAPI imports.
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | Cold start — fetches on first get_key call | Log shows JWKS_CACHE_REFRESHED |
| TC-2 | Second call within TTL — cache hit | Log shows JWKS_CACHE_HIT, no HTTP request |
| TC-3 | Expired cache — re-fetches | After TTL, next get_key triggers JWKS_CACHE_MISS and re-fetch |
| TC-4 | Unknown kid after fetch — returns None | Log shows JWKS_KID_NOT_FOUND |
| TC-5 | invalidate_and_refetch — logs correctly | Log shows JWKS_CACHE_INVALIDATED_REFETCH then JWKS_CACHE_REFRESHED |

**Verification command:**
```bash
# Requires real Okta JWKS URI in environment
cd okta-identity-lab/api-a && source .env && .venv/bin/python -c "
import os, time
from app.auth.jwks_cache import JWKSCache
cache = JWKSCache(os.environ['OKTA_JWKS_URI'], ttl_seconds=2)
# Cold start — should fetch
keys = cache._fetch()
print('Keys loaded:', len(cache._keys), 'keys')
assert len(cache._keys) > 0, 'No keys fetched from Okta JWKS endpoint'
# Test invalidation
cache.invalidate_and_refetch()
assert cache._fetched_at > 0
print('JWKSCache OK')
"
```

**Invariant flag:** INV-08 (cache, no per-request fetch), INV-09 (invalidate on kid mismatch), INV-11 (observable logging). Code review: confirm `get_key` does NOT make an HTTP call on every invocation — only on cold start, TTL expiry, or explicit invalidation.

---

### Task 2.3 — JWT Auth Middleware (API A)

**Description:** Implement the FastAPI dependency that validates the JWT signature, checks expiry with 60-second leeway, and extracts claims. Returns 401 on all token failures. Does not check scopes — scope checking is a separate concern (Task 2.4).

**CC prompt:**
```
In api-a/app/auth/__init__.py, implement the JWT validation dependency for FastAPI.

This module provides:
  1. A module-level JWKSCache instance (initialised from OKTA_JWKS_URI env var)
  2. A FastAPI dependency function: verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict

verify_token must:
  1. Extract the Bearer token from the Authorization header
  2. Decode the JWT header (without verification) to extract the kid claim
  3. Call jwks_cache.get_key(kid) to retrieve the public key
  4. If kid not found: call jwks_cache.invalidate_and_refetch(), retry get_key once
  5. If key still not found after retry: raise HTTPException(status_code=401, detail={"error": "invalid_token", "message": "Signing key not found"})
  6. Validate the JWT using python-jose jwt.decode():
     - algorithms=["RS256"]
     - audience=OKTA_AUDIENCE (from env)
     - issuer=OKTA_ISSUER (from env)
     - leeway=60 (INV-10)
  7. On JWTError: raise HTTPException(status_code=401, detail={"error": "invalid_token", "message": "Token validation failed"})
  8. Return the decoded claims dict

Do NOT check scopes in this function — that is a separate dependency.
Do NOT return stack traces in HTTPException details — only safe messages (INV-21).
Use HTTPBearer() as the security scheme.
Load all env vars using python-dotenv at module level (load_dotenv()).
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | No Authorization header | 401 with structured JSON body |
| TC-2 | Malformed token (not a JWT) | 401 with structured JSON body |
| TC-3 | Expired token | 401 (exp check enforced) |
| TC-4 | Valid token from Okta | Returns claims dict with sub, scp, groups |
| TC-5 | Token signed with unknown kid | Triggers invalidate_and_refetch, then 401 if still not found |
| TC-6 | Clock skew <60s | Token accepted (leeway=60 applied) |

**Verification command:**
```bash
# Start API A with just the health route and confirm auth dependency loads
cd okta-identity-lab/api-a && source .env && .venv/bin/python -c "
from app.auth import verify_token, jwks_cache
print('JWKS URI:', jwks_cache.jwks_uri)
print('Auth module loads OK')
"
```

**Invariant flag:** INV-07, INV-09, INV-10, INV-16, INV-21. Code review: confirm `leeway=60` is present on `jwt.decode()`; confirm no stack trace in exception detail.

---

### Task 2.4 — User Route Handlers (API A)

**Description:** Implement all five API A routes. Scope-checking dependency applied per route. Fine-grained ownership check on `GET /api/users/:id`. Structured auth log on every decision. Health endpoint with no auth.

**CC prompt:**
```
In api-a/app/routes/users.py and api-a/app/main.py, implement the API A route handlers.

First, add to api-a/app/auth/__init__.py a scope-checking dependency factory:
  def require_scope(required_scope: str):
      def check_scope(claims: dict = Depends(verify_token)) -> dict:
          token_scopes = claims.get("scp", [])
          if isinstance(token_scopes, str):
              token_scopes = token_scopes.split()
          if required_scope not in token_scopes:
              _log_auth_decision(claims.get("sub", "anonymous"), "scope_check", required_scope, "fail")
              raise HTTPException(status_code=403, detail={"error": "insufficient_scope", "message": f"Required scope: {required_scope}"})
          _log_auth_decision(claims.get("sub", "anonymous"), "scope_check", required_scope, "pass")
          return claims
      return check_scope

Add _log_auth_decision(subject, route, required_scope, outcome) — emits structured JSON log line with timestamp, subject, route, required_scope, outcome fields. (INV-23)

In api-a/app/routes/users.py, implement:

  GET /health — no auth, returns {"status": "ok"}

  GET /api/users — requires api-a:read scope
    Returns: list of all users from mock_db.get_all_users()

  GET /api/users/{user_email} — requires api-a:read scope PLUS fine-grained check:
    1. Retrieve record via mock_db.get_user_by_email(user_email)
    2. If record is None: return 404 {"error": "not_found", "message": "User not found"}
    3. Check if caller is in api-b-admins group (claims["groups"] contains "api-b-admins"):
       if yes: return record (bypass ownership check)
    4. If token.sub != record["email"]: raise 403 {"error": "forbidden", "message": "Access to this record is not permitted"}
    5. Return record

  POST /api/users — requires api-a:write scope
    Body: {"email": str, "name": str, "department": str, "employee_number": str}
    Calls mock_db.create_user(body). Returns 201 with created record.

  PUT /api/users/{user_email} — requires api-a:write scope
    Body: partial update dict (any subset of fields except email)
    Calls mock_db.update_user(user_email, body). If None: 404. Else: 200 with updated record.

In api-a/app/main.py:
  - Create FastAPI app instance
  - Add CORS middleware: allow_origins=["http://localhost:3000"], allow_headers=["Authorization","Content-Type"], allow_methods=["*"] (INV-20)
  - Add global exception handler that catches all unhandled exceptions and returns {"error": "internal_error", "message": "An unexpected error occurred"} — no stack traces (INV-21)
  - Include router from users.py

Do not include any Okta credentials in source files. Read all config from env vars.
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | GET /health — no token | 200 {"status": "ok"} |
| TC-2 | GET /api/users — no token | 401 |
| TC-3 | GET /api/users — valid token, api-a:read scope | 200, list of 3 users |
| TC-4 | GET /api/users — valid token, missing api-a:read | 403 |
| TC-5 | GET /api/users/alice@example.com — alice's own token | 200, alice's record |
| TC-6 | GET /api/users/alice@example.com — bob's token (non-admin) | 403 |
| TC-7 | GET /api/users/alice@example.com — admin token | 200 (ownership bypass) |
| TC-8 | POST /api/users — valid token with api-a:write | 201 with new record |
| TC-9 | PUT /api/users/alice@example.com — api-a:write scope | 200 with updated record |
| TC-10 | Any protected endpoint — expired token | 401 |
| TC-11 | CORS: request from http://localhost:3000 | 200 with correct CORS headers |
| TC-12 | CORS: request from http://evil.com | No CORS headers (request blocked by browser) |

**Verification command:**
```bash
cd okta-identity-lab/api-a && source .env && .venv/bin/python -m uvicorn app.main:app --port 3001 &
sleep 2

# Health — no auth
curl -s http://localhost:3001/health

# No token → 401
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3001/api/users)
echo "No token: $STATUS (expect 401)"

# Wrong CORS origin — verify header absent
curl -s -H "Origin: http://evil.com" -I http://localhost:3001/health | grep -i "access-control"

kill %1
```

**Invariant flag:** INV-07, INV-12, INV-14, INV-16, INV-20, INV-21, INV-23. Code review: confirm `require_scope("api-a:read")` is applied via `Depends()` on every protected route; confirm `leeway=60` in verify_token (from Task 2.3); confirm no stack trace in any 4xx/5xx response body; confirm `allow_origins` does not contain `"*"`.

---

### Task 2.5 — API A Startup Verification

**Description:** Wire the app together, write the startup script, and confirm the full API A stack runs clean with a real Okta token obtained from the test user.

**CC prompt:**
```
In api-a/, create a startup script run.sh:
  #!/bin/bash
  set -a && source .env && set +a
  .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 3001 --reload

Make it executable (chmod +x run.sh).

In api-a/README.md, document:
  1. Prerequisites (Python 3.11+, .env populated)
  2. Setup: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
  3. Run: ./run.sh
  4. Endpoints list with required scopes

Do not modify any application code.
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | run.sh starts cleanly | Uvicorn logs show "Application startup complete" on port 3001 |
| TC-2 | /health accessible | curl returns 200 |
| TC-3 | JWKS cache logs on startup | First token validation shows JWKS_CACHE_MISS then JWKS_CACHE_REFRESHED |

**Verification command:**
```bash
cd okta-identity-lab/api-a && bash run.sh &
sleep 3
curl -s http://localhost:3001/health
kill %1
```

**Invariant flag:** INV-11 (JWKS cache logging observable on startup).

---

## Session 3 — API B: Admin Auth

**Session goal:** API B starts on port 3002, serves all five endpoints, enforces scope + group-based auth (api-b:admin scope alone is insufficient for admin routes — group membership required), writes every protected request to the in-memory audit_log, and the audit_log endpoint returns the self-populated log.

**Integration check:**
```bash
cd okta-identity-lab/api-b && bash run.sh &
sleep 2

# Health — no auth
curl -s http://localhost:3002/health

# No token → 401 on protected route
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3002/api/analytics/summary)
echo "No token: $STATUS (expect 401)"

# Confirm audit_log is populated after the 401 attempt
# (Requires a valid token with api-b:read scope for this endpoint — test with alice's token)
# Full audit_log test deferred to Session 7 (system sign-off with real tokens)

kill %1
```

---

### Task 3.1 — Mock Database (API B)

**Description:** Implement the API B in-memory database: analytics aggregate, config dict, and audit_log list. All three are independent data structures per ARCHITECTURE.md Section 8.

**CC prompt:**
```
In api-b/app/db/mock_db.py, implement the in-memory mock database for API B.

Three independent module-level data structures:

_analytics: dict = {
    "total_users": 42,
    "active_sessions": 7,
    "last_updated": "2026-03-22T00:00:00Z"
}

_config: dict = {
    "maintenance_mode": False,
    "log_level": "INFO",
    "feature_flags": {"dark_mode": True, "beta_features": False}
}

_audit_log: list[dict] = []  # starts empty — populated at runtime by auth middleware

Functions (exact signatures):

  def get_analytics() -> dict:
      return _analytics.copy()

  def get_config() -> dict:
      return _config.copy()

  def update_config(updates: dict) -> dict:
      _config.update(updates)
      return _config.copy()

  def append_audit_entry(entry: dict) -> None:
      """entry must have: timestamp (str), subject (str), route (str), outcome (str)"""
      _audit_log.append(entry)

  def get_audit_log() -> list[dict]:
      return list(_audit_log)

Do not add auth logic. Do not import fastapi or jose.
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | get_analytics returns seed | Dict with total_users=42 |
| TC-2 | get_config returns seed | maintenance_mode=False |
| TC-3 | update_config patches correctly | Updated key reflected in subsequent get_config |
| TC-4 | append_audit_entry + get_audit_log | Entry appears in log |
| TC-5 | audit_log starts empty | get_audit_log() returns [] on fresh import |

**Verification command:**
```bash
cd okta-identity-lab && api-b/.venv/bin/python -c "
from api_b.app.db.mock_db import get_analytics, get_config, update_config, append_audit_entry, get_audit_log
import datetime
assert get_analytics()['total_users'] == 42
assert get_config()['maintenance_mode'] == False
update_config({'log_level': 'DEBUG'})
assert get_config()['log_level'] == 'DEBUG'
assert get_audit_log() == []
append_audit_entry({'timestamp': datetime.datetime.utcnow().isoformat(), 'subject': 'test', 'route': '/test', 'outcome': 'pass'})
assert len(get_audit_log()) == 1
print('api-b mock_db OK')
"
```

**Invariant flag:** INV-15 (audit log write path). Code review: confirm `append_audit_entry` is called by auth middleware (Task 3.2), not by route handlers.

---

### Task 3.2 — JWKS Cache + JWT Auth Middleware (API B)

**Description:** Duplicate and adapt the JWKS cache and JWT auth middleware from API A into API B. This is intentional per Decision 2 (no shared code). The implementation is identical in structure; the configuration is independent.

**CC prompt:**
```
Copy the JWKS cache and auth middleware from API A into API B. These are independent implementations — do not create a shared module or symlink.

1. Copy api-a/app/auth/jwks_cache.py → api-b/app/auth/jwks_cache.py unchanged.

2. Copy api-a/app/auth/__init__.py → api-b/app/auth/__init__.py as a base,
   then modify as follows:

   In api-b/app/auth/__init__.py:
   - Keep verify_token unchanged
   - Keep require_scope unchanged
   - Modify _log_auth_decision to also call:
       from app.db.mock_db import append_audit_entry
       append_audit_entry({
           "timestamp": datetime.utcnow().isoformat(),
           "subject": subject,
           "route": route,
           "outcome": outcome
       })
     This means EVERY auth decision in API B (pass or fail) is written to the audit log. (INV-15)

   - Add a second dependency factory: require_group(required_group: str)
       def require_group(required_group: str):
           def check_group(claims: dict = Depends(verify_token)) -> dict:
               token_groups = claims.get("groups", [])
               if required_group not in token_groups:
                   _log_auth_decision(claims.get("sub", "anonymous"), "group_check", required_group, "fail")
                   raise HTTPException(status_code=403, detail={"error": "insufficient_privileges", "message": f"Required group: {required_group}"})
               _log_auth_decision(claims.get("sub", "anonymous"), "group_check", required_group, "pass")
               return claims
           return check_group

Do not modify api-a/ files. Do not create a shared package.
Do not import from api-a/.
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | verify_token loads from api-b .env | OKTA_ISSUER/OKTA_AUDIENCE read from api-b's own .env |
| TC-2 | require_group — user in group | Returns claims, logs pass |
| TC-3 | require_group — user not in group | 403, logs fail, audit entry written |
| TC-4 | Every auth decision writes to audit_log | After 3 requests, get_audit_log() has 3 entries |

**Verification command:**
```bash
cd okta-identity-lab/api-b && source .env && .venv/bin/python -c "
from app.auth import verify_token, require_scope, require_group
from app.db.mock_db import get_audit_log
print('API B auth module loads OK')
print('Audit log starts empty:', get_audit_log())
"
```

**Invariant flag:** INV-07, INV-08, INV-09, INV-10, INV-11, INV-13, INV-15, INV-18, INV-23. Code review: confirm `append_audit_entry` is called in `_log_auth_decision`, not in route handlers; confirm api-b imports nothing from api-a.

---

### Task 3.3 — API B Route Handlers

**Description:** Implement all five API B routes with scope + group auth as appropriate.

**CC prompt:**
```
In api-b/app/routes/ and api-b/app/main.py, implement the API B route handlers.

GET /health — no auth, returns {"status": "ok"}

GET /api/analytics/summary — requires api-b:read scope (no group check)
  Returns mock_db.get_analytics()

GET /api/config — requires BOTH api-b:admin scope AND api-b-admins group
  Dependency chain: require_scope("api-b:admin") then require_group("api-b-admins")
  Returns mock_db.get_config()

POST /api/config — requires BOTH api-b:admin scope AND api-b-admins group
  Body: partial config update dict
  Calls mock_db.update_config(body). Returns 200 with updated config.

GET /api/audit-log — requires BOTH api-b:admin scope AND api-b-admins group
  Returns mock_db.get_audit_log()

In api-b/app/main.py:
  - Create FastAPI app instance
  - Add CORS middleware: allow_origins=["http://localhost:3000"] only (INV-20)
  - Add global exception handler (same as API A — no stack traces) (INV-21)
  - Include all routers

Dependency ordering for dual-gated routes: require_scope must execute before require_group.
A user with the correct group but missing scope must receive 403 "insufficient_scope", not 403 "insufficient_privileges".
This tests the layered nature of the authorization model.
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | GET /health — no token | 200 |
| TC-2 | GET /api/analytics/summary — no token | 401 |
| TC-3 | GET /api/analytics/summary — api-b:read scope | 200 with analytics data |
| TC-4 | GET /api/config — api-b:admin scope, NOT in api-b-admins group | 403 "insufficient_privileges" |
| TC-5 | GET /api/config — in api-b-admins group, missing api-b:admin scope | 403 "insufficient_scope" |
| TC-6 | GET /api/config — admin token (scope + group) | 200 with config |
| TC-7 | GET /api/audit-log — admin token | 200 with audit entries |
| TC-8 | POST /api/config — admin token, valid body | 200 with updated config |
| TC-9 | After multiple requests to protected routes, audit_log grows | GET /api/audit-log shows all entries |

**Verification command:**
```bash
cd okta-identity-lab/api-b && bash run.sh &
sleep 2
curl -s http://localhost:3002/health
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3002/api/analytics/summary)
echo "No token analytics: $STATUS (expect 401)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3002/api/config)
echo "No token config: $STATUS (expect 401)"
kill %1
```

**Invariant flag:** INV-12, INV-13, INV-15, INV-16, INV-20, INV-21, INV-23. Code review: confirm dual dependency chain on admin routes; confirm audit write happens on BOTH pass and fail outcomes.

---

### Task 3.4 — API B Startup Script

**Description:** Wire the app, create run.sh, update README.md. Same pattern as Task 2.5.

**CC prompt:**
```
In api-b/, create run.sh:
  #!/bin/bash
  set -a && source .env && set +a
  .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 3002 --reload

Make executable. Update api-b/README.md with setup and endpoints list including required scope/group for each.
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | run.sh starts on port 3002 | Uvicorn startup complete |
| TC-2 | /health returns 200 | curl confirms |

**Verification command:**
```bash
cd okta-identity-lab/api-b && bash run.sh & sleep 3 && curl -s http://localhost:3002/health && kill %1
```

**Invariant flag:** None. Wiring task.

---

## Session 4 — Frontend SPA

**Session goal:** The React SPA runs on port 3000, completes Auth Code + PKCE login via Okta, displays user info from the ID token on the Dashboard, shows the Token Inspector Panel with live countdown, calls all API A and API B endpoints via the API Tester Panel with visual 401/403 treatment, and the Token Refresh Demo shows before/after states simultaneously.

**Integration check:**
```bash
cd okta-identity-lab/frontend && npm run dev -- --port 3000 &
sleep 3
# Confirm app serves at root
curl -s http://localhost:3000 | grep -i "root\|vite\|react"
# Confirm no localStorage writes for access tokens (static analysis)
grep -r "localStorage.setItem" src/ && echo "INV-02 VIOLATION" || echo "INV-02 PASS"
kill %1
```

---

### Task 4.1 — Okta Auth Configuration and Router

**Description:** Configure @okta/okta-react with the correct OIDC settings. Set up React Router with protected routes. Implement the PKCE redirect and callback handling.

**CC prompt:**
```
In frontend/src/, set up the Okta authentication foundation.

Create frontend/src/config/oktaConfig.js:
  import { OktaAuth } from '@okta/okta-auth-js';

  export const oktaAuth = new OktaAuth({
    issuer: import.meta.env.VITE_OKTA_ISSUER,
    clientId: import.meta.env.VITE_OKTA_CLIENT_ID,
    redirectUri: import.meta.env.VITE_OKTA_REDIRECT_URI,
    scopes: ['openid', 'profile', 'email', 'offline_access', 'api-a:read', 'api-a:write', 'api-b:read', 'api-b:admin'],
    pkce: true,
    tokenManager: {
      storage: 'sessionStorage',   // refresh tokens only — NOT access tokens
      storageKey: 'okta-token-storage',
    },
  });

  // CRITICAL: Access tokens must NOT be stored by the SDK in localStorage.
  // The tokenManager stores tokens — access tokens are stored in session-scoped memory,
  // refresh tokens use sessionStorage. Verify the SDK default behaviour satisfies INV-02 and INV-03.

Create frontend/src/App.jsx:
  - Wrap the app in <Security oktaAuth={oktaAuth} restoreOriginalUri={...}>
  - Set up React Router with routes:
    - / → <LoginPage /> (public)
    - /login/callback → <LoginCallback /> (from @okta/okta-react, handles PKCE callback)
    - /dashboard → <SecureRoute><Dashboard /></SecureRoute>
  - SecureRoute redirects unauthenticated users to /

Do not implement page components yet — use placeholder components that render a single div with the route name.
Do not hardcode any Okta credentials.
State validation is handled by the okta-auth-js SDK internally — do not disable or bypass it. (INV-28)
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | App compiles without errors | `npm run build` exits 0 |
| TC-2 | / renders LoginPage | curl or browser shows root route |
| TC-3 | /dashboard redirects to Okta | Unauthenticated visit to /dashboard triggers Okta redirect |
| TC-4 | No credential literals in source | `grep -r "dev-" src/` returns nothing |
| TC-5 | pkce: true is set | Code inspection shows pkce flag in oktaConfig |

**Verification command:**
```bash
cd okta-identity-lab/frontend && npm run build 2>&1 | tail -5
grep -r "localStorage" src/ && echo "localStorage found — review" || echo "No localStorage in src"
grep "pkce: true" src/config/oktaConfig.js && echo "PKCE flag present" || echo "PKCE MISSING — INV-01 risk"
```

**Invariant flag:** INV-01 (PKCE), INV-02 (no localStorage), INV-22 (no hardcoded credentials), INV-28 (state param, SDK-handled). Code review: confirm no `localStorage.setItem` anywhere in `src/`; confirm `pkce: true` in config; confirm no `ignoreSignature` or equivalent SDK bypass flags.

---

### Task 4.2 — Login Page and Dashboard

**Description:** Implement the Login Page (single "Login with Okta" button) and the Dashboard (user display name, email from ID token). Access token stored in React state via context.

**CC prompt:**
```
Implement the Login Page and Dashboard components, and the access token context.

Create frontend/src/context/TokenContext.jsx:
  - React context providing: { accessToken, setAccessToken }
  - accessToken stored in useState — in JavaScript memory only
  - Never written to localStorage, sessionStorage, or cookies (INV-02)
  - Export: TokenProvider (wrap app root), useToken (hook)

Create frontend/src/pages/LoginPage.jsx:
  - Single "Login with Okta" button
  - On click: calls oktaAuth.signInWithRedirect({ scopes: [...all scopes...] })
  - If user is already authenticated: redirect to /dashboard

Create frontend/src/pages/Dashboard.jsx:
  - Uses useOktaAuth() to get authState and oktaAuth
  - On mount: if authenticated, call oktaAuth.getAccessToken() and store in TokenContext
  - Display from authState.idToken.claims: user's name, email
  - Display: "Token loaded" or "No token" status
  - Navigation links to Token Inspector, API Tester, Token Refresh Demo panels

Wrap App.jsx root with <TokenProvider>.

Access token flow:
  1. After login, Dashboard calls oktaAuth.getAccessToken() → stores in TokenContext (memory only)
  2. All child components read from TokenContext — never call getAccessToken() independently
  3. On page refresh: useEffect on Dashboard mount attempts silent restore via getAccessToken()
     (SDK handles the refresh token path internally)
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | LoginPage renders button | "Login with Okta" button visible |
| TC-2 | After login, Dashboard shows user name and email | Values from ID token claims |
| TC-3 | Access token in TokenContext (memory) | TokenContext has non-null accessToken after login |
| TC-4 | Page refresh — token restored | After refresh, accessToken is restored to memory via SDK silent path |
| TC-5 | No localStorage write for access token | DevTools Application → LocalStorage: no token entries |

**Verification command:**
```bash
cd okta-identity-lab/frontend
grep -r "localStorage" src/ && echo "VIOLATION INV-02" || echo "INV-02 OK"
grep -rn "setAccessToken\|TokenContext" src/ | head -10
npm run build 2>&1 | grep -E "error|warning" | head -10
```

**Invariant flag:** INV-02, INV-03, INV-04, INV-06. Code review: confirm `setAccessToken` is only called with the value from `oktaAuth.getAccessToken()`, not from any storage read; confirm no `localStorage.setItem` or `document.cookie` write for tokens in any component.

---

### Task 4.3 — Token Inspector Panel

**Description:** Implement the Token Inspector Panel: decoded JWT header, full payload, live expiry countdown updating every second, raw base64url segments.

**CC prompt:**
```
Create frontend/src/components/TokenInspector.jsx.

This component reads the access token from TokenContext (useToken()) and displays:

1. HEADER section — decoded: alg, kid
2. PAYLOAD section — all claims including: iss, sub, aud, exp, iat, scp (as list), groups (as list), department, employee_id, and any other claims present
3. EXPIRY COUNTDOWN — live countdown in seconds to token expiry, updating every second via setInterval
   Format: "Expires in Xs" — turns red when < 60 seconds remaining
4. RAW SEGMENTS — the three base64url segments of the JWT displayed in monospace, each labeled: Header, Payload, Signature

JWT decoding must be done in-browser using atob() on the base64url segments. Do not call any API to decode.
Do not use any JWT library for decoding the display — manual base64url decode only.

Base64url decode helper:
  function decodeSegment(segment) {
    const padded = segment.replace(/-/g, '+').replace(/_/g, '/');
    const padLength = (4 - padded.length % 4) % 4;
    return JSON.parse(atob(padded + '='.repeat(padLength)));
  }

If no access token is in context: render "No access token — please log in."
If token format is invalid: render "Token decode error."

The countdown timer must clear on component unmount (clearInterval in useEffect cleanup).
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | No token in context | "No access token" message |
| TC-2 | Valid token — header section | alg and kid values displayed correctly |
| TC-3 | Valid token — payload section | All standard + custom claims visible |
| TC-4 | Expiry countdown | Updates every second, matches exp claim |
| TC-5 | Countdown <60s | Turns red |
| TC-6 | Raw segments visible | Three base64url strings displayed |
| TC-7 | No external JWT library used | `grep -r "jwt-decode\|jsonwebtoken" src/` returns nothing |

**Verification command:**
```bash
cd okta-identity-lab/frontend
grep -r "jwt-decode\|jsonwebtoken\|jose" src/ && echo "External JWT lib found — review" || echo "No external JWT lib (correct)"
grep -n "decodeSegment\|atob\|setInterval\|clearInterval" src/components/TokenInspector.jsx | head -20
npm run build 2>&1 | grep error
```

**Invariant flag:** INV-25. Code review: confirm all required fields are rendered (use checklist from INV-25); confirm `clearInterval` in useEffect cleanup; confirm no external JWT decode library.

---

### Task 4.4 — API Tester Panel

**Description:** Implement the API Tester Panel: one button per protected endpoint (all 8 endpoints from Brief Sections 5.1 and 5.2), full request display (URL + Authorization header truncated for readability), raw response display with visually distinct 200/401/403 treatment.

**CC prompt:**
```
Create frontend/src/components/ApiTester.jsx.

This component calls API A (http://localhost:3001) and API B (http://localhost:3002) from the browser, using the access token from TokenContext.

Implement buttons for all 8 protected endpoints:

API A:
  - GET /api/users
  - GET /api/users/:id  (prompt user for email in a text input before calling)
  - POST /api/users (use a hardcoded test payload: {"email":"test@example.com","name":"Test","department":"QA","employee_number":"EMP999"})
  - PUT /api/users/:id (prompt for email; hardcoded update: {"department":"Updated"})

API B:
  - GET /api/analytics/summary
  - GET /api/config
  - POST /api/config (hardcoded update: {"log_level":"DEBUG"})
  - GET /api/audit-log

For each call:
  1. Show the full request: method, URL, Authorization: Bearer <first 20 chars>...
  2. Show the response: HTTP status code (large, bold) + raw JSON body
  3. Status code 200: render with green border/badge
  4. Status code 401: render with red border/badge + label "Unauthenticated"
  5. Status code 403: render with amber/orange border/badge + label "Forbidden"
  6. Status codes 4xx/5xx: render with red border

State: keep the last response per endpoint visible until a new call is made.

If no access token is in context: all buttons disabled, show "Login required" message.

Do not store responses in localStorage. Component state only.
All fetch calls must include headers: { "Authorization": `Bearer ${accessToken}`, "Content-Type": "application/json" }
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | All 8 buttons rendered | Count: 8 buttons present in DOM |
| TC-2 | No token — all buttons disabled | Buttons in disabled state |
| TC-3 | GET /api/users with valid token | 200 green, user list displayed |
| TC-4 | GET /api/config with non-admin token | 403 amber displayed |
| TC-5 | Request with expired token | 401 red displayed |
| TC-6 | Full request visible | URL and truncated Bearer token shown above response |

**Verification command:**
```bash
cd okta-identity-lab/frontend
grep -c "onClick" src/components/ApiTester.jsx  # expect >= 8
grep -n "401\|403\|200" src/components/ApiTester.jsx | head -20
npm run build 2>&1 | grep error
```

**Invariant flag:** INV-24, INV-27. Code review: confirm all 8 endpoints from Brief Sections 5.1/5.2 have corresponding buttons; confirm 401 and 403 have visually distinct rendering classes.

---

### Task 4.5 — Token Refresh Demo Panel

**Description:** Implement the Token Refresh Demo Panel: capture before-state on user trigger, initiate silent refresh via SDK, display before and after simultaneously.

**CC prompt:**
```
Create frontend/src/components/TokenRefreshDemo.jsx.

This component demonstrates silent token refresh. It has one button: "Trigger Silent Refresh".

State:
  - beforeToken: string | null  — snapshot of the access token at the moment the button is clicked
  - afterToken: string | null   — the new access token received after refresh
  - refreshStatus: 'idle' | 'refreshing' | 'success' | 'error'

On button click:
  1. Snapshot the current access token from TokenContext into beforeToken (INV-26 — must capture BEFORE calling refresh)
  2. Set refreshStatus = 'refreshing'
  3. Call oktaAuth.tokenManager.renew('accessToken')
  4. On success: set afterToken to the new token string; call setAccessToken(newToken) in TokenContext; set refreshStatus = 'success'
  5. On failure: set refreshStatus = 'error'; redirect to login (INV-06)

Display:
  - "Before" panel: decoded exp claim from beforeToken (or "No token")
  - "After" panel: decoded exp claim from afterToken (or "Waiting...")
  - Both panels visible simultaneously after refresh completes (INV-26)
  - A diff highlight if afterToken.exp > beforeToken.exp (shows token was actually renewed)

The before panel must NOT be cleared when afterToken is set. Both remain visible.
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | Before state captured correctly | beforeToken shows current token exp before refresh |
| TC-2 | After state shows new token | afterToken exp > beforeToken exp (new token issued) |
| TC-3 | Both panels visible simultaneously | Before and after rendered at same time (INV-26) |
| TC-4 | Refresh failure redirects to login | oktaAuth error → redirect to / |
| TC-5 | TokenContext updated | After refresh, subsequent API calls use new token |

**Verification command:**
```bash
cd okta-identity-lab/frontend
grep -n "beforeToken\|afterToken\|renew" src/components/TokenRefreshDemo.jsx
grep -n "beforeToken = null\|setBeforeToken(null)" src/components/TokenRefreshDemo.jsx && echo "WARNING: before state may be cleared" || echo "Before state preserved OK"
npm run build 2>&1 | grep error
```

**Invariant flag:** INV-26, INV-05, INV-06. Code review: confirm `beforeToken` snapshot is taken BEFORE the `renew()` call; confirm `beforeToken` is never set to null after the refresh succeeds; confirm refresh failure triggers redirect, not silent continuation.

---

### Task 4.6 — Proactive Silent Refresh Timer

**Description:** Implement the 60-second-before-expiry proactive refresh timer. Wired into the Dashboard or a top-level auth component.

**CC prompt:**
```
In frontend/src/components/AuthManager.jsx (new file), implement the proactive refresh timer.

This component renders null (no UI). It is mounted once inside the Security provider and runs for the lifetime of the session.

Logic:
  1. On mount and whenever accessToken changes in TokenContext: read the token's exp claim
  2. Calculate: refreshAt = (exp * 1000) - Date.now() - 60000  (60 seconds before expiry, in ms)
  3. If refreshAt > 0: set a setTimeout for refreshAt ms
  4. On timeout: call oktaAuth.tokenManager.renew('accessToken')
     - On success: update TokenContext with new token; reschedule timer from new exp
     - On failure: redirect to / and clear TokenContext (INV-06)
  5. On component unmount or token change: clear the previous setTimeout

The timer must be reset after each successful refresh — not set only once at login. (INV-05)

Mount this component inside App.jsx, inside the Security wrapper but outside any route.
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | Timer set after login | setTimeout called with positive delay |
| TC-2 | Timer fires at exp - 60s | Refresh triggered before expiry |
| TC-3 | Timer reset after refresh | New timer set based on new token exp |
| TC-4 | Refresh failure → redirect | User sent to login page |
| TC-5 | Timer cleared on unmount | clearTimeout called in useEffect cleanup |

**Verification command:**
```bash
cd okta-identity-lab/frontend
grep -n "setTimeout\|clearTimeout\|exp.*1000\|60000" src/components/AuthManager.jsx
grep -n "AuthManager" src/App.jsx && echo "AuthManager mounted in App" || echo "AuthManager NOT mounted — timer won't run"
npm run build 2>&1 | grep error
```

**Invariant flag:** INV-05, INV-06. Code review: confirm timer is rescheduled after each successful renew (not just once at login); confirm clearTimeout in useEffect cleanup; confirm failure path redirects.

---

## Session 5 — M2M Flow

**Session goal:** API A can obtain a client credentials access token from Okta using its own Client ID and Secret, call API B's analytics endpoint with that token, and return the result. API B validates the M2M token through the same JWKS middleware with no special handling.

**Integration check:**
```bash
# Start both APIs
cd okta-identity-lab/api-a && bash run.sh &
cd okta-identity-lab/api-b && bash run.sh &
sleep 3

# Call the M2M trigger endpoint (no user token needed — API A fetches its own token)
curl -s http://localhost:3001/api/internal/pull-analytics
# Expect: JSON response containing analytics data from API B

kill %1 %2
```

---

### Task 5.1 — M2M Token Fetch (API A)

**Description:** Implement the client credentials token fetch function in API A. Reads Client ID and Secret from environment. Explicitly requests `scope=api-b:read`.

**CC prompt:**
```
In api-a/app/auth/m2m.py (new file), implement the M2M token fetch function.

Function:
  async def fetch_m2m_token() -> str:
      """
      Fetch a client credentials access token from Okta for API-to-API calls.
      Returns the raw access token string.
      Raises HTTPException(503) if the token endpoint call fails.
      """

Implementation:
  1. Read from environment: OKTA_CLIENT_ID, OKTA_CLIENT_SECRET, OKTA_TOKEN_ENDPOINT
  2. Make a POST request to OKTA_TOKEN_ENDPOINT using httpx:
     - grant_type=client_credentials
     - scope=api-b:read   (must be explicitly included — INV-17)
     - auth=(OKTA_CLIENT_ID, OKTA_CLIENT_SECRET)  (HTTP Basic auth)
     - Content-Type: application/x-www-form-urlencoded
  3. If response.status_code != 200: log the error and raise HTTPException(status_code=503, detail={"error": "m2m_token_error", "message": "Failed to obtain M2M token"})
  4. Parse response JSON: return response.json()["access_token"]

Do NOT log the access token value or the client secret at any point. (INV-19)
Do NOT hardcode credentials. Read from os.environ only.
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | fetch_m2m_token with valid credentials | Returns a JWT string |
| TC-2 | fetch_m2m_token with wrong secret | Okta returns 401, function raises HTTPException(503) |
| TC-3 | scope=api-b:read in request | Token endpoint called with scope parameter |
| TC-4 | Token value not in logs | Log output does not contain the raw JWT |
| TC-5 | Secret not in logs | Log output does not contain OKTA_CLIENT_SECRET value |

**Verification command:**
```bash
cd okta-identity-lab/api-a && source .env && .venv/bin/python -c "
import asyncio
from app.auth.m2m import fetch_m2m_token
token = asyncio.run(fetch_m2m_token())
print('Token starts with:', token[:20], '...')
assert len(token.split('.')) == 3, 'Not a JWT'
print('M2M token fetch OK')
"
```

**Invariant flag:** INV-17, INV-19. Code review: confirm `scope=api-b:read` is in the POST body; confirm no logging of token or secret value; confirm credentials come from `os.environ`.

---

### Task 5.2 — Internal Pull-Analytics Endpoint (API A)

**Description:** Implement `GET /api/internal/pull-analytics` — the endpoint that triggers the M2M flow. API A fetches its own token and calls API B.

**CC prompt:**
```
In api-a/app/routes/internal.py, implement the internal pull-analytics endpoint.

  GET /api/internal/pull-analytics — no user auth required (this endpoint is for M2M demo)

  Logic:
  1. Call fetch_m2m_token() to get an M2M access token
  2. Using httpx, call GET http://localhost:3002/api/analytics/summary
     with header: Authorization: Bearer <m2m_token>
  3. If API B returns 200: return {"source": "api-b", "data": <response body>}
  4. If API B returns 4xx/5xx: return {"source": "api-b", "error": <status code>, "message": "API B call failed"}

Include this router in api-a/app/main.py.

Log the M2M call: log subject "api-a-m2m", route "/api/internal/pull-analytics", scope "api-b:read", outcome based on API B response status.

Do not pass the M2M token value in any log field. (INV-19)
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | API B running — happy path | Returns analytics data from API B |
| TC-2 | API B down | Returns structured error (not stack trace) |
| TC-3 | M2M token used by API B — same JWKS path | API B logs show validation via JWKS, no special handling |
| TC-4 | Token not logged | API A logs for this call contain no JWT string |

**Verification command:**
```bash
# Both APIs must be running
cd okta-identity-lab
api-b/run.sh &
sleep 2
api-a/run.sh &
sleep 2
curl -s http://localhost:3001/api/internal/pull-analytics | python3 -m json.tool
kill %1 %2
```

**Invariant flag:** INV-17, INV-18, INV-19. Code review: confirm API A calls API B at `localhost:3002`; confirm `Authorization: Bearer` header used; confirm API B auth middleware applies (no route bypass).

---

### Task 5.3 — M2M End-to-End Verification

**Description:** Verify the complete M2M chain: token fetch, API B validation, scope enforcement, and audit log entry creation — with no human user token in the flow.

> **Note:** This is primarily a verification task, not a build task. CC is used only if gaps were found in Tasks 5.1 or 5.2.

**CC prompt (only if gaps found):**
```
Fix any issues identified during M2M verification. Do not add new features.
Specific fixes: [engineer fills in gaps from verification]
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | Full M2M chain succeeds | GET /api/internal/pull-analytics returns analytics data |
| TC-2 | API B audit_log populated by M2M call | GET /api/audit-log shows entry with subject from M2M token sub |
| TC-3 | M2M token has api-b:read scope | Decoded M2M token scp claim contains api-b:read |
| TC-4 | M2M call to api-b:admin endpoint | 403 (M2M token lacks admin scope) |
| TC-5 | Client secret not in API A response body | curl response from /api/internal/pull-analytics has no secret value |

**Verification command:**
```bash
# Both APIs running
RESULT=$(curl -s http://localhost:3001/api/internal/pull-analytics)
echo "M2M result: $RESULT" | python3 -m json.tool
echo "$RESULT" | grep -i "client_secret\|OKTA_CLIENT" && echo "SECRET LEAK — INV-19 VIOLATION" || echo "No secret leak"
```

**Invariant flag:** INV-17, INV-18, INV-19.

---

## Session 6 — Enterprise Hardening

**Session goal:** CORS is explicitly verified to reject non-allowlisted origins on both APIs. JWKS key rotation is tested manually (forced cache invalidation path). The engineer has completed the Okta System Log walkthrough. All non-functional requirements are met.

**Integration check:**
```bash
# CORS lockdown — wrong origin returns no CORS headers
curl -s -H "Origin: http://attacker.com" -I http://localhost:3001/api/users | grep -i "access-control-allow-origin"
# Expect: no line (header absent)

# CORS — correct origin returns header
curl -s -H "Origin: http://localhost:3000" -I http://localhost:3001/health | grep -i "access-control-allow-origin"
# Expect: access-control-allow-origin: http://localhost:3000

# OPTIONS preflight — correct origin returns 200
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X OPTIONS -H "Origin: http://localhost:3000" -H "Access-Control-Request-Method: GET" http://localhost:3001/api/users)
echo "OPTIONS preflight: $STATUS (expect 200)"
```

---

### Task 6.1 — CORS Lockdown Verification (Both APIs)

**Description:** Verify and harden CORS configuration on both APIs. The middleware was set in Sessions 2 and 3. This task adds an explicit integration test script.

**CC prompt:**
```
In okta-identity-lab/, create scripts/test_cors.sh:

#!/bin/bash
# CORS lockdown verification script — tests both APIs
# Both APIs must be running before executing this script

ALLOWED_ORIGIN="http://localhost:3000"
BLOCKED_ORIGIN="http://attacker.com"
API_A="http://localhost:3001"
API_B="http://localhost:3002"

echo "=== API A CORS Tests ==="
# Allowed origin — should return CORS header
HEADER=$(curl -s -H "Origin: $ALLOWED_ORIGIN" -I $API_A/health | grep -i "access-control-allow-origin")
echo "Allowed origin header: $HEADER"

# Blocked origin — should NOT return CORS header
HEADER=$(curl -s -H "Origin: $BLOCKED_ORIGIN" -I $API_A/health | grep -i "access-control-allow-origin")
[ -z "$HEADER" ] && echo "PASS: Blocked origin rejected" || echo "FAIL: Blocked origin header present: $HEADER"

# OPTIONS preflight
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X OPTIONS -H "Origin: $ALLOWED_ORIGIN" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: Authorization" $API_A/api/users)
[ "$STATUS" = "200" ] && echo "PASS: OPTIONS preflight 200" || echo "FAIL: OPTIONS $STATUS"

echo ""
echo "=== API B CORS Tests ==="
# Same three tests for API B
HEADER=$(curl -s -H "Origin: $ALLOWED_ORIGIN" -I $API_B/health | grep -i "access-control-allow-origin")
echo "Allowed origin header: $HEADER"

HEADER=$(curl -s -H "Origin: $BLOCKED_ORIGIN" -I $API_B/health | grep -i "access-control-allow-origin")
[ -z "$HEADER" ] && echo "PASS: Blocked origin rejected" || echo "FAIL: Blocked origin header present: $HEADER"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X OPTIONS -H "Origin: $ALLOWED_ORIGIN" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: Authorization" $API_B/api/analytics/summary)
[ "$STATUS" = "200" ] && echo "PASS: OPTIONS preflight 200" || echo "FAIL: OPTIONS $STATUS"

Make executable: chmod +x scripts/test_cors.sh
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | Allowed origin — API A | CORS header present |
| TC-2 | Blocked origin — API A | No CORS header |
| TC-3 | OPTIONS preflight — API A | 200 response |
| TC-4 | Allowed origin — API B | CORS header present |
| TC-5 | Blocked origin — API B | No CORS header |
| TC-6 | OPTIONS preflight — API B | 200 response |

**Verification command:**
```bash
bash okta-identity-lab/scripts/test_cors.sh
```

**Invariant flag:** INV-20. Code review: confirm `allow_origins` in both `main.py` files is `["http://localhost:3000"]` — not `["*"]` and not an empty list.

---

### Task 6.2 — JWKS Key Rotation Test

**Description:** Verify the forced JWKS cache invalidation path works correctly. The engineer triggers rotation manually in Okta console; this task provides the test script.

**CC prompt:**
```
In okta-identity-lab/scripts/test_jwks_rotation.sh, create a key rotation test script:

#!/bin/bash
# JWKS cache rotation test
# Step 1: Make a valid API call — confirm cache is warm (check logs for JWKS_CACHE_HIT)
# Step 2: Engineer manually triggers key rotation in Okta Admin Console
# Step 3: Make a new API call — first call after rotation should trigger JWKS_CACHE_INVALIDATED_REFETCH (if kid changes)
#          or JWKS_CACHE_MISS (if TTL expired) — both are acceptable
# Step 4: Confirm subsequent calls succeed (new key cached)

echo "This script documents the manual steps for JWKS key rotation testing."
echo "Automated portion: confirm JWKS cache log output is observable."
echo ""
echo "Step 1: Making a request to warm the cache..."
echo "  Check API A logs for: JWKS_CACHE_REFRESHED or JWKS_CACHE_HIT"
echo ""
echo "Step 2: MANUAL — In Okta Admin Console:"
echo "  Security → API → okta-lab-authserver → Rotate Signing Keys"
echo ""
echo "Step 3: Making a request after rotation..."
echo "  Check API A logs for: JWKS_CACHE_INVALIDATED_REFETCH"
echo ""
echo "Step 4: Making a second request after rotation..."
echo "  Check API A logs for: JWKS_CACHE_HIT (new key now cached)"
echo ""
echo "If all four log events appear in sequence: key rotation handling PASS"

Also add a forced cache invalidation test to api-a/app/auth/jwks_cache.py:
  Add a test endpoint (only in dev mode — guard with an IS_DEV env var):
    POST /dev/invalidate-jwks-cache — calls jwks_cache.invalidate_and_refetch()
    Returns {"message": "JWKS cache invalidated and refetched", "key_count": len(jwks_cache._keys)}
  This endpoint must not exist if IS_DEV is not set to "true".
```

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | Warm cache — request hits cache | API A logs show JWKS_CACHE_HIT |
| TC-2 | POST /dev/invalidate-jwks-cache | Returns key count, logs JWKS_CACHE_INVALIDATED_REFETCH |
| TC-3 | Request after forced invalidation | Logs show JWKS_CACHE_REFRESHED, then request succeeds |
| TC-4 | IS_DEV not set — endpoint absent | POST /dev/invalidate-jwks-cache returns 404 |

**Verification command:**
```bash
# With IS_DEV=true
IS_DEV=true bash okta-identity-lab/api-a/run.sh &
sleep 2
curl -s -X POST http://localhost:3001/dev/invalidate-jwks-cache | python3 -m json.tool
kill %1

# Without IS_DEV
bash okta-identity-lab/api-a/run.sh &
sleep 2
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:3001/dev/invalidate-jwks-cache)
[ "$STATUS" = "404" ] && echo "Dev endpoint gated correctly" || echo "FAIL: dev endpoint exposed without IS_DEV"
kill %1
```

**Invariant flag:** INV-09, INV-11.

---

### Task 6.3 — Okta System Log Walkthrough (Manual — Engineer-Executed)

**Description:** This is a human-executed learning task. No CC prompt. The engineer navigates the Okta admin console and identifies specific log events.

> **Engineer executes the following after all prior sessions are complete:**

1. Navigate to Okta Admin Console → Reports → System Log
2. Identify and record timestamps for:
   - A successful login event (`user.session.start`)
   - A token issuance event (`app.oauth2.token.grant.access_token`)
   - A scope grant event
   - A failed authentication attempt (use an expired token or wrong credentials)
3. Filter by `alice@example.com` and identify her login history
4. Filter by `admin@example.com` and confirm admin group assignment in events
5. Record observations in a file: `okta-identity-lab/docs/system-log-walkthrough.md`

**Verification:** The `docs/system-log-walkthrough.md` file exists with at least 4 event types documented and timestamps recorded.

**Test cases:**
| Case | Scenario | Expected |
|---|---|---|
| TC-1 | Login event visible | user.session.start event found for both test users |
| TC-2 | Token issuance visible | access_token grant events present |
| TC-3 | Failed auth visible | Event logged when expired token or bad credentials used |
| TC-4 | Walkthrough document created | docs/system-log-walkthrough.md exists and is non-empty |

**Verification command:**
```bash
[ -f okta-identity-lab/docs/system-log-walkthrough.md ] && wc -l okta-identity-lab/docs/system-log-walkthrough.md || echo "Walkthrough doc missing"
```

**Invariant flag:** None. Learning/observability task.

---

## Session 7 — System Sign-Off

**Session goal:** All 9 Definition of Done scenarios from the requirements brief pass. All 28 invariants are verified end-to-end. VERIFICATION_CHECKLIST.md is complete with documented sign-off.

**Integration check:**
This session IS the integration check. See VERIFICATION_CHECKLIST.md produced at end.

---

### Task 7.1 — Full System Sign-Off

**Description:** Run all Definition of Done scenarios from the requirements brief (Section 2.2). Deliberately break each auth check. Complete VERIFICATION_CHECKLIST.md.

> **This is a human-executed task. CC is not used.**

**Definition of Done scenarios (from requirements brief Section 2.2):**

| Scenario | Steps | Expected |
|---|---|---|
| Log in via frontend | Start frontend, click Login, complete Okta login | Tokens stored, user info displayed on Dashboard |
| Inspect JWT in UI | After login, open Token Inspector | Decoded JWT shows iss, exp, scp, groups claims |
| Call API A (authorized) | API Tester → GET /api/users with alice's token | 200 with user list |
| Call API A (expired token) | Use expired token (reduce token lifetime to 5 min and wait) | 401 Unauthorized |
| Call API B (no admin scope) | API Tester → GET /api/config with alice's token | 403 Forbidden |
| Grant admin scope, re-login | Add admin@example.com to api-b-admins group, re-login | API B returns 200 |
| JWKS key rotation | Rotate keys in Okta console, POST /dev/invalidate-jwks-cache, make API call | API continues to validate new tokens |
| M2M: API A calls API B | GET /api/internal/pull-analytics | Client credentials flow succeeds, analytics returned |
| Okta System Log review | Navigate System Log | All auth events visible |

**Deliberate breakage tests:**

| Break | Method | Expected |
|---|---|---|
| Remove api-a:read scope from alice | Okta admin: remove scope grant | GET /api/users returns 403 |
| Expire access token | Reduce token lifetime to 1 min, wait | API call returns 401 |
| Remove alice from api-a-users group | Okta admin console | Scope no longer granted at login |
| Use M2M token on admin endpoint | Manually decode M2M token, note scp | GET /api/config returns 403 |
| Submit wrong Origin header | curl with wrong Origin | No CORS header returned |

**Verification command:**
```bash
# Generate VERIFICATION_CHECKLIST.md from invariant list
cat > okta-identity-lab/VERIFICATION_CHECKLIST.md << 'EOF'
# VERIFICATION_CHECKLIST.md — Okta Identity Lab System Sign-Off

Date: 
Engineer: 

| Invariant | Description | Result |
|---|---|---|
| INV-01 | PKCE code_verifier never transmitted to server | [ ] PASS / [ ] FAIL |
| INV-02 | Access tokens in memory only | [ ] PASS / [ ] FAIL |
| INV-03 | Refresh tokens in sessionStorage or httpOnly cookie | [ ] PASS / [ ] FAIL |
| INV-04 | Silent refresh before rendering protected UI on page load | [ ] PASS / [ ] FAIL |
| INV-05 | Proactive silent refresh 60s before expiry | [ ] PASS / [ ] FAIL |
| INV-06 | Failed silent refresh triggers logout redirect | [ ] PASS / [ ] FAIL |
| INV-07 | Every protected endpoint validates JWT signature via JWKS | [ ] PASS / [ ] FAIL |
| INV-08 | JWKS keys cached in memory — no per-request fetch | [ ] PASS / [ ] FAIL |
| INV-09 | Cache invalidated and re-fetched on kid mismatch | [ ] PASS / [ ] FAIL |
| INV-10 | 60-second clock leeway on JWT validation | [ ] PASS / [ ] FAIL |
| INV-11 | JWKS cache emits observable logs on all state transitions | [ ] PASS / [ ] FAIL |
| INV-12 | Missing scope returns 403, not 401 | [ ] PASS / [ ] FAIL |
| INV-13 | api-b:admin scope alone insufficient for admin routes — group check required | [ ] PASS / [ ] FAIL |
| INV-14 | Fine-grained ownership check on GET /api/users/:id | [ ] PASS / [ ] FAIL |
| INV-15 | Every API B protected request appended to audit_log | [ ] PASS / [ ] FAIL |
| INV-16 | All protected endpoints return 401 on missing/invalid/expired token | [ ] PASS / [ ] FAIL |
| INV-17 | M2M token request explicitly includes scope=api-b:read | [ ] PASS / [ ] FAIL |
| INV-18 | M2M tokens validated by same JWKS middleware — no bypass | [ ] PASS / [ ] FAIL |
| INV-19 | M2M client secret sourced from env vars only — never in code/logs/responses | [ ] PASS / [ ] FAIL |
| INV-20 | Both APIs reject cross-origin requests not from http://localhost:3000 | [ ] PASS / [ ] FAIL |
| INV-21 | No stack traces or internal details in API response bodies | [ ] PASS / [ ] FAIL |
| INV-22 | All Okta credentials from env vars — never hardcoded | [ ] PASS / [ ] FAIL |
| INV-23 | Both APIs log every auth decision as structured JSON | [ ] PASS / [ ] FAIL |
| INV-24 | Every protected endpoint has a corresponding API Tester button | [ ] PASS / [ ] FAIL |
| INV-25 | Token Inspector displays all required fields including live countdown | [ ] PASS / [ ] FAIL |
| INV-26 | Token Refresh Demo shows before and after states simultaneously | [ ] PASS / [ ] FAIL |
| INV-27 | API Tester visually distinguishes 401/403 from 200 | [ ] PASS / [ ] FAIL |
| INV-28 | Frontend rejects callback if state parameter does not match | [ ] PASS / [ ] FAIL |

## Definition of Done Scenarios

| Scenario | Result |
|---|---|
| Log in via frontend | [ ] PASS / [ ] FAIL |
| Inspect JWT in UI | [ ] PASS / [ ] FAIL |
| Call API A (authorized) | [ ] PASS / [ ] FAIL |
| Call API A (expired token) | [ ] PASS / [ ] FAIL |
| Call API B (no admin scope) | [ ] PASS / [ ] FAIL |
| Grant admin scope, re-login | [ ] PASS / [ ] FAIL |
| JWKS key rotation | [ ] PASS / [ ] FAIL |
| M2M: API A calls API B | [ ] PASS / [ ] FAIL |
| Okta System Log review | [ ] PASS / [ ] FAIL |

## Engineer Sign-Off

All invariants and DoD scenarios verified end-to-end.

Signed: 
Date: 
EOF
echo "VERIFICATION_CHECKLIST.md created"
```

**Invariant flag:** All 28 invariants. This is the system-level verification pass.

---

## Git Branch Conventions

| Session | Branch Name |
|---|---|
| Session 1 | `session/1-scaffold-okta-setup` |
| Session 2 | `session/2-api-a-core-auth` |
| Session 3 | `session/3-api-b-admin-auth` |
| Session 4 | `session/4-frontend-spa` |
| Session 5 | `session/5-m2m-flow` |
| Session 6 | `session/6-enterprise-hardening` |
| Session 7 | `session/7-system-sign-off` |

One branch per session. One commit per task. PR to `main` only after session integration check and engineer sign-off.

---

## Commit Message Conventions

```
[Task N.N] <imperative description>

e.g.
[Task 1.1] Initialise repository scaffold and directory structure
[Task 2.2] Implement JWKS cache with TTL, rotation handling, and observable logging
[Task 4.3] Implement Token Inspector Panel with live expiry countdown
```

---

*EXECUTION_PLAN.md — Okta Identity Lab v1.0 — Draft*
*Produced for PBVI Phase 3. Awaiting engineer review before Phase 4 Design Gate.*
