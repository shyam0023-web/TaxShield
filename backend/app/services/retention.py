"""
TaxShield — Data Retention Service
DPDP Act, 2023 Compliance: auto-delete notices and drafts after 90 days.
Runs as a background task alongside the server.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

RETENTION_DAYS = 90


async def run_retention_cleanup(db: AsyncSession) -> dict:
    """
    Delete notices and associated data older than 90 days.
    Returns summary of what was deleted.
    """
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    logger.info(f"Running retention cleanup: deleting data before {cutoff.date()}")

    deleted = {"notices": 0, "drafts": 0}

    try:
        # Import models here to avoid circular imports
        from app.models.notice import Notice
        from app.models.draft import Draft
        from app.models.case import Case

        # Find notices older than cutoff
        result = await db.execute(
            select(Notice).where(Notice.created_at < cutoff)
        )
        old_notices = result.scalars().all()
        old_notice_ids = [n.id for n in old_notices]

        if old_notice_ids:
            # Delete associated drafts
            draft_result = await db.execute(
                delete(Draft).where(Draft.notice_id.in_(old_notice_ids))
            )
            deleted["drafts"] = draft_result.rowcount

            # Delete associated cases
            await db.execute(
                delete(Case).where(Case.notice_id.in_(old_notice_ids))
            )

            # Delete notices
            notice_result = await db.execute(
                delete(Notice).where(Notice.id.in_(old_notice_ids))
            )
            deleted["notices"] = notice_result.rowcount

        await db.commit()

        logger.info(
            f"Retention cleanup complete: "
            f"{deleted['notices']} notices, {deleted['drafts']} drafts deleted"
        )
        return {"status": "ok", "cutoff": str(cutoff.date()), **deleted}

    except Exception as e:
        await db.rollback()
        logger.error(f"Retention cleanup failed: {e}")
        return {"status": "error", "detail": str(e)}
