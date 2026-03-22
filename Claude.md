# Claude.md — v1.1 · FROZEN · March 2026

---

## 1. System Intent

A self-contained learning laboratory for Okta-based OAuth 2.0 / OIDC authentication and authorisation, running fully on localhost. It consists of a React SPA, two independent FastAPI services (API A on 3001, API B on 3002), and an Okta developer tenant — no shared code, no shared database, no cloud deployment. Success means the engineer can add auth to a new API endpoint in under 5 minutes without reference material.

---

## 2. Hard Invariants

INVARIANT: The PKCE code_verifier is generated in the browser, used directly against the Okta token endpoint, and never forwarded to API A or API B. This is never negotiable.

INVARIANT: Access tokens are stored exclusively in React component state (JavaScript memory). No write to localStorage, sessionStorage, cookies, or any persistent storage ever occurs for access tokens. This is never negotiable.

INVARIANT: Refresh tokens are stored in an httpOnly cookie. They are not held in JavaScript memory. This is never negotiable.

INVARIANT: On every page load, the frontend attempts silent token refresh before rendering any protected route. If refresh fails, the user is redirected to the Login Page. This is never negotiable.

INVARIANT: A proactive silent refresh timer fires at `exp − 60 seconds`. The timer is reset after every successful refresh, not only after login. This is never negotiable.

INVARIANT: If silent refresh fails for any reason, the session ends: refresh token is cleared and the user is redirected to the Login Page. No silent continuation of a broken session. This is never negotiable.

INVARIANT: Every protected endpoint in API A and API B validates the JWT signature against JWKS. No protected endpoint bypasses signature verification. Health endpoints are explicitly excluded. This is never negotiable.

INVARIANT: JWKS public keys are cached in memory with a 10-minute TTL. No JWKS HTTP fetch occurs on a per-request basis. This is never negotiable.

INVARIANT: On a JWT signature failure caused by an unrecognised `kid`, the JWKS cache is invalidated and re-fetched before returning 401. This invalidation path is triggered only on `kid` mismatch or signature failure — not on `exp` or other claim failures. This is never negotiable.

INVARIANT: JWT validation applies `leeway=60` seconds on all `jwt.decode()` calls in both API A and API B. This is never negotiable.

INVARIANT: The JWKS cache emits structured JSON log lines on every state transition: JWKS_CACHE_MISS, JWKS_CACHE_HIT, JWKS_KID_NOT_FOUND, JWKS_CACHE_INVALIDATED_REFETCH, JWKS_CACHE_REFRESHED. All events are observable without a debugger. This is never negotiable.

INVARIANT: A valid JWT with a missing required scope returns 403 Forbidden, not 401 Unauthorized. 401 is reserved for missing, malformed, or expired tokens only. This is never negotiable.

INVARIANT: API B admin routes (`GET /api/config`, `POST /api/config`, `GET /api/audit-log`) require both `api-b:admin` scope AND membership in the `api-b-admins` group. Scope alone is insufficient. This is never negotiable.

INVARIANT: `GET /api/users/{email}` in API A compares `token.sub` to `record.email`. Non-admin users receive 403 when requesting any record that is not their own. Members of `api-b-admins` bypass this check. This is never negotiable.

INVARIANT: Every protected request to API B — pass or fail — appends an entry to the in-memory `audit_log` with: timestamp, subject (token `sub`), route, and outcome. This write occurs in the auth middleware, not in route handlers. This is never negotiable.

INVARIANT: All protected endpoints return 401 with a structured JSON body `{"error": "...", "message": "..."}` when the Authorization header is absent, the token is malformed, or the token is expired. This is never negotiable.

INVARIANT: The M2M client credentials POST from API A to the Okta token endpoint explicitly includes `scope=api-b:read` in the request body. The scope is never assumed to be auto-granted. This is never negotiable.

INVARIANT: API B validates M2M tokens through the same JWKS middleware as user tokens. No special handling, no bypass path exists for M2M-issued tokens. This is never negotiable.

INVARIANT: The M2M client secret is read exclusively from environment variables at startup. It never appears in source code, log output, or API response bodies. This is never negotiable.

INVARIANT: Both APIs permit cross-origin requests only from `http://localhost:3000`. The `allow_origins` list is exactly `["http://localhost:3000"]` — no wildcard, no additional origins. OPTIONS preflight returns 200. This is never negotiable.

INVARIANT: No API endpoint returns a Python stack trace, exception message, or internal implementation detail. All errors return `{"error": "...", "message": "..."}` with a safe human-readable message. This is never negotiable.

INVARIANT: All Okta credentials (Client ID, Client Secret, domain, issuer URL, JWKS URI, token endpoint) are sourced from `.env` files via environment variables. No credential string literal appears in any `.py`, `.js`, `.jsx`, or `.ts` file. `.env` is in `.gitignore`. This is never negotiable.

INVARIANT: Both APIs emit a structured JSON log line for every auth decision containing: timestamp, `sub`, route, required scope, and outcome (`pass` or `fail`). This is never negotiable.

