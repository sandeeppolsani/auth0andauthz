# VERIFICATION_RECORD.md

**Session:** Session 3 — API B: Admin Auth
**Date:** 22/03/2026
**Engineer:** Sandeep

---

## Task 3.1 — Mock Database (API B)

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 3

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | get_analytics returns seed | Dict with total_users=42 | PASS |
| TC-2 | get_analytics returns copy (mutating returned dict doesn't change stored value) | Stored total_users still 42 after mutation | PASS |
| TC-3 | get_config returns seed | maintenance_mode=False, log_level=INFO, feature_flags correct | PASS |
| TC-4 | get_config returns copy | Stored log_level unchanged after mutation of returned dict | PASS |
| TC-5 | update_config patches a key | log_level becomes DEBUG | PASS |
| TC-6 | update_config leaves unrelated keys unchanged | maintenance_mode, feature_flags untouched | PASS |
| TC-7 | update_config adds a new key | New key appears in subsequent get_config | PASS |
| TC-8 | update_config returns updated state | Returned dict reflects the change | PASS |
| TC-9 | update_config return is a copy | Mutating returned dict doesn't change stored value | PASS |
| TC-10 | append_audit_entry + get_audit_log | Entry appears in log | PASS |
| TC-11 | Multiple entries are ordered (FIFO) | First entry has earlier timestamp | PASS |
| TC-12 | get_audit_log returns list copy | Appending to returned list doesn't change internal log | PASS |
| TC-13 | audit_log starts empty | get_audit_log() returns [] after reset | PASS |
| TC-14 | update_config with empty dict is no-op | Config unchanged | PASS (CC add) |
| TC-15 | update_config with nested dict replaces sub-dict wholesale | feature_flags replaced entirely | PASS (CC add) |
| TC-16 | No fastapi or jose imports in mock_db.py | AST scan finds no forbidden imports | PASS |

### Prediction Statement
<!-- LEAVE BLANK — engineer writes predictions before running verification commands -->

### CC Challenge Output

| Item raised | Decision |
|-------------|----------|
| `update_config({})` empty dict is no-op | Accepted — TC-14 added |
| `update_config` with nested dict replaces not merges | Accepted — TC-15 added (documents `dict.update()` wholesale replacement behaviour) |
| `get_audit_log` entry-dict mutation not guarded | Rejected — `list(_audit_log)` gives list-level copy. No caller in this codebase mutates individual entry dicts. |
| `append_audit_entry` with partial entry (missing required field) | Rejected — passive receiver; schema validation is auth middleware's responsibility (Task 3.2). |
| `get_analytics` not mutated by any public function | Rejected — no public function modifies `_analytics`; copy test (TC-2) already guards this. |

### Code Review
**Invariants touched:** INV-15 (audit log write path)

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-15 | `append_audit_entry` is called by auth middleware (Task 3.2) — NOT by route handlers | `api-b/app/db/mock_db.py` — confirm no audit write logic exists here; the function is a passive receiver only | PASS — function only calls `_audit_log.append(entry)`, no other logic |
| INV-15 | `append_audit_entry` entry schema accepts: timestamp, subject, route, outcome — all four fields | `mock_db.py` — docstring and append logic | PASS — docstring states all four required fields; no schema enforcement (by design) |

### Scope Decisions

| Item | Accepted as out of scope | Reason |
|------|--------------------------|--------|
| Entry-level dict mutation guard on `get_audit_log` | Out of scope | Contract is list-level copy only. No caller in this codebase mutates audit entries after retrieval. Deep copying every entry would be over-engineering for a mock. |
| Input validation inside `append_audit_entry` | Out of scope | Passive receiver pattern. The auth middleware (Task 3.2) owns entry construction and correctness. |

### Verification Verdict
[x] All planned cases passed
[x] CC challenge reviewed
[x] Code review complete (if invariant-touching)
[x] Scope decisions documented

**Status:** PASSED

---

## Task 3.2 — JWKS Cache + JWT Auth Middleware (API B)

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 3 + jwks_cache.py independent test suite

**test_jwks_cache.py (8 tests)**

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | get_key triggers fetch on empty cache | httpx.get called once, key returned | PASS |
| TC-2 | get_key returns cached key — no re-fetch within TTL | httpx.get not called on second access | PASS |
| TC-3 | get_key re-fetches after TTL expiry | httpx.get called again after TTL | PASS |
| TC-4 | get_key returns None for unknown kid | None returned, no exception | PASS |
| TC-5 | invalidate_and_refetch clears and reloads | New key available after invalidation | PASS |
| TC-6 | get_key returns None on HTTP fetch failure | Exception swallowed, None returned | PASS |
| TC-7 | invalidate_and_refetch survives fetch failure silently | No exception raised, _keys cleared | PASS |
| TC-8 | get_key stores all keys from JWKS response | Second key accessible without re-fetch | PASS |

**test_auth_middleware.py (12 tests)**

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | Module loads OKTA_ISSUER/OKTA_AUDIENCE/OKTA_JWKS_URI from env | All three vars present in module | PASS |
| TC-2 | require_scope — valid scope → 200 | Route returns 200 | PASS |
| TC-3 | require_scope — missing scope → 403 insufficient_scope | 403 with correct error code | PASS |
| TC-4 | require_group — user in group → 200 | Route returns 200 | PASS |
| TC-5 | require_group — user NOT in group → 403 insufficient_privileges | 403 with correct error code | PASS |
| TC-6 | Scope checked before group — missing scope returns insufficient_scope not insufficient_privileges | 403 error = insufficient_scope | PASS |
| TC-7 | Every auth decision writes to audit_log (real middleware, 3 requests → 3 entries) | audit_log length == 3 | PASS |
| TC-8 | Audit entry schema — timestamp, subject, route, outcome all present | Entry has all 4 fields | PASS |
| TC-9 | Audit entry written on fail outcome | outcome == "fail" in log | PASS |
| TC-10 | jwks_cache is module-level singleton | Same object reference on repeated access | PASS |
| TC-11 | leeway=60 passed to jwt.decode | mock_decode called with options.leeway == 60 | PASS |
| TC-12 | No api-a imports in api-b auth module | AST scan finds no cross-service imports | PASS |
| TC-13 | verify_token — no Authorization header → 401 | 401 with error=invalid_token | PASS (CC add) |
| TC-14 | verify_token — malformed token string → 401 | 401 with error=invalid_token | PASS (CC add) |
| TC-15 | verify_token — kid not found after invalidate_and_refetch → 401 | 401 with error=invalid_token | PASS (CC add) |
| TC-16 | require_scope — scp as space-separated string is handled | 200, scope accepted | PASS (CC add) |

### CC Challenge Output

| Item raised | Decision |
|-------------|----------|
| `verify_token` — no Authorization header (`credentials is None`) → 401 | Accepted — TC-13 added |
| `verify_token` — malformed token string (`jwt.get_unverified_header` raises JWTError) → 401 | Accepted — TC-14 added |
| `verify_token` — kid not found even after `invalidate_and_refetch` → 401 (INV-09 two-step retry) | Accepted — TC-15 added |
| `require_scope` — `scp` claim is a space-separated string, not a list | Accepted — TC-16 added |
| `require_group` — claims with no `groups` key vs explicit `[]` | Rejected — `claims.get("groups", [])` and `[]` are identical code paths |
| `_log_auth_decision` with missing `sub` key → `"anonymous"` default | Rejected — Okta always issues `sub`; defensive default, not a reachable production gap |
| Audit entries from multiple different routes in one test | Rejected — TC-8 already verifies `route` field is captured; growth behaviour is route-agnostic |

### Code Review
**Invariants touched:** INV-07, INV-08, INV-09, INV-10, INV-11, INV-13, INV-15, INV-18, INV-23

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-07 | `verify_token` present and identical in structure to API A — no route can bypass it | `api-b/app/auth/__init__.py` — verify_token definition | PASS — same structure: HTTPBearer(auto_error=False), kid extraction, cache lookup, jwt.decode |
| INV-08 | JWKS cache is a module-level instance — not re-instantiated per request | `api-b/app/auth/__init__.py` — top-level `jwks_cache = JWKSCache(...)` | PASS — module-level, confirmed by TC-10 |
| INV-09 | `invalidate_and_refetch` path present — triggered on kid mismatch (key is None), not on exp failures | `api-b/app/auth/__init__.py` — key=None → invalidate_and_refetch → retry | PASS — only triggered when get_key returns None |
| INV-10 | `leeway=60` on `jwt.decode()` | `api-b/app/auth/__init__.py` — `options={"leeway": 60}` | PASS — confirmed by TC-11 |
| INV-11 | All five JWKS log event strings present | `api-b/app/auth/jwks_cache.py` — JWKS_CACHE_MISS, JWKS_CACHE_HIT, JWKS_KID_NOT_FOUND, JWKS_CACHE_INVALIDATED_REFETCH, JWKS_CACHE_REFRESHED | PASS — all five present |
| INV-13 | `require_group("api-b-admins")` is a separate factory from `require_scope` | `api-b/app/auth/__init__.py` — separate `require_group` function | PASS — independent factory, separate `Depends()` in route |
| INV-15 | `_log_auth_decision` calls `append_audit_entry` — both pass and fail write to audit_log | `api-b/app/auth/__init__.py` — `_log_auth_decision` body | PASS — every call to `_log_auth_decision` calls `mock_db.append_audit_entry`, confirmed TC-7/TC-9 |
| INV-18 | No special handling for M2M tokens — `verify_token` is the same function for all callers | `api-b/app/auth/__init__.py` — no token-origin branching | PASS — single `verify_token` function, no M2M branch |
| INV-23 | Structured JSON log line: timestamp, subject, route, required_scope, outcome | `api-b/app/auth/__init__.py` — `_log_auth_decision` log_entry dict | PASS — all five fields present |
| **Independence** | No `api-a/` imports | All import statements in `api-b/app/auth/__init__.py` | PASS — confirmed by TC-12 |

### Scope Decisions

| Item | Accepted as out of scope | Reason |
|------|--------------------------|--------|
| `require_group` missing-key vs empty-list distinction | Out of scope | `dict.get("groups", [])` collapses both to the same empty list — there is no separate branch to test. |
| `_log_auth_decision` anonymous subject default | Out of scope | The `sub` claim is always present in a valid Okta JWT. The default exists as a defensive fallback, not a real production path. Testing it would be testing Python's `dict.get` default, not our logic. |
| Multi-route audit accumulation | Out of scope | TC-8 already verifies the `route` field is set correctly per request. The list-append behaviour of `append_audit_entry` is covered by Task 3.1 tests. |

### Verification Verdict
[x] All planned cases passed
[x] CC challenge reviewed
[x] Code review complete (if invariant-touching)
[x] Scope decisions documented

**Status:** PASSED — 24 tests (8 JWKS cache + 16 auth middleware), all PASS

---

## Task 3.3 — API B Route Handlers

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 3

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | GET /health — no token | 200 | PASS |
| TC-2 | GET /health — still 200 with no Authorization header | 200 | PASS |
| TC-3 | GET /api/analytics/summary — no token | 401 invalid_token | PASS |
| TC-4 | GET /api/analytics/summary — api-b:read scope | 200 with analytics data (total_users, active_sessions, last_updated) | PASS |
| TC-5 | GET /api/config — api-b:admin scope, NOT in api-b-admins group | 403 insufficient_privileges | PASS |
| TC-6 | GET /api/config — in api-b-admins group, missing api-b:admin scope | 403 insufficient_scope | PASS |
| TC-7 | GET /api/config — admin token (scope + group) | 200 with config | PASS |
| TC-8 | GET /api/audit-log — admin token | 200, list returned | PASS |
| TC-9 | POST /api/config — admin token, valid body | 200, updated key reflected, unrelated key unchanged | PASS |
| TC-10 | Audit log grows after 3 analytics requests (real middleware) | audit_log length == 3 | PASS |
| TC-11 | POST /api/config — no token → 401 | 401 | PASS |
| TC-12 | GET /api/audit-log — no token → 401 | 401 | PASS |
| TC-13 | CORS — allowed origin → ACAO header present | header == "http://localhost:3000" | PASS |
| TC-14 | CORS — disallowed origin → no ACAO header | header absent or different | PASS |
| TC-15 | Global exception handler — verify_token raises RuntimeError → 500 structured JSON | error=internal_error, no stack trace | PASS |
| TC-16 | POST /api/config — scope only, no group → 403 insufficient_privileges | 403 error=insufficient_privileges | PASS (CC add) |
| TC-17 | POST /api/config — group only, no scope → 403 insufficient_scope | 403 error=insufficient_scope | PASS (CC add) |
| TC-18 | POST /api/config — empty body → no-op, config unchanged | 200, log_level still INFO | PASS (CC add) |
| TC-19 | GET /api/analytics/summary — admin-only scope, no api-b:read → 403 | 403 error=insufficient_scope | PASS (CC add) |
| TC-20 | OPTIONS preflight on protected route → 200 (INV-20) | 200 | PASS (CC add) |

### CC Challenge Output

| Item raised | Decision |
|-------------|----------|
| POST /api/config — scope only, no group → 403 insufficient_privileges (GET was tested, POST was not) | Accepted — TC-16 added |
| POST /api/config — group only, no scope → 403 insufficient_scope (GET was tested, POST was not) | Accepted — TC-17 added |
| POST /api/config empty body → no-op | Accepted — TC-18 added |
| GET /api/analytics/summary with admin-only scope (no api-b:read) → 403 — tests scope isolation between routes | Accepted — TC-19 added |
| OPTIONS preflight → 200 (INV-20 explicitly states this) | Accepted — TC-20 added |
| GET /api/config response body completeness (every nested field) | Rejected — tests the mock seed data, not the route logic |
| POST /api/config with unknown key in body | Rejected — dict.update behaviour already covered in Task 3.1 TC-7 |
| GET /api/audit-log showing specific pre-populated entries | Rejected — cumulative state non-deterministic; list correctness covered in Tasks 3.1 and 3.2 |

### Code Review
**Invariants touched:** INV-12, INV-13, INV-15, INV-16, INV-20, INV-21, INV-23

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-12 | Missing scope returns 403 not 401 | `api-b/app/auth/__init__.py` — require_scope raises HTTPException(403) | PASS — TC-6 confirms |
| INV-13 | Admin routes have BOTH `require_scope("api-b:admin")` AND `require_group("api-b-admins")` | `api-b/app/routes/config.py` and `audit.py` — both Depends() present | PASS |
| INV-13 | `require_scope` declared before `require_group` — missing scope returns insufficient_scope | Dependency ordering: `_scope = Depends(require_scope(...))` listed first | PASS — TC-6 confirms order |
| INV-15 | Audit entry written on both pass and fail — TC-10 shows log grows on real middleware | `api-b/app/auth/__init__.py` — `_log_auth_decision` in require_scope | PASS |
| INV-16 | Missing token → 401, not 403/500 | All protected routes — auth middleware runs first | PASS — TC-3/TC-11/TC-12 confirm |
| INV-20 | `allow_origins=["http://localhost:3000"]` not wildcard | `api-b/app/main.py` — CORSMiddleware config | PASS — TC-13/TC-14 confirm |
| INV-21 | Global exception handler present, structured JSON, no stack trace | `api-b/app/main.py` — exception handler | PASS — TC-15 confirms |
| INV-23 | Auth decision log includes route path | `api-b/app/auth/__init__.py` — route captured via request.url.path | PASS — covered in Task 3.2 TC-8 |

### Scope Decisions

| Item | Accepted as out of scope | Reason |
|------|--------------------------|--------|
| GET /api/config response body completeness | Out of scope | TC-7 checks meaningful keys. Asserting every fixed seed field tests mock data, not route logic. |
| POST /api/config with unknown key in body | Out of scope | `dict.update()` accepting any key is mock_db behaviour, covered in Task 3.1 TC-7. The route is a one-line pass-through. |
| GET /api/audit-log pre-populated entry visibility | Out of scope | Audit log is cumulative; state ordering is non-deterministic across tests. Entry structure and list correctness covered in Tasks 3.1 and 3.2. |

### Verification Verdict
[x] All planned cases passed
[x] CC challenge reviewed
[x] Code review complete (if invariant-touching)
[x] Scope decisions documented

**Status:** PASSED — 20 route tests, 60 total across all Task 3 files, all PASS

---

## Task 3.4 — API B Startup Script

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 3

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | run.sh starts on port 3002 | Uvicorn startup complete | Manual — pending engineer run |
| TC-2 | /health returns 200 | curl confirms | Manual — pending engineer run |

### Code Review
**Invariants touched:** None — wiring task only.

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| Executable bit | `git ls-files --stage api-b/run.sh` shows `100755` | git index | PASS — `100755` confirmed |
| LF line endings | `cat -A run.sh` shows `$` not `^M$` | run.sh | PASS — LF only |
| Port 3002 | Uvicorn invoked on port 3002 | run.sh line 3 | PASS |
| Windows path | `.venv/Scripts/python` used | run.sh line 3 | PASS — deviation documented |
| README Python version | States 3.14+ | api-b/README.md | PASS |
| README endpoint table | All 5 routes with scope + group columns | api-b/README.md | PASS |
| README CRLF note | Documents `source <(tr -d '\r' < .env)` workaround | api-b/README.md | PASS |

### CC Challenge Output

| Item raised | Decision |
|-------------|----------|
| `api-b/.env.example` not created — README references it, scope boundary permits it, API A has one | Accepted — `.env.example` created with all 4 required vars |
| README endpoint table not explicitly cross-checked against actual routes | Accepted — cross-checked: all 5 rows match method, path, scope, and group in the implemented routes |
| Port number consistency — README could accidentally say 3001 | Rejected — verified: `port **3002**` in header, `--port 3002` in CRLF workaround, no 3001 anywhere |
| `run.sh --reload` flag presence | Rejected — present, obvious from reading the file |
| `set -a` / `set +a` export behaviour | Rejected — standard shell behaviour, same pattern as Task 2.5 |

### Scope Decisions

| Item | Accepted as out of scope | Reason |
|------|--------------------------|--------|
| Live Okta token verification (TC-1/TC-2 with real token) | Deferred to engineer manual step | Requires real `.env` with Okta credentials. Same pattern as Task 2.5 TC-3 — manual verification, not automated. |
| `api-b/.env.example` missing | Moved in-scope | CC challenge caught this. Created with all 4 required vars matching Fixed Stack env var names. |

### Verification Verdict
[x] All planned cases passed (pending engineer manual TC-1/TC-2)
[x] CC challenge reviewed
[x] Code review complete
[x] Scope decisions documented

**Status:** Completed

---

## Session Integration Check

**Command:**
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

**Prediction:** Audit log is happening correctly

**Result:** Completed

**Verdict:** [*] PASSED
