"""
TaxShield — Notices Routes
Full CRUD for notices with SQLite persistence.
"""
import asyncio
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import graph
from app.database import get_db, AsyncSessionLocal
from app.logger import logger
from app.models.notice import Notice
from app.models.user import User
from app.auth.deps import get_current_user, require_role
from app.audit import log_audit
from app.middleware.rate_limiter import check_upload_rate

router = APIRouter()

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
ALLOWED_MIME_TYPES = {"application/pdf"}
ALLOWED_EXTENSIONS = {".pdf"}


# ═══════════════════════════════════════════
# POST /api/notices/upload — Upload & Process
# ═══════════════════════════════════════════

@router.post("/notices/upload")
async def upload_notice(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload PDF → Return 202 → Process pipeline in background."""

    # Per-user upload rate limit (stricter than global IP limit)
    await check_upload_rate(current_user.id)

    # Validate file extension
    filename = (file.filename or "").lower()
    if not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Validate MIME type
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Only PDF is accepted",
        )

    # Issue 14A: Read file in one shot — avoid O(n²) byte concatenation
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 25 MB")

    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    # Create notice record in DB (status=processing)
    base_name = file.filename or "notice"
    case_id = f"{base_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    now = datetime.utcnow()

    notice = Notice(
        case_id=case_id,
        filename=file.filename or "unknown.pdf",
        user_id=current_user.id,  # Issue 3A: Track notice owner
        status="processing",
        created_at=now,
        updated_at=now,
    )
    db.add(notice)
    await db.commit()
    await db.refresh(notice)
    notice_id = notice.id

    # Launch pipeline in the background (non-blocking)
    asyncio.create_task(
        _run_pipeline_background(notice_id, case_id, content, current_user.id, file.filename)
    )

    # Return 202 Accepted immediately — frontend polls GET /notices/{id}
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=202,
        content={
            "id": notice_id,
            "case_id": case_id,
            "status": "processing",
            "message": "Upload accepted. Pipeline is processing in background.",
        },
    )



PIPELINE_TIMEOUT_SECONDS = 120  # Max time for full pipeline (OCR → NER → Risk → Legal → Draft → Verify)


# ═══════════════════════════════════════════
# Pipeline Helpers — extracted for testability
# ═══════════════════════════════════════════

def _map_pipeline_state_to_notice(notice: Notice, final_state: dict) -> None:
    """
    Pure function: map all pipeline output fields onto a Notice model instance.
    No DB access, no IO — fully unit-testable.
    Mutates `notice` in place.
    """
    from app.utils import parse_llm_extracted, parse_demand_amount

    entities = final_state.get("entities", {})
    llm_extracted = parse_llm_extracted(entities)
    sections = entities.get("SECTIONS", [])

    notice.notice_text = final_state.get("raw_text", "")
    notice.entities = entities
    notice.notice_annotations = final_state.get("notice_annotations", [])
    notice.processing_status = final_state.get("processing_status", "unknown")
    notice.risk_level = final_state.get("risk_level", "UNKNOWN")
    notice.risk_score = float(final_state.get("risk_score", 0))
    notice.risk_reasoning = final_state.get("risk_reasoning", "")
    notice.is_time_barred = final_state.get("is_time_barred", False)
    notice.time_bar_detail = final_state.get("time_bar_detail")
    notice.fy = llm_extracted.get("financial_year", "")
    notice.section = sections[0] if sections else ""
    notice.notice_type = llm_extracted.get("notice_type", "")
    notice.demand_amount = parse_demand_amount(llm_extracted)
    notice.response_deadline = llm_extracted.get("response_deadline", "")
    notice.draft_reply = final_state.get("draft_reply", "")
    notice.draft_status = "draft_ready" if final_state.get("draft_reply") else "pending"
    notice.verification_status = final_state.get("verification_status")
    notice.verification_score = final_state.get("verification_score")
    notice.verification_issues = final_state.get("verification_issues")
    notice.accuracy_report = final_state.get("accuracy_report")
    notice.status = "processed"
    notice.updated_at = datetime.utcnow()


async def _mark_notice_error(notice_id: str, error: Exception) -> None:
    """
    Isolated error path: update notice status to 'error' in a fresh DB session.
    Uses its own session so a DB failure here doesn't swallow the original error.
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Notice).where(Notice.id == notice_id))
            notice = result.scalar_one_or_none()
            if notice:
                notice.status = "error"
                notice.error_message = str(error)
                notice.updated_at = datetime.utcnow()
                await db.commit()
    except Exception:
        logger.exception(f"Failed to mark notice {notice_id} as error — original error was: {error}")


