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
| TC-1 | GET /health — no token | 200 `{"status": "ok"}` | PASS |
| TC-2 | GET /api/users — no token | 401 | PASS |
| TC-3 | GET /api/users — valid token, api-a:read scope | 200, list of 3 users | PASS |
| TC-4 | GET /api/users — valid token, missing api-a:read | 403 | PASS |
| TC-5 | GET /api/users/alice@example.com — alice's own token | 200, alice's record | PASS |
| TC-6 | GET /api/users/alice@example.com — bob's token (non-admin) | 403 | PASS |
| TC-7 | GET /api/users/alice@example.com — admin token | 200 (ownership bypass) | PASS |
| TC-8 | POST /api/users — valid token with api-a:write | 201 with new record | PASS |
| TC-9 | PUT /api/users/alice@example.com — api-a:write scope | 200 with updated record | PASS |
| TC-10 | Any protected endpoint — expired token | 401 | PASS (auth middleware; dependency_overrides used in route tests) |
| TC-11 | CORS: request from http://localhost:3000 | 200 with correct CORS headers | PASS |
| TC-12 | CORS: disallowed origin does not get ACAO header | ACAO header absent or not set to evil.com | PASS |
| TC-13 | GET /api/users/{user_email} — email not found (admin token) | 404 | PASS |
| TC-14 | POST /api/users — duplicate email | 409 conflict | PASS |
| TC-15 | PUT /api/users/{user_email} — user not found | 404 | PASS |
| TC-16 | PUT /api/users/{user_email} — email key in body | email unchanged, other fields updated | PASS |
| TC-17 | GET /api/users/{user_email} — insufficient scope | 403 | PASS |
| TC-18 | POST /api/users — insufficient scope | 403 | PASS |
| TC-19 | PUT /api/users/{user_email} — insufficient scope | 403 | PASS |
| TC-20 | GET /api/users/{user_email} — no token | 401 | PASS |
| TC-21 | POST /api/users — no token | 401 | PASS |
| TC-22 | PUT /api/users/{user_email} — no token | 401 | PASS |
| TC-23 | GET /api/users/{user_email} — non-admin, own email, record absent | 404 | PASS |
| TC-24 | GET /api/users/{user_email} — ownership 403 response body structure | {"error": "insufficient_scope", "message": ...} | PASS |
| TC-25 | POST /api/users — body missing email key | 500, {"error": "internal_error"}, no traceback | PASS |
| TC-26 | PUT /api/users/{user_email} — body has only email key | 200, record unchanged | PASS |

**26/26 PASS**

### Prediction Statement
Routes should enforce auth via require_scope Depends(). /health is public. /api/users returns all 3 seed records. /api/users/{email} enforces token.sub == record.email; api-b-admins group bypasses. POST returns 201. PUT returns 404 for missing users. CORS allows only http://localhost:3000.

### CC Challenge Output
  1. Non-admin user requests their own email but record doesn't exist in DB
  TC-13 only tested admin -> 404. A non-admin whose sub matches the path email but the record is absent follows a different code path: ownership check passes, then DB returns None -> 404. Not tested.
  -> Accepted — added TC-23

  ---
  2. PUT with only the email key in the update body
  safe_updates = {} after stripping email -> user.update({}) is a no-op -> returns unchanged record at 200. Not tested.
  -> Accepted — added TC-26

  ---
  3. Ownership violation 403 response body structure not verified
  TC-6 asserted status 403 but never checked body is {"error": "insufficient_scope", "message": "..."} (INV-16).
  -> Accepted — added TC-24

  ---
  4. POST body missing the email key entirely
  KeyError in mock_db.create_user -> global exception handler -> 500 with {"error": "internal_error", ...}. Natural path that exercises INV-21 handler without a test-only route.
  -> Accepted — added TC-25

  ---
  5. CORS — disallowed origin does not get ACAO header
  TC-12 was in original spec. Server doesn't reject the request but must not echo the disallowed origin as ACAO. Testable via TestClient.
  -> Accepted — added TC-12 (PASS)

  ---
  6. groups claim absent entirely from token
  claims.get("groups", []) returns [] if key missing — identical path to non-admin with empty groups. No new code path.
  -> Rejected — default [] covers this; no observable behavioral gap

  ---
  7. sub claim missing from token
  claims.get("sub", "") returns "" — never matches any email path param -> ownership check fails -> 403. Same code path as wrong-sub case already tested in TC-6.
  -> Rejected — same code path, no new coverage

  ---
  8. Response body field completeness for PUT/POST
  Verifying all fields present in the response body retests mock_db.create_user/update_user return values, already covered in Task 2.1 TC-4 and TC-5.
  -> Rejected — testing mock_db behaviour, not route behaviour

