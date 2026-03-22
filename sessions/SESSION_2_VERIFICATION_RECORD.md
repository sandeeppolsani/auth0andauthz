# VERIFICATION_RECORD.md

**Session:** Session 2 — API A: Core Auth
**Date:** 
**Engineer:** sandeeppolsani

---

## Task 2.1 — Mock Database (API A)

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 2

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | 3 seed records at import | len == 3 | PASS |
| TC-2 | get_user_by_email() hit | Returns correct record | PASS |
| TC-3 | get_user_by_email() miss | Returns None | PASS |
| TC-4 | create_user() appends and returns | Record in store, count +1 | PASS |
| TC-5 | update_user() hit | Returns updated record | PASS |
| TC-6 | update_user() miss | Returns None | PASS |
| TC-7 | get_all_users() returns a copy | pop() on result does not mutate store | PASS |
| TC-8 | create_user() rejects duplicate email | Raises ValueError | PASS |
| TC-9 | update_user() ignores email key | Original email unchanged, other fields updated | PASS |
| TC-10 | Store mutation reflected in subsequent read | get_user_by_email() returns updated value | PASS |

### Prediction Statement
Implement the in-memory Python dict database for API A. Seed three user records. Expose             
  read/write functions used by route handlers. In api-a/app/db/mock_db.py, implement the in-memory mock          
  database for API A

### CC Challenge Output
1. get_all_users() returns a direct reference to _users                                                        
  Callers can mutate the list in-place (e.g. get_all_users().pop()) without going through create_user() or
  update_user(), bypassing the intended interface.                                                                 
  → Accepted — add case
                                                                                                                 
  ---
  2. create_user() does not guard against duplicate emails
  Calling create_user() with an already-existing email silently appends a duplicate. get_user_by_email() would   
  then return only the first match, leaving the duplicate unreachable.
  → Accepted — add case

  ---
  3. update_user() can overwrite the email key
  user.update(updates) applies any key in updates, including email. Passing {"email": "new@example.com"} would   
  corrupt the record's lookup key — the original email would no longer resolve.
  → Accepted — add case

  ---
  4. Store mutation not confirmed via subsequent read
  I tested update_user() returns the updated record but never called get_user_by_email() afterwards to confirm   
  the mutation is reflected in the store.
  → Accepted — add case

  ---
  5. Exact function signatures not read back from file
  Behavior was tested but the written annotations (list[dict], dict | None) were not read back from the file to  
  confirm they match the spec exactly.
  → Rejected — the file was written directly from spec and all behavioral tests passed against it. Read-back     
  would be redundant.

  ---
  6. _users initialised at import time
  → Rejected — Python module-level assignment is always evaluated at import. No test needed.

  ---

### Code Review
**Invariants touched:** INV-14 (fine-grained auth joins on email field)

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-14 | `email` field name is consistent — matches the `token.sub` comparison in Task 2.4 route handler | `api-a/app/db/mock_db.py` seed data and `get_user_by_email` signature | PASS get_user_by_email is returning the email |
| INV-14 | `_users` list is not exposed directly — only through the four functions | `mock_db.py` module interface | PASS _users is private and restricted to access directly |

### Scope Decisions
  ---                                                                                                              
  1. get_all_users() returns a shallow copy, not a deep copy
  list(_users) copies the list structure but the dict objects inside are still references. A caller could do     
  get_all_users()[0]['name'] = 'x' and mutate the original record directly. Accepted — the spec concern was
  callers bypassing create_user() / update_user() by appending or popping from the returned list. Shallow copy
  addresses that. Deep copying every record on every call would be over-engineering for a learning lab mock DB.  

  ---
  2. No persistence across process restarts
  _users is module-level state — it resets every time the server restarts. Accepted — the spec explicitly states 
  "The data store is a Python dict — not SQLite, not a file, not any external DB." In-memory only is the stated  
  requirement, not a limitation.

### Verification Verdict
[x] All planned cases passed
[x] CC challenge reviewed
[x] Code review complete (if invariant-touching)
[x] Scope decisions documented

**Status:**
Done
---