async def _run_pipeline_background(
    notice_id: str,
    case_id: str,
    pdf_bytes: bytes,
    user_id: str,
    original_filename: str | None,
):
    """
    Orchestrate the 5-agent pipeline in the background, then persist results.
    Capped at PIPELINE_TIMEOUT_SECONDS to prevent zombie 'processing' notices.
    """
    try:
        initial_state = {
            "pdf_bytes": pdf_bytes,
            "case_id": case_id,
            "current_agent": "start",
        }

        try:
            final_state = await asyncio.wait_for(
                graph.ainvoke(initial_state),
                timeout=PIPELINE_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Pipeline timed out after {PIPELINE_TIMEOUT_SECONDS}s. "
                "This usually means a slow LLM response. Try uploading again."
            )

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Notice).where(Notice.id == notice_id))
            notice = result.scalar_one_or_none()
            if not notice:
                logger.error(f"Background pipeline: notice {notice_id} not found in DB")
                return

            _map_pipeline_state_to_notice(notice, final_state)

            await log_audit(
                db, action="upload", resource_type="notice", resource_id=notice_id,
                user=None, details={"filename": original_filename, "risk_level": notice.risk_level, "user_id": user_id},
            )
            await db.commit()
            logger.info(f"Background pipeline complete: notice={notice_id} risk={notice.risk_level}")

    except Exception as e:
        logger.exception(f"Background pipeline failed for notice {notice_id}")
        await _mark_notice_error(notice_id, e)



# ═══════════════════════════════════════════
# Notice Serialization Helpers (Issue 8A: DRY)
# ═══════════════════════════════════════════

