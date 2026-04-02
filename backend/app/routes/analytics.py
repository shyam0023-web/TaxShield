"""
TaxShield — Analytics Endpoint
Dashboard analytics: risk distribution, processing stats, approval rates.

Security: all queries are scoped to current_user.id.
Performance: results cached in Redis for 60s per user (falls back gracefully if Redis down).
"""
import asyncio
import json
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logger import logger
from app.models.notice import Notice
from app.models.audit_log import AuditLog
from app.models.user import User
from app.auth.deps import get_current_user

router = APIRouter()

ANALYTICS_CACHE_TTL = 60  # seconds — analytics don't need real-time precision


def _analytics_cache_key(user_id: str) -> str:
    return f"analytics:{user_id}"


async def _get_cached_analytics(user_id: str) -> dict | None:
    """Return cached analytics dict for this user, or None if not cached / Redis down."""
    try:
        from app.redis_client import get_redis
        redis = await get_redis()
        raw = await redis.get(_analytics_cache_key(user_id))
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.debug(f"Analytics cache read failed (non-fatal): {e}")
    return None


async def _set_cached_analytics(user_id: str, data: dict) -> None:
    """Write analytics dict to Redis with TTL. Silent on failure."""
    try:
        from app.redis_client import get_redis
        redis = await get_redis()
        await redis.setex(_analytics_cache_key(user_id), ANALYTICS_CACHE_TTL, json.dumps(data))
    except Exception as e:
        logger.debug(f"Analytics cache write failed (non-fatal): {e}")


@router.get("/analytics")
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dashboard analytics — risk distribution, processing stats, approval rates.
    Scoped to current user only. Cached per-user for 60 seconds.
    """
    # Check cache first
    cached = await _get_cached_analytics(current_user.id)
    if cached:
        logger.debug(f"Analytics cache hit for user {current_user.id}")
        return cached

    # Issue 4A: Scope all queries to this user only
    uid = current_user.id

    (
        total_result,
        risk_rows,
        status_rows,
        draft_rows,
        time_barred_result,
        avg_score_result,
        avg_demand_result,
        type_rows,
        audit_count_result,
    ) = await asyncio.gather(
        db.execute(select(func.count(Notice.id)).where(Notice.user_id == uid)),
        db.execute(select(Notice.risk_level, func.count(Notice.id)).where(Notice.user_id == uid).group_by(Notice.risk_level)),
        db.execute(select(Notice.status, func.count(Notice.id)).where(Notice.user_id == uid).group_by(Notice.status)),
        db.execute(select(Notice.draft_status, func.count(Notice.id)).where(Notice.user_id == uid).group_by(Notice.draft_status)),
        db.execute(select(func.count(Notice.id)).where(Notice.user_id == uid, Notice.is_time_barred == True)),
        db.execute(select(func.avg(Notice.verification_score)).where(Notice.user_id == uid, Notice.verification_score.isnot(None))),
        db.execute(select(func.avg(Notice.demand_amount)).where(Notice.user_id == uid, Notice.demand_amount > 0)),
        db.execute(select(Notice.notice_type, func.count(Notice.id)).where(Notice.user_id == uid).group_by(Notice.notice_type)),
        db.execute(select(func.count(AuditLog.id))),
    )

    total = total_result.scalar() or 0
    risk_distribution = {(row[0] or "UNKNOWN"): row[1] for row in risk_rows.all()}
    status_distribution = {(row[0] or "unknown"): row[1] for row in status_rows.all()}
    draft_distribution = {(row[0] or "pending"): row[1] for row in draft_rows.all()}
    time_barred = time_barred_result.scalar() or 0
    avg_score = avg_score_result.scalar()
    avg_demand = avg_demand_result.scalar()
    type_distribution = {(row[0] or "Unknown"): row[1] for row in type_rows.all()}
    audit_count = audit_count_result.scalar() or 0

    approved = draft_distribution.get("approved", 0)
    rejected = draft_distribution.get("rejected", 0)
    review_total = approved + rejected
    approval_rate = round((approved / review_total * 100), 1) if review_total > 0 else 0

    result = {
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

    # Write to cache (fire-and-forget, non-fatal)
    await _set_cached_analytics(current_user.id, result)

    return result