## Task 2.2 — JWKS Cache (API A)

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 2

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | Cold start — fetches on first get_key call | Log shows JWKS_CACHE_MISS then JWKS_CACHE_REFRESHED | PASS |
| TC-2 | Second call within TTL — cache hit | Log shows JWKS_CACHE_HIT, no HTTP request made | PASS |
| TC-3 | Expired cache — re-fetches | After TTL, next get_key triggers JWKS_CACHE_MISS and re-fetch | PASS |
| TC-4 | Unknown kid after fetch — returns None | Log shows JWKS_KID_NOT_FOUND | PASS |
| TC-5 | invalidate_and_refetch — logs correctly | Log shows JWKS_CACHE_INVALIDATED_REFETCH then JWKS_CACHE_REFRESHED | PASS |
| TC-6 | get_key returns None on HTTP failure | No exception raised — None returned | PASS |
| TC-7 | JWKS_CACHE_REFRESHED — key count correct | 2 keys stored, keyed by kid | PASS |
| TC-8 | Structured JSON log format | All lines valid JSON with timestamp + event; kid and key_count present where applicable | PASS |
| TC-9 | `timeout=10` passed to `httpx.get` | `call_args` confirms `timeout=10` kwarg | PASS |
| TC-10 | Second valid `kid` lookup | `get_key('kid-002')` returns correct key dict | PASS |
| TC-11 | `invalidate_and_refetch` failure — subsequent `get_key` returns None | `_keys` stays empty; next call returns None | PASS |
| TC-12 | Malformed response (no `keys` field) — `get_key` returns None | `KeyError` caught; None returned | PASS |

### Prediction Statement
JWKSCache should fetch from Okta JWKS URI on cold start and cache the keys. Subsequent calls within TTL should hit the cache without HTTP requests. Expired cache should trigger a re-fetch. Unknown kid should return None. invalidate_and_refetch should clear cache and re-fetch immediately. All transitions should emit structured JSON log lines.

### CC Challenge Output
  1. timeout=10 not verified on httpx.get call
  httpx.get was mocked — timeout=10 argument never asserted as actually passed.
  → Accepted — add case (TC-9)

  ---
  2. Second valid kid lookup never tested
  TC-7 confirmed both kids stored but get_key('kid-002') never called.
  → Accepted — add case (TC-10)

  ---
  3. invalidate_and_refetch failure — subsequent get_key state
  _keys stays empty after failed refetch; next get_key tries again, fails, returns None. Not tested.
  → Accepted — add case (TC-11)

  ---
  4. _fetch() with malformed response body
  HTTP 200 but no "keys" field raises KeyError — caught by get_key outer try/except, returns None.
  → Accepted — add case (TC-12)

  ---
  5. Thread safety
  Two concurrent cold-cache requests could both trigger _fetch() simultaneously. No locking.
  → Rejected — not in spec; FastAPI/uvicorn runs single event loop thread. Learning lab, not production.

  ---
  6. Logger name and propagate=False
  Internal config details with no observable effect on tested behaviour.
  → Rejected — not observable from outside the module.

### Code Review
**Invariants touched:** INV-08, INV-09, INV-10

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-08 | `get_key` does NOT make an HTTP call on every invocation — only on cold start, TTL expiry, or explicit invalidation | `jwks_cache.py` — `get_key` method body | PASS — HTTP only called when `_keys` empty or age > ttl_seconds |
| INV-08 | Default TTL is 600 seconds | `JWKSCache.__init__` — `ttl_seconds=600` default | PASS — default confirmed |
| INV-09 | `invalidate_and_refetch` method exists and clears cache before re-fetching | `jwks_cache.py` — `invalidate_and_refetch` | PASS — sets `_keys={}`, `_fetched_at=0.0`, then calls `_fetch()` |
| INV-10 | All five log event strings present: `JWKS_CACHE_MISS`, `JWKS_CACHE_HIT`, `JWKS_KID_NOT_FOUND`, `JWKS_CACHE_INVALIDATED_REFETCH`, `JWKS_CACHE_REFRESHED` | `jwks_cache.py` — logging calls | PASS — all five confirmed in test output |
| INV-10 | Log lines include: timestamp, event, key_count where applicable, kid where applicable | `jwks_cache.py` — `_JsonFormatter` | PASS — verified via TC-8 |

### Scope Decisions
  1. `invalidate_and_refetch` integration with kid-mismatch not tested here
  INV-09 requires this method to be called by the JWT middleware when a `kid` is unrecognised.
  The JWKSCache itself only provides the method — the wiring happens in Task 2.3 auth middleware.
  Accepted — method correctness verified here; integration tested in Task 2.3.

  ---
  2. Real Okta JWKS endpoint not called
  All tests use a mocked `httpx.get` response. Accepted — real network calls would make tests
  brittle and environment-dependent. The actual JWKS fetch is verified during Task 2.5 startup.

