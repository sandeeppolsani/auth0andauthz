# INVARIANTS.md — Okta Identity Lab

**PBVI Phase:** 2 — Invariant Definition
**Status:** Proposed — awaiting engineer sign-off
**Engineer:** Naveen
**Date:** March 2026
**Derived from:** ARCHITECTURE.md + Requirements Brief v1.0

---

## Step 0 — Data Touch-Point Map

### Touch points enumerated before invariant drafting

| Touch Point | Boundary | Data in motion |
|---|---|---|
| T1 | User action → Okta (browser redirect) | PKCE code_verifier, auth code, redirect URI |
| T2 | Okta → Frontend SPA (callback) | Authorization code, state param |
| T3 | Frontend → Okta token endpoint | Auth code + PKCE code_verifier → access token + ID token + refresh token |
| T4 | Frontend memory → API A or API B (HTTP) | Bearer access token in Authorization header |
| T5 | API A or API B → JWKS endpoint (HTTP) | Public key fetch on cold start or cache miss |
| T6 | JWKS cache → JWT validation logic | Cached public keys, kid lookup |
| T7 | JWT claims → authorization middleware | scp, groups, sub claims |
| T8 | Authorization middleware → route handler | Pass or 401/403 rejection |
| T9 | Route handler → mock DB (in-memory dict) | Read/write to user records (API A) or analytics/config/audit (API B) |
| T10 | API B audit middleware → audit_log | Every protected request appends a record |
| T11 | API A → Okta token endpoint (M2M) | Client credentials grant: client_id + client_secret → access token |
| T12 | API A → API B (M2M HTTP call) | Bearer token from client credentials flow |
| T13 | Frontend refresh token (sessionStorage) → Okta token endpoint | Silent refresh: refresh token → new access token + new refresh token |
| T14 | Frontend memory → Token Inspector UI | Decoded JWT header, payload, expiry |
| T15 | Frontend → API Tester UI | Full request and raw response display |

### User journey map (UI + API surface)

| Journey | Screens required |
|---|---|
| J1: Human login | Login Page → (Okta redirect) → Dashboard |
| J2: Inspect JWT claims | Dashboard → Token Inspector Panel |
| J3: Call API A (read) | Dashboard → API Tester Panel → response rendered |
| J4: Call API B (admin) | Dashboard → API Tester Panel → response rendered (403 or 200 depending on group) |
| J5: Silent token refresh | Token Refresh Demo Panel (manual trigger) → before/after comparison |
| J6: Observe 401 on expired token | API Tester Panel → 401 rendered visually |
| J7: Observe 403 on missing scope | API Tester Panel → 403 rendered visually |
| J8: M2M flow (no UI) | API A internal endpoint — no frontend journey; observable via API Tester or Postman |

---

## Invariants

---

### Authentication & Token Acquisition

**INV-01: PKCE code_verifier must never be transmitted to the server**
- Category: security
- Why this matters: if the code_verifier is sent to the backend, an attacker who intercepts the authorization code can exchange it for tokens by providing the same verifier. PKCE is meaningless if the verifier leaks.
- Enforcement points: Frontend only. The code_verifier is generated in the browser, stored temporarily in memory, and sent directly to the Okta token endpoint — never forwarded to API A or API B. No backend route accepts or logs this value.

---

**INV-02: Access tokens must be stored in JavaScript memory only — never in localStorage, sessionStorage, a cookie, or any other persistent browser storage**
- Category: security
- Why this matters: localStorage survives page refresh and is readable by any script on the same origin. An XSS attack can exfiltrate a localStorage-stored token silently. Memory-only storage limits blast radius to the current page lifetime.
- Enforcement points: Frontend React state / context. Confirmed by code review: no `localStorage.setItem`, no `sessionStorage.setItem`, and no `document.cookie` writes for access tokens. Token is lost on page refresh and must be silently restored via the refresh token path.

---

**INV-03: Refresh tokens must be stored in sessionStorage or an httpOnly cookie — not in plain JavaScript memory**
- Category: security
- Why this matters: refresh tokens are long-lived. If lost on page refresh, the user is forced to re-authenticate on every page load — this defeats silent refresh. sessionStorage persists within the tab session. An httpOnly cookie is inaccessible to JavaScript entirely, per ARCHITECTURE.md decision.
- Enforcement points: Frontend token handling layer. Confirmed by code review: refresh token is written to the resolved storage location after every token exchange and after every silent refresh. Memory variable is not used for refresh token persistence.

