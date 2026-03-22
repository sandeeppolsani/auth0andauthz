from fastapi import APIRouter, Depends

from app.auth import require_scope
from app.db import mock_db

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/api/analytics/summary")
def get_analytics_summary(claims: dict = Depends(require_scope("api-b:read"))):
    return mock_db.get_analytics()