### Verification Verdict
[x] All planned cases passed
[x] CC challenge reviewed
[x] Code review complete (if invariant-touching)
[x] Scope decisions documented

**Status:**
Done

---

## Task 2.3 — JWT Auth Middleware (API A)

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 2

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | No Authorization header | 401 with structured JSON body | PASS |
| TC-2 | Malformed token (not a JWT) | 401 with structured JSON body | PASS |
| TC-3 | Expired token — JWTError on decode | 401 | PASS |
| TC-4 | Valid token — key found | Returns claims dict | PASS |
| TC-5 | Unknown kid — invalidate_and_refetch called — retry succeeds | Claims returned | PASS |
| TC-6 | Key not found after retry | 401 Signing key not found | PASS |
| TC-7 | No kid in header | 401 | PASS |
| TC-8 | No stack trace in any HTTPException detail | detail has no Traceback | PASS |
| TC-9 | leeway=60 passed to jwt.decode | options leeway confirmed | PASS |
| TC-10 | audience and issuer passed to jwt.decode | kwargs confirmed | PASS |
| TC-11 | algorithms=["RS256"] passed to jwt.decode | kwargs confirmed | PASS |
| TC-12 | invalidate_and_refetch NOT called on JWTError expiry | call_count == 0 | PASS |

### Prediction Statement
verify_token should reject missing, malformed, and expired tokens with 401. Valid tokens should return claims. Unknown kid should trigger invalidate_and_refetch and retry once. jwt.decode must receive leeway=60, RS256, correct audience and issuer. No stack traces in error responses.

### CC Challenge Output
  1. audience and issuer not verified as passed to jwt.decode
  TC-9 verified leeway but audience/issuer kwargs were never asserted.
  -> Accepted — add case (TC-10)

  ---
  2. algorithms=["RS256"] not verified as passed to jwt.decode
  Same gap — algorithms kwarg never asserted.
  -> Accepted — add case (TC-11)

  ---
  3. invalidate_and_refetch NOT called on JWTError from expiry (INV-09)
  INV-09: invalidation fires only on kid mismatch, never on exp or other claim failures.
  Tested that it IS called on missing kid but never tested it is NOT called on expired token.
  -> Accepted — add case (TC-12)

  ---
  4. Real HTTP behavior with auto_error=False
  Tested by passing None directly; real FastAPI behavior without Authorization header not tested.
  -> Rejected — requires running server; covered by Task 2.5.

  ---
  5. load_dotenv() fires at module level
  Mocked out in tests.
  -> Rejected — plainly visible at module body top level; Python semantics guarantee import-time execution.

### Code Review
**Invariants touched:** INV-07, INV-09, INV-10, INV-16, INV-21

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-07 | `verify_token` is a FastAPI dependency using `Depends()` — no route can bypass it | `api-a/app/auth/__init__.py` — `verify_token` signature | PASS — uses `Depends(security)` and returns claims dict for downstream routes |
| INV-09 | On `kid not found`, `invalidate_and_refetch` called and `get_key` retried once before 401 | `verify_token` — kid lookup + retry block | PASS — TC-4/TC-5 confirm single invalidation + retry |
| INV-09 | `invalidate_and_refetch` NOT called on JWTError (expiry/claim failure) | `verify_token` — JWTError catch block | PASS — TC-12 confirms call_count == 0 on expiry |
| INV-10 | `leeway=60` on `jwt.decode()` | `verify_token` — `options={"leeway": 60}` | PASS — TC-9 confirms |
| INV-16 | Missing/invalid/expired tokens all produce 401, not 403 or 500 | `verify_token` — all exception paths | PASS — TC-1 through TC-7 all return 401 |
| INV-21 | No stack trace or internal detail in any `HTTPException` detail | `verify_token` — all `raise HTTPException(...)` calls | PASS — TC-8 confirms |

### Scope Decisions
  1. Real HTTP behavior with auto_error=False not tested
  Missing Authorization header simulated by passing None directly to verify_token.
  Accepted — full HTTP integration requires a running server; covered by Task 2.5 startup check.

  ---
  2. Token clock skew test uses mocked jwt.decode
  Leeway is verified by asserting the kwarg is passed correctly (TC-9) rather than constructing
  a token with a slightly expired exp. Accepted — constructing a real signed JWT would require
  a private key, which is out of scope for unit tests.

