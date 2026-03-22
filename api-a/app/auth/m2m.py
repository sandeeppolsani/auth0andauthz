import json
import logging
import os
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return record.getMessage()


_handler = logging.StreamHandler()
_handler.setFormatter(_JsonFormatter())

logger = logging.getLogger(__name__)
logger.addHandler(_handler)
logger.setLevel(logging.INFO)
logger.propagate = False


def _log(event: str, outcome: str) -> None:
    logger.info(
        json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "subject": "api-a-m2m",
                "scope": "api-b:read",
                "outcome": outcome,
            }
        )
    )


async def fetch_m2m_token() -> str:
    """
    Fetch a client credentials access token from Okta for API-to-API calls.
    Returns the raw access token string.
    Raises HTTPException(503) if the token endpoint call fails.
    """
    client_id = os.environ["OKTA_CLIENT_ID"]
    client_secret = os.environ["OKTA_CLIENT_SECRET"]
    token_endpoint = os.environ["OKTA_TOKEN_ENDPOINT"]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_endpoint,
            data={
                "grant_type": "client_credentials",
                "scope": "api-b:read",  # explicit — INV-17
            },
            auth=(client_id, client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )

    if response.status_code != 200:
        # Log the HTTP status only — never log the secret or token value (INV-19)
        _log("m2m_token_fetch", f"fail:http_{response.status_code}")
        raise HTTPException(
            status_code=503,
            detail={"error": "m2m_token_error", "message": "Failed to obtain M2M token"},
        )

    _log("m2m_token_fetch", "pass")
    return response.json()["access_token"]
