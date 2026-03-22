import json
import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter

from app.auth.m2m import fetch_m2m_token

router = APIRouter()


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return record.getMessage()


_handler = logging.StreamHandler()
_handler.setFormatter(_JsonFormatter())

logger = logging.getLogger(__name__)
logger.addHandler(_handler)
logger.setLevel(logging.INFO)
logger.propagate = False


def _log(outcome: str) -> None:
    logger.info(
        json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "subject": "api-a-m2m",
                "route": "/api/internal/pull-analytics",
                "required_scope": "api-b:read",
                "outcome": outcome,
            }
        )
    )


@router.get("/api/internal/pull-analytics")
async def pull_analytics():
    m2m_token = await fetch_m2m_token()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "http://localhost:3002/api/analytics/summary",
                headers={"Authorization": f"Bearer {m2m_token}"},
                timeout=10,
            )
        except httpx.RequestError:
            _log("fail:api_b_unreachable")
            return {"source": "api-b", "error": 503, "message": "API B call failed"}

    if response.status_code == 200:
        _log("pass")
        return {"source": "api-b", "data": response.json()}

    _log(f"fail:http_{response.status_code}")
    return {"source": "api-b", "error": response.status_code, "message": "API B call failed"}
