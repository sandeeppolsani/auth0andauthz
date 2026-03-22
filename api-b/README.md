# API B

FastAPI service — port **3002**. Provides analytics, config management, and audit log endpoints protected by Okta-issued JWTs. Admin routes require both a scope and group membership.

---

## Prerequisites

- Python 3.14+
- `.env` file populated (copy from `.env.example` if present, or set variables manually — see below)

**Required environment variables (`api-b/.env`):**

| Variable | Description |
|---|---|
| `OKTA_DOMAIN` | Your Okta domain, e.g. `dev-12345678.okta.com` |
| `OKTA_ISSUER` | Authorization server issuer URL |
| `OKTA_JWKS_URI` | JWKS endpoint, e.g. `https://<domain>/oauth2/<authServerId>/v1/keys` |
| `OKTA_AUDIENCE` | Token audience, e.g. `api://okta-lab` |

---

## Setup

```bash
cd api-b
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
> .venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 3002 --reload
> ```

Server starts at `http://localhost:3002`. Uvicorn runs in `--reload` mode.

---

## Endpoints

| Method | Path | Auth required | Required scope | Required group |
|--------|------|---------------|----------------|----------------|
| GET | `/health` | None | — | — |
| GET | `/api/analytics/summary` | Bearer JWT | `api-b:read` | — |
| GET | `/api/config` | Bearer JWT | `api-b:admin` | `api-b-admins` |
| POST | `/api/config` | Bearer JWT | `api-b:admin` | `api-b-admins` |
| GET | `/api/audit-log` | Bearer JWT | `api-b:admin` | `api-b-admins` |

Admin routes enforce **scope then group** in that order. A token with the correct group but missing `api-b:admin` scope returns 403 `insufficient_scope`. A token with the correct scope but not in `api-b-admins` returns 403 `insufficient_privileges`.

Every protected request (pass or fail) appends an entry to the in-memory audit log.

---

## Error responses

All error responses use the structure:

```json
{"error": "<code>", "message": "<human-readable message>"}
```

| Status | Meaning |
|--------|---------|
| 401 | Missing, malformed, or expired token |
| 403 | Valid token but missing required scope or group membership |
| 500 | Unexpected server error (no internal detail exposed) |

---

## Running tests

```bash
cd api-b
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pytest tests/ -v
```
