# API A

FastAPI service — port **3001**. Provides user management endpoints protected by Okta-issued JWTs.

---

## Prerequisites

- Python 3.14+
- `.env` file populated (copy from `.env.example` if present, or set variables manually — see below)

**Required environment variables (`api-a/.env`):**

| Variable | Description |
|---|---|
| `OKTA_DOMAIN` | Your Okta domain, e.g. `dev-12345678.okta.com` |
| `OKTA_ISSUER` | Authorization server issuer URL |
| `OKTA_JWKS_URI` | JWKS endpoint, e.g. `https://<domain>/oauth2/<authServerId>/v1/keys` |
| `OKTA_AUDIENCE` | Token audience, e.g. `api://okta-lab` |
| `OKTA_CLIENT_ID` | Client ID for the `okta-lab-api-a` application |
| `OKTA_CLIENT_SECRET` | Client secret for M2M token requests |
| `OKTA_TOKEN_ENDPOINT` | Token endpoint URL |
| `IS_DEV` | Set to `true` for development |

---

## Setup

```bash
cd api-a
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Run

```bash
./run.sh
```

> **Windows note:** `run.sh` uses `.venv/Scripts/python`. Run it from Git Bash.
>
> **Windows CRLF note:** If `.env` was created or edited on Windows it may have CRLF line endings, causing `source .env` to append `\r` to every variable value. If env vars appear unset, source manually first:
> ```bash
> source <(tr -d '\r' < .env)
> .venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 3001 --reload
> ```

Server starts at `http://localhost:3001`. Uvicorn runs in `--reload` mode.

---

## Endpoints

| Method | Path | Auth required | Required scope |
|--------|------|---------------|----------------|
| GET | `/health` | None | — |
| GET | `/api/users` | Bearer JWT | `api-a:read` |
| GET | `/api/users/{user_email}` | Bearer JWT | `api-a:read` + ownership* |
| POST | `/api/users` | Bearer JWT | `api-a:write` |
| PUT | `/api/users/{user_email}` | Bearer JWT | `api-a:write` |

\* `GET /api/users/{user_email}` enforces `token.sub == user_email`. Members of the `api-b-admins` group bypass this check.

---

## Error responses

All error responses use the structure:

```json
{"error": "<code>", "message": "<human-readable message>"}
```

| Status | Meaning |
|--------|---------|
| 401 | Missing, malformed, or expired token |
| 403 | Valid token but missing required scope or ownership check failed |
| 404 | User record not found |
| 409 | Duplicate email on POST |
| 500 | Unexpected server error (no internal detail exposed) |

---

## Running tests

```bash
cd api-a
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pytest tests/ -v
```