---

**INV-04: On page load, the frontend must attempt silent token refresh before rendering any protected UI**
- Category: operational
- Why this matters: access tokens are memory-only (INV-02). A page refresh destroys them. If the app renders protected panels before restoring the access token, API calls fail with 401 and the user sees a broken state.
- Enforcement points: Frontend app initialisation path. The silent refresh attempt runs before the router renders any authenticated route. If refresh succeeds, access token is restored to memory. If refresh fails, user is redirected to the Login Page.

---

**INV-05: Silent token refresh must be triggered proactively 60 seconds before access token expiry — not reactively on a 401**
- Category: operational
- Why this matters: reactive refresh on 401 means the user experiences a failed API call, then a delay while the token is refreshed, then a retry. Proactive refresh is invisible to the user.
- Enforcement points: Frontend timer logic. A timer is set after each successful token acquisition to fire at `exp - 60 seconds`. The timer calls the refresh path (INV-03). Code review must confirm the timer is reset after each refresh, not only after login.

---

**INV-06: If silent refresh fails for any reason, the user must be redirected to the Login Page — the session must not silently persist in a broken state**
- Category: security
- Why this matters: a failed refresh may indicate a revoked or expired refresh token. Allowing the app to continue running without a valid access token would result in all API calls failing and the user not knowing why. Transparent logout is the correct enterprise behaviour.
- Enforcement points: Frontend refresh error handler. Any error from the Okta token endpoint during silent refresh triggers a redirect to the Login Page and clears the refresh token from storage.

---

### JWT Validation

**INV-07: Every protected API endpoint must validate the JWT signature using JWKS — no endpoint may skip signature verification**
- Category: security
- Why this matters: a JWT without signature verification is a trusted assertion with no cryptographic basis. Any client could construct a payload claiming admin group membership and gain access.
- Enforcement points: API A and API B auth middleware. Applied via FastAPI `Depends()` on every protected route. Health endpoints are explicitly excluded. Code review must confirm no route decorator bypasses the middleware.

---

**INV-08: JWKS public keys must be cached in memory — no JWKS fetch may be made on a per-request basis**
- Category: operational
- Why this matters: an uncached JWKS implementation makes an HTTP call to Okta on every API request. Under load this creates Okta rate-limit risk and adds 50–200ms latency per request. The JWKS endpoint is designed for infrequent polling.
- Enforcement points: JWKS cache class in both API A and API B. The cache is populated on first request, serves all subsequent requests from memory, and expires after a configurable TTL (10 minutes per ARCHITECTURE.md).

---

**INV-09: On a JWT signature validation failure caused by an unrecognised kid, the JWKS cache must be invalidated and re-fetched before returning a 401**
- Category: operational
- Why this matters: Okta rotates its signing keys periodically. If the cache holds a stale key set, valid tokens signed with a new key will fail validation and the API will return spurious 401s. Re-fetching on `kid` mismatch handles rotation transparently.
- Enforcement points: JWKS cache class. The cache invalidation-and-refetch path is triggered specifically on `kid not found` or signature verification failure — not on all JWT errors (e.g. exp validation failures must still return 401 immediately without a refetch).

---

**INV-10: JWT validation must apply a 60-second clock leeway — a token that is within 60 seconds of expiry or was issued within 60 seconds of the past must not be rejected on clock grounds alone**
- Category: operational
- Why this matters: local machine and Okta clocks can drift. A strict `exp` check rejects valid tokens from machines with minor clock skew.
- Enforcement points: `python-jose` JWTError handling in both API A and API B. The `leeway=60` parameter is set on all `jwt.decode()` calls.

---

**INV-11: The JWKS cache must log every cache hit, cache miss, and re-fetch — these events must be observable without attaching a debugger**
- Category: operational
- Why this matters: ARCHITECTURE.md explicitly calls for "an explicit class with observable state" for the cache. Silent cache failures are the hardest to diagnose. Log output is the primary diagnostic tool in a localhost dev environment.
- Enforcement points: JWKS cache class in both services. Structured JSON log lines emitted on: initial fetch, cache hit, cache expiry/miss, forced invalidation, re-fetch after rotation.

---

### Authorization

