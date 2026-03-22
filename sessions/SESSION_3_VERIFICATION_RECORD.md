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

### CC Challenge Output
<!-- To be filled after CC challenge -->

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
<!-- To be filled after CC challenge -->

### Verification Verdict
[ ] All planned cases passed
[ ] CC challenge reviewed
[x] Code review complete (if invariant-touching)
[ ] Scope decisions documented

**Status:** Tests PASS — awaiting CC challenge

---

## Task 3.3 — API B Route Handlers

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 3

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | GET /health — no token | 200 | |
| TC-2 | GET /api/analytics/summary — no token | 401 | |
| TC-3 | GET /api/analytics/summary — api-b:read scope | 200 with analytics data | |
| TC-4 | GET /api/config — api-b:admin scope, NOT in api-b-admins group | 403 "insufficient_privileges" | |
| TC-5 | GET /api/config — in api-b-admins group, missing api-b:admin scope | 403 "insufficient_scope" | |
| TC-6 | GET /api/config — admin token (scope + group) | 200 with config | |
| TC-7 | GET /api/audit-log — admin token | 200 with audit entries | |
| TC-8 | POST /api/config — admin token, valid body | 200 with updated config | |
| TC-9 | After multiple requests to protected routes, audit_log grows | GET /api/audit-log shows all entries | |

### Prediction Statement
<!-- LEAVE BLANK — engineer writes predictions before running verification commands -->

### CC Challenge Output
<!-- Paste CC's response to: 'What did you not test in this task?'
For each item: accepted (added case) / rejected (reason). -->

### Code Review
**Invariants touched:** INV-12, INV-13, INV-15, INV-16, INV-20, INV-21, INV-23

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-12 | Missing scope returns 403 not 401 — `require_scope` raises `HTTPException(403)` | `api-b/app/auth/__init__.py` — require_scope exception code | |
| INV-13 | Admin routes (`GET /api/config`, `POST /api/config`, `GET /api/audit-log`) have BOTH `require_scope("api-b:admin")` AND `require_group("api-b-admins")` in their `Depends()` chain | `api-b/app/routes/config.py` and `audit.py` — route decorators | |
| INV-13 | `require_scope` executes BEFORE `require_group` — a missing scope returns "insufficient_scope", not "insufficient_privileges" | Dependency ordering in route `Depends()` declarations | |
| INV-15 | Audit entry written on BOTH pass and fail outcomes — verified by TC-9 showing log growth across multiple request types | `api-b/app/auth/__init__.py` — `_log_auth_decision` called on all paths | |
| INV-16 | Missing/invalid/expired tokens return 401 — not 403 or 500 | All protected routes — verify auth middleware runs before any route logic | |
| INV-20 | `allow_origins` is `["http://localhost:3000"]` — not `["*"]` | `api-b/app/main.py` — CORS middleware config | |
| INV-21 | Global exception handler present, returns `{"error": "...", "message": "..."}` with no stack trace | `api-b/app/main.py` — exception handler | |
| INV-23 | Auth decision log includes route path, not just scope name, for every entry | `api-b/app/auth/__init__.py` — `_log_auth_decision` call sites in route handlers | |

### Scope Decisions
<!-- What was accepted as out of scope and why. Cannot be left blank for deliverables. -->

### Verification Verdict
[ ] All planned cases passed
[ ] CC challenge reviewed
[ ] Code review complete (if invariant-touching)
[ ] Scope decisions documented

**Status:**

---

## Task 3.4 — API B Startup Script

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 3

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | run.sh starts on port 3002 | Uvicorn startup complete | |
| TC-2 | /health returns 200 | curl confirms | |

### Prediction Statement
<!-- LEAVE BLANK — engineer writes predictions before running verification commands -->

### CC Challenge Output
<!-- Paste CC's response to: 'What did you not test in this task?'
For each item: accepted (added case) / rejected (reason). -->

### Code Review
**Invariants touched:** None — wiring task only.

### Scope Decisions
<!-- What was accepted as out of scope and why. Cannot be left blank for deliverables. -->

### Verification Verdict
[ ] All planned cases passed
[ ] CC challenge reviewed
[ ] Code review complete (if invariant-touching)
[ ] Scope decisions documented

**Status:**

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

**Prediction:**
<!-- LEAVE BLANK — engineer writes prediction before running -->

**Result:**
<!-- LEAVE BLANK -->

**Verdict:** [ ] PASSED