### Verification Verdict
[x] All planned cases passed
[x] CC challenge reviewed
[x] Code review complete (if invariant-touching)
[x] Scope decisions documented

**Status:**
Done

---

## Task 2.4 — User Route Handlers (API A)

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 2

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | GET /health — no token | 200 `{"status": "ok"}` | |
| TC-2 | GET /api/users — no token | 401 | |
| TC-3 | GET /api/users — valid token, api-a:read scope | 200, list of 3 users | |
| TC-4 | GET /api/users — valid token, missing api-a:read | 403 | |
| TC-5 | GET /api/users/alice@example.com — alice's own token | 200, alice's record | |
| TC-6 | GET /api/users/alice@example.com — bob's token (non-admin) | 403 | |
| TC-7 | GET /api/users/alice@example.com — admin token | 200 (ownership bypass) | |
| TC-8 | POST /api/users — valid token with api-a:write | 201 with new record | |
| TC-9 | PUT /api/users/alice@example.com — api-a:write scope | 200 with updated record | |
| TC-10 | Any protected endpoint — expired token | 401 | |
| TC-11 | CORS: request from http://localhost:3000 | 200 with correct CORS headers | |
| TC-12 | CORS: request from http://evil.com | No CORS headers (request blocked by browser) | |

### Prediction Statement
<!-- LEAVE BLANK — engineer writes predictions before running verification commands -->

### CC Challenge Output
<!-- Paste CC's response to: 'What did you not test in this task?'
For each item: accepted (added case) / rejected (reason). -->

### Code Review
**Invariants touched:** INV-07, INV-12, INV-14, INV-16, INV-20, INV-21, INV-23

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-07 | `require_scope(...)` applied via `Depends()` on every protected route — health endpoint explicitly excluded | `api-a/app/routes/users.py` — all route decorators | |
| INV-12 | Missing scope returns 403, not 401 — `require_scope` raises `HTTPException(403)` | `api-a/app/auth/__init__.py` — `require_scope` exception | |
| INV-14 | `GET /api/users/{user_email}` compares `token.sub` to `record["email"]` — not any other field | `api-a/app/routes/users.py` — ownership check block | |
| INV-14 | Admin bypass reads from `claims["groups"]` claim, not from a DB lookup | `api-a/app/routes/users.py` — admin group check | |
| INV-16 | All 401 responses use structured JSON: `{"error": "...", "message": "..."}` | All `HTTPException(401)` raises across auth module | |
| INV-20 | `allow_origins` in CORS middleware is `["http://localhost:3000"]` — not `["*"]`, not empty | `api-a/app/main.py` — CORS middleware config | |
| INV-21 | Global exception handler catches unhandled exceptions and returns generic message — no stack trace | `api-a/app/main.py` — exception handler | |
| INV-23 | `_log_auth_decision` emits structured JSON with: timestamp, subject, route, required_scope, outcome | `api-a/app/auth/__init__.py` — `_log_auth_decision` function | |

### Scope Decisions
<!-- What was accepted as out of scope and why. Cannot be left blank for deliverables. -->

### Verification Verdict
[ ] All planned cases passed
[ ] CC challenge reviewed
[ ] Code review complete (if invariant-touching)
[ ] Scope decisions documented

**Status:**

---

## Task 2.5 — API A Startup Verification

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 2

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | run.sh starts cleanly | Uvicorn logs show "Application startup complete" on port 3001 | |
| TC-2 | /health accessible | curl returns 200 | |
| TC-3 | JWKS cache logs on startup | First token validation shows JWKS_CACHE_MISS then JWKS_CACHE_REFRESHED | |

### Prediction Statement
<!-- LEAVE BLANK — engineer writes predictions before running verification commands -->

### CC Challenge Output
<!-- Paste CC's response to: 'What did you not test in this task?'
For each item: accepted (added case) / rejected (reason). -->

### Code Review
**Invariants touched:** INV-11 (JWKS cache logging observable on startup)

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-11 | JWKS cache log output is visible in terminal without attaching a debugger — log level is not suppressed | `api-a/app/auth/jwks_cache.py` — logger configuration and `run.sh` startup | |

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

**Prediction:**
<!-- LEAVE BLANK — engineer writes prediction before running -->

**Result:**
<!-- LEAVE BLANK -->

**Verdict:** [ ] PASSED