**INV-12: A request with a valid JWT but missing the required scope for a route must return 403 Forbidden — not 401 Unauthorized**
- Category: security
- Why this matters: 401 means "you are not authenticated." 403 means "you are authenticated but not authorised." Returning the wrong code obscures the actual failure mode and breaks any client that distinguishes these cases (e.g. the frontend API Tester Panel must surface them differently).
- Enforcement points: scope-checking middleware in both API A and API B. 401 is returned for missing/invalid/expired tokens. 403 is returned for valid tokens with insufficient scope.

---

**INV-13: A request with the api-b:admin scope but without membership in the api-b-admins group must return 403 for admin endpoints**
- Category: security
- Why this matters: scope alone is insufficient for admin routes on API B. The brief and architecture both explicitly model this as a two-factor check (scope + group). A user who has the scope without the group must be denied — this is the least-privilege pattern the lab is designed to demonstrate.
- Enforcement points: group-checking middleware on API B admin routes (`GET /api/config`, `POST /api/config`, `GET /api/audit-log`). The check reads the `groups` claim from the JWT — a JWKS-validated claim, not a runtime Okta API call.

---

**INV-14: The fine-grained ownership check on GET /api/users/:id must compare the JWT's sub claim to the requested record's email field — a non-admin user requesting another user's record must receive 403**
- Category: security
- Why this matters: ARCHITECTURE.md Section 6 (Open Questions) resolves the fine-grained auth join key as `token.sub` (Okta user email) vs `record.email`. Without this check, any authenticated user with `api-a:read` can read any other user's record.
- Enforcement points: route handler logic for `GET /api/users/:id` in API A. Check executes after scope validation passes. Admin group members (from `groups` claim) bypass the ownership check. Non-admin users where `token.sub != record.email` receive 403.

---

**INV-15: Every protected request to API B must append an entry to the in-memory audit_log — the entry must include timestamp, token sub, route, and outcome**
- Category: operational
- Why this matters: the audit_log is a first-class API B data model entity. It is self-populating during testing and is the content behind the `GET /api/audit-log` endpoint. A missing entry means the audit trail is incomplete.
- Enforcement points: API B auth middleware. The audit write occurs after the auth decision (pass or fail) — both outcomes are logged. The write is non-blocking (does not affect response time or error propagation).

---

**INV-16: All protected endpoints must return 401 Unauthorized if no Authorization header is present, the token is malformed, or the token is expired**
- Category: security
- Why this matters: unauthenticated requests to protected endpoints must be rejected before any application logic runs. The 401 response must include a structured JSON body: `{"error": "...", "message": "..."}`.
- Enforcement points: auth middleware in API A and API B. The middleware is applied before route handlers. FastAPI dependency injection (Depends) ensures no handler executes if middleware raises.

---

### Machine-to-Machine Flow

**INV-17: The M2M client credentials token request from API A must explicitly include scope=api-b:read in the request body — the scope must not be assumed to be granted automatically**
- Category: security
- Why this matters: ARCHITECTURE.md Section 6 (Open Questions) resolves this: the scope is not baked in at the application policy level — it must be explicitly requested in the token request body. If omitted, the issued token may have no scopes and will be rejected by API B.
- Enforcement points: M2M token fetch function in API A (`GET /api/internal/pull-analytics` trigger). The POST to Okta's token endpoint must include `scope=api-b:read` as a body parameter.

---

**INV-18: The M2M access token must be validated by API B using the same JWKS middleware as user-issued tokens — no special handling or bypass path exists for M2M tokens**
- Category: security
- Why this matters: the requirements brief explicitly states "API B validates this token using the same JWKS middleware — no special handling needed." A bypass path for M2M tokens would be a security regression: machine tokens could bypass scope or group checks.
- Enforcement points: API B auth middleware. No route decorator distinguishes between user-issued and M2M-issued tokens. Validation is purely signature + claims-based.

---

**INV-19: The M2M client secret must never appear in application code, logs, or API responses — it must be read exclusively from environment variables at startup**
- Category: security
- Why this matters: a hardcoded or logged client secret is a credential leak. It can be exfiltrated from version control, log aggregation, or API responses.
- Enforcement points: API A configuration loading. The secret is read from the `.env` file at startup via `os.environ` or a settings model. Code review must confirm no `print()`, structured log field, or response body contains the secret value. `.env` must be in `.gitignore`.

