"""
TaxShield — Analytics Endpoint
Dashboard analytics: risk distribution, processing stats, approval rates.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.notice import Notice
from app.models.audit_log import AuditLog
from app.models.user import User
from app.auth.deps import get_current_user

router = APIRouter()


@router.get("/analytics")
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dashboard analytics — risk distribution, processing stats, approval rates."""

    # Total notices
    total = (await db.execute(select(func.count(Notice.id)))).scalar() or 0

    # Risk distribution
    risk_query = select(Notice.risk_level, func.count(Notice.id)).group_by(Notice.risk_level)
    risk_rows = (await db.execute(risk_query)).all()
    risk_distribution = {(row[0] or "UNKNOWN"): row[1] for row in risk_rows}

    # Status distribution
    status_query = select(Notice.status, func.count(Notice.id)).group_by(Notice.status)
    status_rows = (await db.execute(status_query)).all()
    status_distribution = {(row[0] or "unknown"): row[1] for row in status_rows}

    # Draft status distribution
    draft_query = select(Notice.draft_status, func.count(Notice.id)).group_by(Notice.draft_status)
    draft_rows = (await db.execute(draft_query)).all()
    draft_distribution = {(row[0] or "pending"): row[1] for row in draft_rows}

    # Approval rate
    approved = draft_distribution.get("approved", 0)
    rejected = draft_distribution.get("rejected", 0)
    review_total = approved + rejected
    approval_rate = round((approved / review_total * 100), 1) if review_total > 0 else 0

    # Time-barred count
    time_barred = (await db.execute(
        select(func.count(Notice.id)).where(Notice.is_time_barred == True)
    )).scalar() or 0

    # Average verification score
    avg_score = (await db.execute(
        select(func.avg(Notice.verification_score)).where(Notice.verification_score.isnot(None))
    )).scalar()

    # Average demand amount
    avg_demand = (await db.execute(
        select(func.avg(Notice.demand_amount)).where(Notice.demand_amount > 0)
    )).scalar()

    # Notice type distribution
    type_query = select(Notice.notice_type, func.count(Notice.id)).group_by(Notice.notice_type)
    type_rows = (await db.execute(type_query)).all()
    type_distribution = {(row[0] or "Unknown"): row[1] for row in type_rows}

    # Audit activity (last 30 days)
    audit_count = (await db.execute(select(func.count(AuditLog.id)))).scalar() or 0

    return {
        "total_notices": total,
        "risk_distribution": risk_distribution,
        "status_distribution": status_distribution,
        "draft_distribution": draft_distribution,
        "approval_rate": approval_rate,
        "time_barred_count": time_barred,
        "avg_verification_score": round(avg_score, 2) if avg_score else None,
        "avg_demand_amount": round(avg_demand, 2) if avg_demand else None,
        "type_distribution": type_distribution,
        "total_audit_events": audit_count,
    }