INVARIANT: The API Tester Panel contains a button for every protected endpoint in the system: `GET /api/users`, `GET /api/users/:id`, `POST /api/users`, `PUT /api/users/:id` (API A); `GET /api/analytics/summary`, `GET /api/config`, `POST /api/config`, `GET /api/audit-log` (API B). This is never negotiable.

INVARIANT: The Token Inspector Panel displays: decoded header (`alg`, `kid`), decoded payload (all claims including `iss`, `sub`, `aud`, `exp`, `iat`, `scp`, `groups`, `department`), a live expiry countdown updating every second, and raw base64url segments. All fields are present. This is never negotiable.

INVARIANT: The Token Refresh Demo Panel captures the before-state snapshot before calling `renew()`. Both before and after states are displayed simultaneously after refresh completes. The before state is never overwritten or cleared on success. This is never negotiable.

INVARIANT: The API Tester Panel renders 401 and 403 responses with visually distinct treatment from 200. HTTP status code and structured response body are both visible for every response. This is never negotiable.

INVARIANT: The frontend does not process an authorization code callback unless the `state` parameter matches the value generated at the start of the flow. The `@okta/okta-auth-js` SDK state validation is not disabled or bypassed — no `ignoreSignature` or equivalent flag is set. This is never negotiable.

---

## 3. Scope Boundary

**CC may create or modify:**
- `api-a/app/**/*.py` and `api-a/app/main.py`
- `api-b/app/**/*.py` and `api-b/app/main.py`
- `api-a/requirements.txt`, `api-b/requirements.txt`
- `api-a/run.sh`, `api-b/run.sh`
- `api-a/README.md`, `api-b/README.md`
- `api-a/.env.example`, `api-b/.env.example`
- `frontend/src/**/*.jsx`, `frontend/src/**/*.js`, `frontend/src/**/*.css`
- `frontend/.env.example`
- `scripts/test_cors.sh`, `scripts/test_jwks_rotation.sh`
- `.gitignore`, root `README.md`
- `VERIFICATION_CHECKLIST.md`

**CC must not:**
- Create a shared `packages/` or common auth module imported by both APIs
- Modify or read from `api-a/.env` or `api-b/.env` or `frontend/.env` (real secrets)
- Install packages beyond those listed in Fixed Stack
- Write any Okta credential value into any source file
- Use `localStorage` for any token storage
- Add `ignoreSignature`, `disableHttpsCheck`, or any SDK bypass flag
- Create any database process, SQLite file, or external storage — in-memory dicts only
- Deploy to any remote environment or add cloud configuration

**Conflict rule:** If a task prompt conflicts with any invariant, the invariant wins. Flag the conflict immediately — never resolve it silently.

---

## 4. Fixed Stack

| Layer | Technology | Version |
|---|---|---|
| API A & B | Python | 3.14+ |
| API framework | FastAPI | 0.111.0 |
| ASGI server | Uvicorn | 0.30.0 (with `[standard]`) |
| JWT validation | python-jose | 3.3.0 (with `[cryptography]`) |
| HTTP client (JWKS + M2M) | httpx | 0.27.0 |
| Env loading | python-dotenv | 1.0.1 |
| Frontend framework | React | 18 |
| Frontend build | Vite | latest via `npm create vite@latest` |
| Okta React SDK | @okta/okta-react | latest compatible |
| Okta auth JS SDK | @okta/okta-auth-js | latest compatible |
| Routing | react-router-dom | latest compatible |
| Identity Provider | Okta Developer (developer.okta.com) | — |

**Ports:** Frontend → 3000, API A → 3001, API B → 3002

**Environment variable names (exact):**

*api-a/.env:*
`OKTA_DOMAIN`, `OKTA_ISSUER`, `OKTA_JWKS_URI`, `OKTA_AUDIENCE`, `OKTA_CLIENT_ID`, `OKTA_CLIENT_SECRET`, `OKTA_TOKEN_ENDPOINT`, `IS_DEV`

*api-b/.env:*
`OKTA_DOMAIN`, `OKTA_ISSUER`, `OKTA_JWKS_URI`, `OKTA_AUDIENCE`

*frontend/.env:*
`VITE_OKTA_DOMAIN`, `VITE_OKTA_CLIENT_ID`, `VITE_OKTA_ISSUER`, `VITE_OKTA_REDIRECT_URI`

**Okta application names:** `okta-lab-spa`, `okta-lab-api-a`, `okta-lab-api-b`
**Authorization Server:** name `okta-lab-authserver`, audience `api://okta-lab`
**Custom scopes:** `api-a:read`, `api-a:write`, `api-b:read`, `api-b:admin`, `offline_access`
**Groups:** `api-a-users`, `api-b-viewers`, `api-b-admins`
**Test users:** `alice@example.com`, `admin@example.com`
**Fine-grained auth join key:** `token.sub` (Okta user email) matched against `record.email`
**JWKS cache TTL:** 600 seconds
**JWT clock leeway:** 60 seconds
**Proactive refresh lead time:** 60 seconds before `exp`
**No external JWT decode library in the frontend** — use `atob()` on base64url segments directly
