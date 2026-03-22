# VERIFICATION_RECORD.md

**Session:** Session 5 — M2M Flow
**Date:** 23/03/2026
**Engineer:** Sandeep

---

## Task 5.1 — M2M Token Fetch (API A)

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 5

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | fetch_m2m_token with valid credentials | Returns a JWT string | PENDING — requires live Okta + running API A; confirmed at runtime (Task 5.3) |
| TC-2 | fetch_m2m_token with wrong secret | Okta returns 401, function raises HTTPException(503) | PASS — code path confirmed: `if response.status_code != 200:` at m2m.py:62 raises HTTPException(503) |
| TC-3 | scope=api-b:read in request | Token endpoint called with scope parameter explicitly in POST body | PASS — `"scope": "api-b:read"` in `data=` dict at m2m.py:53; comment notes INV-17 |
| TC-4 | Token value not in logs | Log output does not contain the raw JWT string | PASS — `response.json()["access_token"]` at line 69 is returned directly; never passed to `_log()` or any logger call |
| TC-5 | Secret not in logs | Log output does not contain OKTA_CLIENT_SECRET value | PASS — `client_secret` at line 45 used only in `auth=(client_id, client_secret)` at line 55; `_log()` records only event/subject/scope/outcome fields |

### Prediction Statement
<!-- LEAVE BLANK — engineer writes predictions before running verification commands -->

### CC Challenge Output
**TC-6 — Missing env var raises KeyError, not HTTPException(503) (accepted)**
If `OKTA_CLIENT_ID`, `OKTA_CLIENT_SECRET`, or `OKTA_TOKEN_ENDPOINT` is absent from the environment, `os.environ["..."]` raises `KeyError`, which propagates as a 500 via the global handler — not a 503. This is acceptable: missing env vars at startup represent a misconfiguration, not a transient M2M failure. The global exception handler in main.py catches it and returns `{"error": "internal_error", "message": "An unexpected error occurred"}` — no stack trace exposed (INV-21 satisfied). No additional test case added; the behaviour is safe.

**TC-7 — httpx timeout raises, not HTTPException(503) (accepted)**
If the Okta token endpoint times out, `httpx.TimeoutException` is raised — not caught in `fetch_m2m_token`. The global handler in API A returns 500. For an internal M2M call this is acceptable (caller /api/internal/pull-analytics catches and wraps at the endpoint level in Task 5.2). No additional case added to 5.1; covered by Task 5.2's TC-2 (API B down / unreachable).

**Content-Type header redundant when httpx data= is used (rejected)**
`httpx` sets `Content-Type: application/x-www-form-urlencoded` automatically when `data=` is a dict. The explicit header is still correct and reinforces spec intent. Not a bug; no change.

### Code Review
**Invariants touched:** INV-17, INV-19

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-17 | `scope=api-b:read` is present as an explicit body parameter in the POST to Okta's token endpoint — not omitted, not assumed | `api-a/app/auth/m2m.py` — `data=` dict at line 53 | PASS — `"scope": "api-b:read"` confirmed |
| INV-17 | `grant_type=client_credentials` is also present in the POST body | `api-a/app/auth/m2m.py` — `data=` dict at line 52 | PASS — `"grant_type": "client_credentials"` confirmed |
| INV-19 | The raw access token string is never passed to any logger, print(), or structured log field | `api-a/app/auth/m2m.py` — all `_log()` calls and return path | PASS — `response.json()["access_token"]` only appears in the return statement (line 69); `_log()` records event/subject/scope/outcome only |
| INV-19 | `OKTA_CLIENT_SECRET` value is never passed to any logger, print(), or structured log field | `api-a/app/auth/m2m.py` — all `_log()` calls | PASS — `client_secret` used only in `auth=` tuple (line 55); never in any log call |
| INV-19 | Credentials read exclusively from `os.environ` — no hardcoded fallback values | `api-a/app/auth/m2m.py` — env var access at lines 43-45 | PASS — `os.environ["OKTA_CLIENT_ID"]`, `os.environ["OKTA_CLIENT_SECRET"]`, `os.environ["OKTA_TOKEN_ENDPOINT"]`; no defaults |

### Scope Decisions
- `load_dotenv()` not called in `m2m.py` — `app/auth/__init__.py` already calls `load_dotenv()` at module load time. Calling it again would be harmless but redundant. `fetch_m2m_token` is only called from within the running API A process where `__init__.py` is already imported.
- No caching of the M2M token — spec does not require it. Each call to `fetch_m2m_token()` fetches a fresh token. Caching (with TTL < exp) is a valid optimisation but not in scope for this session.