def _serialize_notice_brief(n: Notice) -> dict:
    """Brief notice dict for list views."""
    return {
        "id": n.id,
        "case_id": n.case_id,
        "filename": n.filename,
        "notice_type": n.notice_type or "Unknown",
        "fy": n.fy or "",
        "section": n.section or "",
        "risk_level": n.risk_level or "UNKNOWN",
        "demand_amount": n.demand_amount or 0,
        "response_deadline": n.response_deadline or "",
        "draft_status": n.draft_status or "pending",
        "status": n.status,
        "is_time_barred": n.is_time_barred or False,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


def _serialize_notice_detail(n: Notice) -> dict:
    """Full notice dict for detail view — extends brief."""
    data = _serialize_notice_brief(n)
    data.update({
        "notice_text": n.notice_text or "",
        "entities": n.entities or {},
        "notice_annotations": n.notice_annotations or [],
        "processing_status": n.processing_status,
        "risk_score": n.risk_score or 0,
        "risk_reasoning": n.risk_reasoning or "",
        "time_bar_detail": n.time_bar_detail or {},
        "draft_reply": n.draft_reply or "",
        "verification_status": n.verification_status,
        "verification_score": n.verification_score,
        "verification_issues": n.verification_issues or [],
        "accuracy_report": n.accuracy_report or {},
        "error_message": n.error_message,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    })
    return data


# ═══════════════════════════════════════════
# GET /api/notices — List All Notices
# ═══════════════════════════════════════════

@router.get("/notices")
async def list_notices(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str = Query(None, description="Filter by status"),
    risk_level: str = Query(None, description="Filter by risk level"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get notices with pagination, ordered by most recent first."""
    from sqlalchemy import or_
    # Issue 3A: Filter by owner (also show legacy notices with no user_id)
    user_filter = or_(Notice.user_id == current_user.id, Notice.user_id.is_(None))

    # Base query
    query = select(Notice).where(user_filter).order_by(desc(Notice.created_at))
    count_query = select(func.count(Notice.id)).where(user_filter)

    # Filters
    if status:
        query = query.where(Notice.status == status)
        count_query = count_query.where(Notice.status == status)
    if risk_level:
        query = query.where(Notice.risk_level == risk_level)
        count_query = count_query.where(Notice.risk_level == risk_level)

    # Total count
    total = (await db.execute(count_query)).scalar() or 0

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    notices = result.scalars().all()

    return {
        "items": [_serialize_notice_brief(n) for n in notices],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


# ═══════════════════════════════════════════
# GET /api/notices/{id} — Get Notice Detail
# ═══════════════════════════════════════════

@router.get("/notices/{id}")
async def get_notice(id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get notice by ID with full details."""
    from sqlalchemy import or_
    result = await db.execute(
        select(Notice).where(
            Notice.id == id,
            or_(Notice.user_id == current_user.id, Notice.user_id.is_(None)),  # Issue 3A
        )
    )
    notice = result.scalar_one_or_none()

    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")

    return _serialize_notice_detail(notice)


# ═══════════════════════════════════════════
# GET /api/notifications — For Frontend Bell
# ═══════════════════════════════════════════

@router.get("/notifications")
async def list_notifications(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Generate notifications from recent notice activity."""
    from sqlalchemy import or_
    user_filter = or_(Notice.user_id == current_user.id, Notice.user_id.is_(None))
    result = await db.execute(
        select(Notice).where(user_filter).order_by(desc(Notice.updated_at)).limit(20)
    )
    notices = result.scalars().all()

    notifications = []
    for n in notices:
        # Draft ready notification
        if n.draft_status == "draft_ready":
            notifications.append({
                "id": f"draft_{n.id}",
                "type": "draft_ready",
                "title": "Draft Reply Generated",
                "message": f"Notice {n.case_id} draft is ready for review",
                "time": n.updated_at.isoformat() if n.updated_at else "",
                "read": False,
                "noticeId": n.id,
            })

        # Deadline approaching (if response_deadline exists)
        if n.response_deadline and n.draft_status != "approved":
            notifications.append({
                "id": f"deadline_{n.id}",
                "type": "deadline",
                "title": "Deadline Approaching",
                "message": f"Notice {n.case_id} — respond by {n.response_deadline}",
                "time": n.created_at.isoformat() if n.created_at else "",
                "read": False,
                "noticeId": n.id,
            })

        # High risk alert
        if n.risk_level == "HIGH":
            notifications.append({
                "id": f"risk_{n.id}",
                "type": "approval_pending",
                "title": "High Risk Notice",
                "message": f"Notice {n.case_id} classified as HIGH risk — requires attention",
                "time": n.created_at.isoformat() if n.created_at else "",
                "read": False,
                "noticeId": n.id,
            })

        # Processing error
        if n.status == "error":
            notifications.append({
                "id": f"error_{n.id}",
                "type": "info",
                "title": "Processing Failed",
                "message": f"Notice {n.case_id} — {n.error_message or 'unknown error'}",
                "time": n.updated_at.isoformat() if n.updated_at else "",
                "read": False,
                "noticeId": n.id,
            })

    return notifications


# ═══════════════════════════════════════════
# DELETE /api/notices/{id} — DPDP Right to Erasure
# ═══════════════════════════════════════════

@router.delete("/notices/{id}")
async def delete_notice(id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_role("admin", "ca"))):
    """
    Permanently delete a notice and all associated data.
    DPDP Act 2023 — Right to Erasure compliance.
    """
    from fastapi.responses import JSONResponse

    # Find the notice (Issue 3A: admin can delete any, CA can delete own)
    from sqlalchemy import or_
    result = await db.execute(
        select(Notice).where(
            Notice.id == id,
            or_(Notice.user_id == current_user.id, Notice.user_id.is_(None)),
        )
    )
    notice = result.scalar_one_or_none()

    if not notice:
        return JSONResponse(status_code=404, content={"detail": "Notice not found"})

    case_id = notice.case_id

    # Delete related drafts (table may not exist yet)
    drafts_deleted = 0
    try:
        from app.models.draft import Draft
        draft_result = await db.execute(select(Draft).where(Draft.notice_id == id))
        drafts = draft_result.scalars().all()
        for draft in drafts:
            await db.delete(draft)
        drafts_deleted = len(drafts)
    except Exception:
        pass  # drafts table may not exist — safe to ignore

    await db.delete(notice)

    # Issue 2A: Single atomic commit for delete + audit log
    await log_audit(
        db, action="delete", resource_type="notice", resource_id=id,
        user=current_user, details={"case_id": case_id, "drafts_deleted": drafts_deleted},
    )
    await db.commit()

    logger.info(f"DPDP Erasure: Deleted notice {id} (case_id={case_id}) and {drafts_deleted} related drafts")

    return {
        "deleted": True,
        "id": id,
        "case_id": case_id,
        "message": "Notice and all associated data permanently deleted",
    }
