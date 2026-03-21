"""
TaxShield — Audit Logs Route
GET /api/audit-logs — Admin-only compliance trail viewer.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.auth.deps import require_role

router = APIRouter()


@router.get("/audit-logs")
async def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action (upload, approve, reject, delete)"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type (notice, draft, user)"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    List audit trail entries. Admin-only.
    Supports filtering by action and resource type.
    """
    query = select(AuditLog).order_by(desc(AuditLog.created_at))

    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)

    query = query.limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "user_email": log.user_email,
            "user_role": log.user_role,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