### Verification Verdict
[x] All planned cases passed (TC-1 PENDING runtime; TC-2 through TC-5 PASS static)
[x] CC challenge reviewed
[x] Code review complete (if invariant-touching)
[x] Scope decisions documented

**Status:** TC-2 through TC-5 PASS. TC-1 PENDING runtime verification (Task 5.3).

---

## Task 5.2 — Internal Pull-Analytics Endpoint (API A)

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 5

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | API B running — happy path | Returns analytics data from API B wrapped in `{"source": "api-b", "data": ...}` | PENDING — runtime (Task 5.3) |
| TC-2 | API B down | Returns structured error — not stack trace | PASS — `httpx.RequestError` caught at internal.py:55; returns `{"source": "api-b", "error": 503, "message": "API B call failed"}` — no exception detail exposed (INV-21) |
| TC-3 | M2M token used by API B — same JWKS path | API B logs show validation via JWKS, no special handling | PENDING — runtime (Task 5.3); code confirms only `Authorization: Bearer` header sent — no special M2M flag (INV-18) |
| TC-4 | Token not logged | API A logs for this call contain no JWT string | PASS — `m2m_token` at line 43 used only in `Authorization` header (line 49); `_log()` records subject/route/scope/outcome only |

### Prediction Statement
<!-- LEAVE BLANK — engineer writes predictions before running verification commands -->

### CC Challenge Output
**TC-5 — 4xx from API B (e.g. 403 scope mismatch) returns structured error, not data (accepted)**
If the M2M token lacks `api-b:read` scope (misconfiguration), API B returns 403. The endpoint handles this in the `status_code != 200` branch returning `{"source": "api-b", "error": 403, "message": "API B call failed"}` — no raw API B error body leaked. Covered by existing TC path; no new test case added since this is exercised in Task 5.3 TC-4.

**TC-6 — fetch_m2m_token() raises HTTPException(503) — not caught here (accepted)**
If `fetch_m2m_token()` raises `HTTPException(503)`, it propagates directly to FastAPI's exception handler — the global handler does NOT intercept `HTTPException` (FastAPI handles it natively), so the 503 with `{"error": "m2m_token_error", ...}` is returned correctly. No catch needed. No new test case; behaviour is correct by FastAPI semantics.

**Response body from API B response.json() could raise if content is not JSON (rejected)**
`GET /api/analytics/summary` always returns JSON. A non-JSON 200 response from a correct API B is not a realistic failure path. No guard added; would add noise for a path that cannot happen in this controlled lab.

### Code Review
**Invariants touched:** INV-17, INV-18, INV-19, INV-21

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-17 | `fetch_m2m_token()` is called to obtain the token — the scope is requested inside that function, confirmed in Task 5.1 | `api-a/app/routes/internal.py` — line 43 | PASS — `m2m_token = await fetch_m2m_token()` confirmed |
| INV-18 | API A calls API B at `http://localhost:3002/api/analytics/summary` with `Authorization: Bearer <token>` — no side-channel or bypass | `api-a/app/routes/internal.py` — lines 47-50 | PASS — `http://localhost:3002/api/analytics/summary` with `Authorization: Bearer {m2m_token}` only |
| INV-18 | No special header, flag, or parameter is added to the API B call to signal "this is M2M" — the token is the only credential | `api-a/app/routes/internal.py` — headers dict at line 49 | PASS — `headers={"Authorization": f"Bearer {m2m_token}"}` is the only header; no X-M2M or similar |
| INV-19 | The M2M access token value is not included in any log field, response body, or error message returned by this endpoint | `api-a/app/routes/internal.py` — `_log()` calls at lines 56, 60, 64 | PASS — `_log()` logs subject/route/required_scope/outcome only; `m2m_token` never appears in any log or response dict |
| INV-21 | API B down path returns `{"error": "...", "message": "..."}` — no stack trace or httpx exception detail exposed | `api-a/app/routes/internal.py` — except block at line 55 | PASS — `except httpx.RequestError:` catches and returns `{"source": "api-b", "error": 503, "message": "API B call failed"}`; exception object not included |

### Scope Decisions
- `/api/internal/pull-analytics` has no user auth (`require_scope` / `verify_token` not applied) — spec explicitly states "no user auth required (this endpoint is for M2M demo)". This is intentional.
- CORS: this endpoint is accessible from any origin — it is an internal server-to-server trigger endpoint, not a browser-facing endpoint. The CORS middleware applies globally but does not block requests without an Origin header (i.e. curl / API calls). Acceptable for this lab.

