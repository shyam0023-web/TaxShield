"""
TaxShield — Drafts Routes
Approve, reject, and edit AI-generated draft replies.
Drafts live on the Notice model (draft_reply + draft_status).
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logger import logger
from app.models.notice import Notice
from app.models.user import User
from app.auth.deps import get_current_user
from app.audit import log_audit

router = APIRouter()


class DraftApproval(BaseModel):
    feedback: Optional[str] = None


class DraftEdit(BaseModel):
    draft_reply: str
    feedback: Optional[str] = None


# ═══════════════════════════════════════════
# POST /api/notices/{id}/approve
# ═══════════════════════════════════════════

@router.post("/notices/{id}/approve")
async def approve_draft(id: str, body: DraftApproval, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Mark a draft reply as approved by the CA."""
    result = await db.execute(select(Notice).where(Notice.id == id))
    notice = result.scalar_one_or_none()

    if not notice:
        return JSONResponse(status_code=404, content={"detail": "Notice not found"})

    if not notice.draft_reply:
        return JSONResponse(status_code=400, content={"detail": "No draft to approve"})

    notice.draft_status = "approved"
    notice.updated_at = datetime.utcnow()

    # Issue 6A: Single atomic commit for notice + audit log
    await log_audit(
        db, action="approve", resource_type="draft", resource_id=id,
        user=current_user, details={"case_id": notice.case_id, "feedback": body.feedback},
    )
    await db.commit()

    logger.info(f"Draft approved for notice {id} (case_id={notice.case_id})")

    return {
        "id": notice.id,
        "case_id": notice.case_id,
        "draft_status": "approved",
        "feedback": body.feedback,
    }


# ═══════════════════════════════════════════
# POST /api/notices/{id}/reject
# ═══════════════════════════════════════════

@router.post("/notices/{id}/reject")
async def reject_draft(id: str, body: DraftApproval, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Reject a draft reply. Optionally provide feedback."""
    result = await db.execute(select(Notice).where(Notice.id == id))
    notice = result.scalar_one_or_none()

    if not notice:
        return JSONResponse(status_code=404, content={"detail": "Notice not found"})

    if not notice.draft_reply:
        return JSONResponse(status_code=400, content={"detail": "No draft to reject"})

    notice.draft_status = "rejected"
    notice.updated_at = datetime.utcnow()

    # Issue 6A: Single atomic commit for notice + audit log
    await log_audit(
        db, action="reject", resource_type="draft", resource_id=id,
        user=current_user, details={"case_id": notice.case_id, "feedback": body.feedback},
    )
    await db.commit()

    logger.info(f"Draft rejected for notice {id} (case_id={notice.case_id}), feedback: {body.feedback}")

    return {
        "id": notice.id,
        "case_id": notice.case_id,
        "draft_status": "rejected",
        "feedback": body.feedback,
    }


# ═══════════════════════════════════════════
# PUT /api/notices/{id}/draft
# ═══════════════════════════════════════════

@router.put("/notices/{id}/draft")
async def update_draft(id: str, body: DraftEdit, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Edit the draft reply text. Resets status to draft_ready."""
    result = await db.execute(select(Notice).where(Notice.id == id))
    notice = result.scalar_one_or_none()

    if not notice:
        return JSONResponse(status_code=404, content={"detail": "Notice not found"})

    notice.draft_reply = body.draft_reply
    notice.draft_status = "draft_ready"
    notice.updated_at = datetime.utcnow()
    await db.commit()

    logger.info(f"Draft edited for notice {id} (case_id={notice.case_id})")

    return {
        "id": notice.id,
        "case_id": notice.case_id,
        "draft_status": "draft_ready",
        "draft_reply": notice.draft_reply,
    }
