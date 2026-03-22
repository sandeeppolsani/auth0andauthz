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
| TC-1 | fetch_m2m_token with valid credentials | Returns a JWT string | |
| TC-2 | fetch_m2m_token with wrong secret | Okta returns 401, function raises HTTPException(503) | |
| TC-3 | scope=api-b:read in request | Token endpoint called with scope parameter explicitly in POST body | |
| TC-4 | Token value not in logs | Log output does not contain the raw JWT string | |
| TC-5 | Secret not in logs | Log output does not contain OKTA_CLIENT_SECRET value | |

### Prediction Statement
<!-- LEAVE BLANK — engineer writes predictions before running verification commands -->

### CC Challenge Output
<!-- Paste CC's response to: 'What did you not test in this task?'
For each item: accepted (added case) / rejected (reason). -->

### Code Review
**Invariants touched:** INV-17, INV-19

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-17 | `scope=api-b:read` is present as an explicit body parameter in the POST to Okta's token endpoint — not omitted, not assumed | `api-a/app/auth/m2m.py` — httpx POST body / data dict | |
| INV-17 | `grant_type=client_credentials` is also present in the POST body | `api-a/app/auth/m2m.py` — httpx POST body | |
| INV-19 | The raw access token string is never passed to any logger, print(), or structured log field | `api-a/app/auth/m2m.py` — all logging calls and return path | |
| INV-19 | `OKTA_CLIENT_SECRET` value is never passed to any logger, print(), or structured log field | `api-a/app/auth/m2m.py` — all logging calls | |
| INV-19 | Credentials read exclusively from `os.environ` — no hardcoded fallback values | `api-a/app/auth/m2m.py` — env var access pattern | |

### Scope Decisions
<!-- What was accepted as out of scope and why. Cannot be left blank for deliverables. -->

### Verification Verdict
[ ] All planned cases passed
[ ] CC challenge reviewed
[ ] Code review complete (if invariant-touching)
[ ] Scope decisions documented

**Status:**

---

## Task 5.2 — Internal Pull-Analytics Endpoint (API A)

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 5

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | API B running — happy path | Returns analytics data from API B wrapped in `{"source": "api-b", "data": ...}` | |
| TC-2 | API B down | Returns structured error — not stack trace | |
| TC-3 | M2M token used by API B — same JWKS path | API B logs show validation via JWKS, no special handling | |
| TC-4 | Token not logged | API A logs for this call contain no JWT string | |

### Prediction Statement
<!-- LEAVE BLANK — engineer writes predictions before running verification commands -->

### CC Challenge Output
<!-- Paste CC's response to: 'What did you not test in this task?'
For each item: accepted (added case) / rejected (reason). -->

### Code Review
**Invariants touched:** INV-17, INV-18, INV-19, INV-21

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-17 | `fetch_m2m_token()` is called to obtain the token — the scope is requested inside that function, confirmed in Task 5.1 | `api-a/app/routes/internal.py` — fetch_m2m_token import and call | |
| INV-18 | API A calls API B at `http://localhost:3002/api/analytics/summary` with `Authorization: Bearer <token>` — no side-channel or bypass | `api-a/app/routes/internal.py` — httpx GET call and headers | |
| INV-18 | No special header, flag, or parameter is added to the API B call to signal "this is M2M" — the token is the only credential | `api-a/app/routes/internal.py` — full headers dict on the API B call | |
| INV-19 | The M2M access token value is not included in any log field, response body, or error message returned by this endpoint | `api-a/app/routes/internal.py` — all log calls and response dicts | |
| INV-21 | API B down path returns `{"error": "...", "message": "..."}` — no stack trace or httpx exception detail exposed | `api-a/app/routes/internal.py` — except block and error response | |

### Scope Decisions
<!-- What was accepted as out of scope and why. Cannot be left blank for deliverables. -->

### Verification Verdict
[ ] All planned cases passed
[ ] CC challenge reviewed
[ ] Code review complete (if invariant-touching)
[ ] Scope decisions documented

**Status:**

---

## Task 5.3 — M2M End-to-End Verification

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 5

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | Full M2M chain succeeds | GET /api/internal/pull-analytics returns analytics data | |
| TC-2 | API B audit_log populated by M2M call | GET /api/audit-log shows entry with subject from M2M token sub | |
| TC-3 | M2M token has api-b:read scope | Decoded M2M token scp claim contains api-b:read | |
| TC-4 | M2M call to api-b:admin endpoint | 403 returned (M2M token lacks admin scope) | |
| TC-5 | Client secret not in API A response body | curl response from /api/internal/pull-analytics contains no secret value | |

### Prediction Statement
<!-- LEAVE BLANK — engineer writes predictions before running verification commands -->

### CC Challenge Output
<!-- Paste CC's response to: 'What did you not test in this task?'
For each item: accepted (added case) / rejected (reason).
Note: Task 5.3 is primarily a verification task. If no CC prompt was needed (no gaps
found in 5.1 or 5.2), the CC Challenge here covers the end-to-end verification
commands themselves — ask CC: 'What did you not test in this end-to-end verification?' -->

### Code Review
**Invariants touched:** INV-17, INV-18, INV-19

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-18 | API B's JWKS middleware processes the M2M token identically to a user token — confirmed by checking API B logs for `JWKS_CACHE_HIT` or `JWKS_CACHE_REFRESHED` on the M2M call | API B stdout logs during TC-1 | |
| INV-19 | Full response body from `/api/internal/pull-analytics` contains no credential values — TC-5 confirms this at runtime | curl output — manual scan | |
| INV-17 | Decoded M2M token `scp` claim contains `api-b:read` and nothing else — scope is narrowly granted | TC-3 — base64url decode the token payload and inspect `scp` | |

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

**Result:**
<!-- LEAVE BLANK -->

**Verdict:** [ ] PASSED
