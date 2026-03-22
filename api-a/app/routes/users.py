from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_scope, verify_token
from app.db import mock_db

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/api/users")
def get_all_users(claims: dict = Depends(require_scope("api-a:read"))):
    return mock_db.get_all_users()


@router.get("/api/users/{user_email}")
def get_user(user_email: str, claims: dict = Depends(require_scope("api-a:read"))):
    # Fine-grained ownership check (INV-14)
    token_sub = claims.get("sub", "")
    groups = claims.get("groups", [])
    is_admin = "api-b-admins" in groups

    if not is_admin and token_sub != user_email:
        raise HTTPException(
            status_code=403,
            detail={"error": "insufficient_scope", "message": "Access denied: you may only access your own record"},
        )

    user = mock_db.get_user_by_email(user_email)
    if user is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"User {user_email} not found"},
        )
    return user


@router.post("/api/users", status_code=201)
def create_user(body: dict, claims: dict = Depends(require_scope("api-a:write"))):
    try:
        created = mock_db.create_user(body)
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "conflict", "message": str(exc)},
        )
    return created


@router.put("/api/users/{user_email}")
def update_user(user_email: str, body: dict, claims: dict = Depends(require_scope("api-a:write"))):
    updated = mock_db.update_user(user_email, body)
    if updated is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"User {user_email} not found"},
        )
    return updated