---

### CORS

**INV-20: Both APIs must reject any cross-origin request whose Origin header does not exactly match http://localhost:3000**
- Category: security
- Why this matters: wildcard CORS (`*`) allows any origin to make credentialed requests. In a real production deployment this would allow attacker-controlled sites to call the APIs with the user's token.
- Enforcement points: CORS middleware in API A and API B. The `allow_origins` list contains exactly `["http://localhost:3000"]`. Wildcard is explicitly not used. Pre-flight OPTIONS requests must return 200 with the correct headers before auth middleware runs.

---

### Error Handling & Information Leakage

**INV-21: No API endpoint may return a Python stack trace, exception message, or internal implementation detail in a response body**
- Category: security
- Why this matters: stack traces reveal file paths, library versions, and internal logic that aid an attacker in targeting vulnerabilities. All errors must return the structured format: `{"error": "...", "message": "..."}` with a safe, human-readable message.
- Enforcement points: FastAPI exception handlers in API A and API B. A global exception handler catches unhandled exceptions and returns the structured JSON format with a generic message. Auth errors use specific codes (401, 403) but safe messages only.

---

### Configuration & Secrets

**INV-22: All Okta credentials (Client ID, Client Secret, Okta domain, Authorization Server issuer URL) must be sourced from environment variables — no credential may be hardcoded in any source file**
- Category: security
- Why this matters: hardcoded credentials in source files are trivially exposed via version control. This is the most common real-world credential leak vector.
- Enforcement points: Both APIs and the frontend. Code review must confirm: no credential string literals in any `.py`, `.js`, `.jsx`, or `.ts` file. The `.env` file exists, is populated, and appears in `.gitignore`. The frontend uses Vite's `import.meta.env` pattern for public configuration values.

---

### Observability & Logging

**INV-23: Both APIs must emit a structured JSON log line for every auth decision — the log line must include: token subject (sub), requested route, required scope, and outcome (pass or fail)**
- Category: operational
- Why this matters: this is an explicit non-functional requirement from the brief. It is also the primary debugging tool when testing 401/403 scenarios. Without it, a failed auth test requires attaching a debugger to understand what went wrong.
- Enforcement points: auth middleware in API A and API B. The log write occurs after the auth decision. Outcome is `"pass"` or `"fail"`. The subject is the `sub` claim from the validated JWT (or `"anonymous"` if no token was present).

---

### UI Completeness

**INV-24: Every protected API endpoint in the system must have a corresponding button in the API Tester Panel — all endpoints enumerated in the requirements brief must be reachable from the UI**
- Category: operational
- Why this matters: the API Tester is the primary tool for running the Definition of Done scenarios. If an endpoint is not surfaced in the UI, the 401/403 test scenarios require Postman or curl — defeating the purpose of the frontend as a self-contained learning surface.
- Enforcement points: API Tester Panel component. Buttons present for all endpoints in Sections 5.1 and 5.2 of the requirements brief: `GET /api/users`, `GET /api/users/:id`, `POST /api/users`, `PUT /api/users/:id` (API A); `GET /api/analytics/summary`, `GET /api/config`, `POST /api/config`, `GET /api/audit-log` (API B).

---

**INV-25: The Token Inspector Panel must display all of the following for the current access token: decoded header (alg, kid), decoded payload (all claims including iss, sub, aud, exp, iat, scp, groups, department), live expiry countdown in seconds, and raw base64url segments**
- Category: operational
- Why this matters: the Token Inspector is described in the brief as "the single most important learning tool in the project." If any of these fields are missing, the panel fails its primary purpose as a concrete, visual representation of the JWT lifecycle.
- Enforcement points: Token Inspector Panel component. Each field is rendered independently. The expiry countdown updates every second. The panel is accessible from the Dashboard at all times when a valid access token is in memory.

---

**INV-26: The Token Refresh Demo Panel must display the access token claims before and after a silent refresh — the before state must remain visible during and after the refresh for comparison**
- Category: operational
- Why this matters: the before/after comparison is the visual proof that token rotation works. If the before state is overwritten immediately on refresh, the learning outcome (observing that a new token is issued with a new exp) is lost.
- Enforcement points: Token Refresh Demo Panel component. The before-state snapshot is taken when the user initiates the refresh and is held in component state independently of the current active token. Both are rendered simultaneously after refresh completes.