### Code Review
**Invariants touched:** INV-07, INV-12, INV-14, INV-16, INV-20, INV-21, INV-23

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-07 | `require_scope(...)` applied via `Depends()` on every protected route — health endpoint explicitly excluded | `api-a/app/routes/users.py` — all route decorators | PASS — /health has no Depends; all 4 others use require_scope |
| INV-12 | Missing scope returns 403, not 401 — `require_scope` raises `HTTPException(403)` | `api-a/app/auth/__init__.py` — `require_scope` exception | PASS — TC-4, TC-17, TC-18, TC-19 all confirm 403 |
| INV-14 | `GET /api/users/{user_email}` compares `token.sub` to `record["email"]` — not any other field | `api-a/app/routes/users.py` — ownership check block | PASS — `token_sub != user_email` is the guard expression |
| INV-14 | Admin bypass reads from `claims["groups"]` claim, not from a DB lookup | `api-a/app/routes/users.py` — admin group check | PASS — `"api-b-admins" in groups` where groups = claims.get("groups", []) |
| INV-16 | All 401 responses use structured JSON: `{"error": "...", "message": "..."}` | All `HTTPException(401)` raises across auth module | PASS — inherited from verify_token (Task 2.3); TC-2, TC-20, TC-21, TC-22 confirm 401 |
| INV-20 | `allow_origins` in CORS middleware is `["http://localhost:3000"]` — not `["*"]`, not empty | `api-a/app/main.py` — CORS middleware config | PASS — `allow_origins=["http://localhost:3000"]` literal confirmed |
| INV-21 | Global exception handler catches unhandled exceptions and returns generic message — no stack trace | `api-a/app/main.py` — exception handler | PASS — handler registered; returns `{"error": "internal_error", "message": "An unexpected error occurred"}` |
| INV-23 | `_log_auth_decision` emits structured JSON with: timestamp, subject, route, required_scope, outcome | `api-a/app/auth/__init__.py` — `_log_auth_decision` function | PASS — 5-field JSON dict confirmed by code review (inherited from Task 2.3) |

### Scope Decisions
  1. TC-10 (expired token) tested via dependency_overrides, not real JWT
  At the route handler layer, auth is exercised through dependency_overrides. The expired-token path through verify_token is fully tested in Task 2.3 (TC-3). Splitting the integration would require signing real tokens. Accepted.

  ---
  2. Response body field completeness not tested for POST/PUT responses
  Verifying all fields present in the response retests mock_db return values already covered in Task 2.1. Accepted out of scope — route tests focus on HTTP semantics, not DB return shape.

### Verification Verdict
[x] All planned cases passed
[x] CC challenge reviewed
[x] Code review complete (if invariant-touching)
[x] Scope decisions documented

**Status:**
Done

---

## Task 2.5 — API A Startup Verification

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 2

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | run.sh starts cleanly | Uvicorn logs show "Application startup complete" on port 3001 | PASS |
| TC-2 | /health accessible | curl returns 200 | PASS |
| TC-3 | JWKS cache logs on startup | First token validation shows JWKS_CACHE_MISS then JWKS_CACHE_REFRESHED | PASS |

### Prediction Statement
<!-- LEAVE BLANK — engineer writes predictions before running verification commands -->

### CC Challenge Output
  1. run.sh not actually executed to confirm startup
  File was written but bash run.sh was not invoked to verify uvicorn starts on port 3001 and reads env vars.
  -> Accepted — this IS Task 2.5 manual verification (TC-1 through TC-3 below)

  ---
  2. Git executable bit not set on run.sh
  chmod +x sets filesystem permission but git tracks the bit separately via update-index. Without it the bit is lost on fresh clone.
  -> Accepted — fixed: git add + git update-index --chmod=+x; ls-files --stage confirms 100755

  ---
  3. README says Python 3.11+ but Fixed Stack requires Python 3.14+
  Incorrect prerequisite — could mislead someone trying to run on 3.11/3.12.
  -> Accepted — fixed: README updated to Python 3.14+

  ---
  4. .env CRLF risk with `source .env` in run.sh
  Windows .env files have CRLF. `source .env` appends \r to every variable value, silently corrupting them. Spec dictates the exact command so it cannot be changed.
  -> Accepted — documented in README with workaround command; logged as deviation in SESSION_2_LOG.md

  ---
  5. README endpoint table not cross-checked against users.py
  No independent verification that the 5 routes listed match the actual implementation.
  -> Rejected — README and users.py written in the same session from direct reference; all routes confirmed by 26 passing tests

  ---
  6. run.sh line endings
  On Windows git with autocrlf, written files may get CRLF, causing `bash^M: bad interpreter`.
  -> Accepted as check — verified clean LF via `cat -A` (output shows $ not ^M$); no fix needed

### Code Review
**Invariants touched:** INV-11 (JWKS cache logging observable on startup)

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-11 | JWKS cache log output is visible in terminal without attaching a debugger — log level is not suppressed | `api-a/app/auth/jwks_cache.py` — logger configuration and `run.sh` startup | PASS — JWKS_CACHE_MISS and JWKS_CACHE_REFRESHED observed in terminal on first real token request; confirmed without debugger |

### Scope Decisions
  1. run.sh actual startup not verified by automated test
  Starting a real uvicorn server in a unit test requires process management and port binding — out of scope for file-creation tasks. TC-1 through TC-3 are manual verification steps performed by the engineer during Task 2.5.

  ---
  2. CRLF in run.sh source .env command not fixed
  The spec explicitly dictates `set -a && source .env && set +a`. Changing the command would be a spec deviation. Documented as a known Windows hazard with the workaround in README.

### Verification Verdict
[x] All planned cases passed
[x] CC challenge reviewed
[x] Code review complete (if invariant-touching)
[x] Scope decisions documented

**Status:**
Done

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
Done

**Verdict:** [*] PASSED
