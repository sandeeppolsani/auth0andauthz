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
| TC-1 | get_analytics returns seed | Dict with total_users=42 | |
| TC-2 | get_config returns seed | maintenance_mode=False | |
| TC-3 | update_config patches correctly | Updated key reflected in subsequent get_config | |
| TC-4 | append_audit_entry + get_audit_log | Entry appears in log | |
| TC-5 | audit_log starts empty | get_audit_log() returns [] on fresh import | |

### Prediction Statement
<!-- LEAVE BLANK — engineer writes predictions before running verification commands -->

### CC Challenge Output
<!-- Paste CC's response to: 'What did you not test in this task?'
For each item: accepted (added case) / rejected (reason). -->

### Code Review
**Invariants touched:** INV-15 (audit log write path)

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-15 | `append_audit_entry` is called by auth middleware (Task 3.2) — NOT by route handlers | `api-b/app/db/mock_db.py` — confirm no audit write logic exists here; the function is a passive receiver only | |
| INV-15 | `append_audit_entry` entry schema accepts: timestamp, subject, route, outcome — all four fields | `mock_db.py` — docstring and append logic | |

### Scope Decisions
<!-- What was accepted as out of scope and why. Cannot be left blank for deliverables. -->

### Verification Verdict
[ ] All planned cases passed
[ ] CC challenge reviewed
[ ] Code review complete (if invariant-touching)
[ ] Scope decisions documented

**Status:**

---

## Task 3.2 — JWKS Cache + JWT Auth Middleware (API B)

### Test Cases Applied
Source: EXECUTION_PLAN.md Session 3

| Case | Scenario | Expected | Result |
|------|----------|----------|--------|
| TC-1 | verify_token loads from api-b .env | OKTA_ISSUER/OKTA_AUDIENCE read from api-b's own .env | |
| TC-2 | require_group — user in group | Returns claims, logs pass | |
| TC-3 | require_group — user not in group | 403, logs fail, audit entry written | |
| TC-4 | Every auth decision writes to audit_log | After 3 requests, get_audit_log() has 3 entries | |

### Prediction Statement
<!-- LEAVE BLANK — engineer writes predictions before running verification commands -->

### CC Challenge Output
<!-- Paste CC's response to: 'What did you not test in this task?'
For each item: accepted (added case) / rejected (reason). -->

### Code Review
**Invariants touched:** INV-07, INV-08, INV-09, INV-10, INV-11, INV-13, INV-15, INV-18, INV-23

| Item | What to look for | Where | Result |
|------|-----------------|-------|--------|
| INV-07 | `verify_token` present and identical in structure to API A — no route can bypass it | `api-b/app/auth/__init__.py` — verify_token definition | |
| INV-08 | JWKS cache is a module-level instance — not re-instantiated per request | `api-b/app/auth/__init__.py` — top-level cache instantiation | |
| INV-09 | `invalidate_and_refetch` path present — triggered on kid mismatch, not on exp failures | `api-b/app/auth/jwks_cache.py` — same check as API A Task 2.2 | |
| INV-10 | `leeway=60` on `jwt.decode()` | `api-b/app/auth/__init__.py` — jwt.decode() call | |
| INV-11 | All five JWKS log event strings present and emitting | `api-b/app/auth/jwks_cache.py` — logging calls | |
| INV-13 | `require_group("api-b-admins")` is a separate dependency from `require_scope("api-b:admin")` — both must be present on admin routes | `api-b/app/auth/__init__.py` — require_group factory | |
| INV-15 | `_log_auth_decision` calls `append_audit_entry` — both pass and fail outcomes write to audit_log | `api-b/app/auth/__init__.py` — `_log_auth_decision` body | |
| INV-18 | No special handling for M2M tokens — `verify_token` is the same function for all callers | `api-b/app/auth/__init__.py` — confirm no token-origin branching | |
| INV-23 | Structured JSON log line emitted on every auth decision: timestamp, subject, route, required_scope, outcome | `api-b/app/auth/__init__.py` — `_log_auth_decision` log output | |
| **Independence** | `api-b/app/auth/__init__.py` imports nothing from `api-a/` — fully independent module | All import statements in `api-b/` | |

### Scope Decisions
<!-- What was accepted as out of scope and why. Cannot be left blank for deliverables. -->

### Verification Verdict
[ ] All planned cases passed
[ ] CC challenge reviewed
[ ] Code review complete (if invariant-touching)
[ ] Scope decisions documented

**Status:**

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