---

**INV-27: The API Tester Panel must render 401 and 403 responses visually distinctly from 200 responses — the HTTP status code and structured error body must both be visible**
- Category: operational
- Why this matters: the Definition of Done scenarios explicitly require observing 401 and 403 responses. If the panel renders all responses the same way, the user cannot confirm the correct behaviour without opening the browser devtools.
- Enforcement points: API Tester Panel component. Status codes 401 and 403 render with a visually distinct treatment (e.g. red/amber border or badge). The raw response body is always displayed below the status code.

---

## Invariant Index

| ID | Name | Category | Phase-critical |
|---|---|---|---|
| INV-01 | PKCE code_verifier never transmitted to server | security | yes |
| INV-02 | Access tokens in memory only | security | yes |
| INV-03 | Refresh tokens in sessionStorage or httpOnly cookie | security | yes |
| INV-04 | Silent refresh before rendering protected UI on page load | operational | yes |
| INV-05 | Proactive silent refresh 60s before expiry | operational | yes |
| INV-06 | Failed silent refresh triggers logout redirect | security | yes |
| INV-07 | Every protected endpoint validates JWT signature via JWKS | security | yes |
| INV-08 | JWKS keys cached in memory — no per-request fetch | operational | yes |
| INV-09 | Cache invalidated and re-fetched on kid mismatch | operational | yes |
| INV-10 | 60-second clock leeway on JWT validation | operational | yes |
| INV-11 | JWKS cache emits observable logs on all state transitions | operational | yes |
| INV-12 | Missing scope returns 403, not 401 | security | yes |
| INV-13 | api-b:admin scope alone insufficient for admin routes — group check required | security | yes |
| INV-14 | Fine-grained ownership check on GET /api/users/:id | security | yes |
| INV-15 | Every API B protected request appended to audit_log | operational | yes |
| INV-16 | All protected endpoints return 401 on missing/invalid/expired token | security | yes |
| INV-17 | M2M token request explicitly includes scope=api-b:read | security | yes |
| INV-18 | M2M tokens validated by same JWKS middleware — no bypass | security | yes |
| INV-19 | M2M client secret sourced from env vars only — never in code/logs/responses | security | yes |
| INV-20 | Both APIs reject cross-origin requests not from http://localhost:3000 | security | yes |
| INV-21 | No stack traces or internal details in API response bodies | security | yes |
| INV-22 | All Okta credentials from env vars — never hardcoded | security | yes |
| INV-23 | Both APIs log every auth decision as structured JSON | operational | yes |
| INV-24 | Every protected endpoint has a corresponding API Tester button | operational | yes |
| INV-25 | Token Inspector displays all required fields including live countdown | operational | yes |
| INV-26 | Token Refresh Demo shows before and after states simultaneously | operational | yes |
| INV-27 | API Tester visually distinguishes 401/403 from 200 | operational | yes |
| INV-28 | Frontend rejects callback if state parameter does not match — no bypass via SDK config | security | yes |

---

---

### CSRF / State Parameter

**INV-28: The frontend must not process an authorization code callback unless the state parameter in the callback exactly matches the state value generated at the start of the auth flow**
- Category: security
- Why this matters: the `state` parameter is the CSRF protection mechanism for the Auth Code flow. Without it, an attacker can craft a callback URL with a stolen authorization code and trick the app into exchanging it for tokens on the attacker's behalf.
- Enforcement points: Frontend callback handler. The `@okta/okta-auth-js` SDK handles this internally — the code review item is to confirm the SDK's state validation is not disabled or bypassed (e.g. no `ignoreSignature` or equivalent flag set in the Okta client configuration). Any callback where state is absent or mismatched must result in an error and redirect to the Login Page — not a silent failure.

---

## Engineer Sign-Off

> This section must be completed by the engineer before Phase 3 begins.

- [x] I have reviewed all 27 invariants
- [x] I confirm no invariant is a goal rather than a constraint
- [x] I confirm all enforcement points are specific and correct
- [x] I confirm the invariant set covers the ARCHITECTURE.md decisions and risks
- [x] I have authored or approved any changes to wording

**Signed off by:** Sandeep Polsani
**Date:** 22nd March 2026

---

*INVARIANTS.md — Okta Identity Lab v1.0 — Proposed*
