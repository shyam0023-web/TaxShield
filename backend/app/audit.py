"""
TaxShield — Audit Logger
Helper to record compliance trail entries from any route.
"""
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


async def log_audit(
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    user=None,
    details: dict | None = None,
    ip_address: str | None = None,
):
    """
    Create an audit trail entry.

    Args:
        db: Database session
        action: What happened (upload, approve, reject, delete, login, register)
        resource_type: What kind of resource (notice, draft, user)
        resource_id: ID of the affected resource
        user: User object (from get_current_user dependency)
        details: Extra context (filename, old/new values, etc.)
        ip_address: Client IP address
    """
    entry = AuditLog(
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        user_role=user.role if user else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)

    logger.info(
        f"AUDIT: {action} {resource_type}"
        f" by={user.email if user else 'system'}"
        f" resource={resource_id}"
    )