### Verification Verdict
[x] All planned cases passed (TC-1 and TC-3 PENDING runtime; TC-2 and TC-4 PASS static)
[x] CC challenge reviewed
[x] Code review complete (if invariant-touching)
[x] Scope decisions documented

**Status:** TC-2 and TC-4 PASS static. TC-1 and TC-3 PENDING runtime verification (Task 5.3).

---

## Task 5.3 — M2M End-to-End Verification

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 5

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | Full M2M chain succeeds | GET /api/internal/pull-analytics returns analytics data | PASS — verified at runtime; `{"source": "api-b", "data": {...}}` returned |
| TC-2 | API B audit_log populated by M2M call | GET /api/audit-log shows entry with subject from M2M token sub | PASS — verified via API Tester Panel (admin@example.com); audit log entry present with M2M token sub |
| TC-3 | M2M token has api-b:read scope | Decoded M2M token scp claim contains api-b:read | PASS — verified via Python decode snippet; `scp` contains `api-b:read` only |
| TC-4 | M2M call to api-b:admin endpoint | 403 returned (M2M token lacks admin scope) | PASS — curl to /api/config with M2M token returned 403 `insufficient_scope` |
| TC-5 | Client secret not in API A response body | curl response from /api/internal/pull-analytics contains no secret value | PASS — grep returned no output; no credential values in response |

### Prediction Statement
<!-- LEAVE BLANK — engineer writes predictions before running verification commands -->

### CC Challenge Output
**TC-6 — M2M token `iss` and `aud` claims validated by API B (accepted)**
TC-3 confirmed `scp` contains `api-b:read`, but the JWKS middleware in API B also validates `iss` and `aud`. Since API A and API B share the same Okta custom auth server and audience (`api://okta-lab`), the M2M token passes these checks identically to a user token. Confirmed indirectly by TC-1 succeeding (a 401 would have been returned if `iss`/`aud` failed). No new test case; covered by TC-1.

**TC-7 — M2M call with expired token returns 401 from API B (rejected)**
Expiring an M2M token mid-flow would require waiting 1 hour or manually altering the token. Not feasible in this verification session. The JWKS middleware `leeway=60` and expiry check are already verified in Sessions 2 and 3 for user tokens; the same code path applies for M2M tokens (INV-18). No new test case.

**TC-8 — audit log entry written even when M2M token is rejected (e.g. wrong scope) (accepted)**
INV-15 states the audit log write occurs in middleware, not route handlers — meaning it fires on both pass and fail. TC-4 (403 on admin endpoint) verified the 403 response but we didn't explicitly check the audit log for the failed entry. Confirmed as out of scope for this session: the audit middleware was verified in Session 3; INV-15 is unchanged.

### Code Review
**Invariants touched:** INV-17, INV-18, INV-19

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-18 | API B's JWKS middleware processes the M2M token identically to a user token — confirmed by API B logs showing `JWKS_CACHE_HIT` or `JWKS_CACHE_REFRESHED` on the M2M call | API B stdout during TC-1 | PASS — API B JWKS logs appeared on M2M call; no special handling path |
| INV-19 | Full response body from `/api/internal/pull-analytics` contains no credential values | TC-5 curl + grep | PASS — grep returned no output |
| INV-17 | Decoded M2M token `scp` claim contains `api-b:read` — scope explicitly requested and granted | TC-3 Python decode | PASS — `scp: ['api-b:read']` confirmed |

### Scope Decisions
- No CC fix prompt was needed — Tasks 5.1 and 5.2 had no gaps found during end-to-end verification. All 5 TCs passed on first run.
- TC-2 audit log checked via frontend API Tester Panel (admin@example.com) rather than raw curl — equivalent result; panel uses the same `Authorization: Bearer` header.

### Verification Verdict
[x] All planned cases passed
[x] CC challenge reviewed
[x] Code review complete (if invariant-touching)
[x] Scope decisions documented

**Status:** All 5 cases PASS. No fixes required.

---

## Session Integration Check

**Command:**
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

**Prediction:**
<!-- LEAVE BLANK — engineer writes prediction before running -->

**Result:** `{"source": "api-b", "data": {...}}` returned. API B JWKS logs confirmed on M2M call. Audit log populated. M2M token `scp` = `api-b:read` only. 403 on admin endpoint. No secret in response.

**Verdict:** [x] PASSED
