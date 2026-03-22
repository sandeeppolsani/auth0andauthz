from fastapi import APIRouter, Depends

from app.auth import require_group, require_scope
from app.db import mock_db

router = APIRouter()


@router.get("/api/audit-log")
def get_audit_log(
    _scope: dict = Depends(require_scope("api-b:admin")),
    claims: dict = Depends(require_group("api-b-admins")),
):
    return mock_db.get_audit_log()
