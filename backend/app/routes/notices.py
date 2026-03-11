"""
TaxShield — Notices Routes
Full CRUD for notices with SQLite persistence.
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import graph
from app.database import get_db
from app.logger import logger
from app.models.notice import Notice

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
):
    """Upload PDF → Run 4-agent pipeline → Save to DB"""

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

    # Read with size limit
    content = b""
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        content += chunk
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 25 MB")

    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    # Create notice record in DB (status=processing)
    case_id = file.filename or f"notice_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    now = datetime.utcnow()

    notice = Notice(
        case_id=case_id,
        filename=file.filename or "unknown.pdf",
        status="processing",
        created_at=now,
        updated_at=now,
    )
    db.add(notice)
    await db.commit()
    await db.refresh(notice)
    notice_id = notice.id

    # Run the agent pipeline
    initial_state = {
        "pdf_bytes": content,
        "case_id": case_id,
        "current_agent": "start",
    }

    try:
        final_state = await graph.ainvoke(initial_state)
    except Exception as e:
        logger.exception("Agent pipeline failed")
        # Update notice with error
        notice.status = "error"
        notice.error_message = str(e)
        notice.updated_at = datetime.utcnow()
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    # Extract derived fields from entities
    entities = final_state.get("entities", {})
    llm_extracted = entities.get("llm_extracted", {})
    if isinstance(llm_extracted, str):
        try:
            llm_extracted = json.loads(llm_extracted)
        except json.JSONDecodeError:
            llm_extracted = {}

    # Parse demand amount
    demand_amount = 0.0
    raw_demand = llm_extracted.get("demand_amount")
    if isinstance(raw_demand, dict):
        demand_amount = float(raw_demand.get("total", 0) or 0)
    elif isinstance(raw_demand, (int, float)):
        demand_amount = float(raw_demand)

    # Get primary section
    sections = entities.get("SECTIONS", [])
    primary_section = sections[0] if sections else ""

    # Update notice with pipeline results
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
    notice.section = primary_section
    notice.notice_type = llm_extracted.get("notice_type", "")
    notice.demand_amount = demand_amount
    notice.response_deadline = llm_extracted.get("response_deadline", "")
    notice.draft_reply = final_state.get("draft_reply", "")
    notice.draft_status = "draft_ready" if final_state.get("draft_reply") else "pending"
    notice.status = "processed"
    notice.updated_at = datetime.utcnow()

    await db.commit()

    return {
        "id": notice_id,
        "case_id": case_id,
        "risk_level": notice.risk_level,
        "status": "processed",
        "draft_status": notice.draft_status,
    }


# ═══════════════════════════════════════════
# GET /api/notices — List All Notices
# ═══════════════════════════════════════════

@router.get("/notices")
async def list_notices(db: AsyncSession = Depends(get_db)):
    """Get all notices, ordered by most recent first."""
    result = await db.execute(
        select(Notice).order_by(desc(Notice.created_at))
    )
    notices = result.scalars().all()

    return [
        {
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
        for n in notices
    ]


# ═══════════════════════════════════════════
# GET /api/notices/{id} — Get Notice Detail
# ═══════════════════════════════════════════

@router.get("/notices/{id}")
async def get_notice(id: str, db: AsyncSession = Depends(get_db)):
    """Get notice by ID with full details."""
    result = await db.execute(select(Notice).where(Notice.id == id))
    notice = result.scalar_one_or_none()

    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")

    return {
        "id": notice.id,
        "case_id": notice.case_id,
        "filename": notice.filename,
        "notice_text": notice.notice_text or "",
        "entities": notice.entities or {},
        "notice_annotations": notice.notice_annotations or [],
        "processing_status": notice.processing_status,
        "risk_level": notice.risk_level or "UNKNOWN",
        "risk_score": notice.risk_score or 0,
        "risk_reasoning": notice.risk_reasoning or "",
        "is_time_barred": notice.is_time_barred or False,
        "time_bar_detail": notice.time_bar_detail or {},
        "fy": notice.fy or "",
        "section": notice.section or "",
        "notice_type": notice.notice_type or "Unknown",
        "demand_amount": notice.demand_amount or 0,
        "response_deadline": notice.response_deadline or "",
        "draft_reply": notice.draft_reply or "",
        "draft_status": notice.draft_status or "pending",
        "status": notice.status,
        "error_message": notice.error_message,
        "created_at": notice.created_at.isoformat() if notice.created_at else None,
        "updated_at": notice.updated_at.isoformat() if notice.updated_at else None,
    }


# ═══════════════════════════════════════════
# GET /api/notifications — For Frontend Bell
# ═══════════════════════════════════════════

@router.get("/notifications")
async def list_notifications(db: AsyncSession = Depends(get_db)):
    """Generate notifications from recent notice activity."""
    result = await db.execute(
        select(Notice).order_by(desc(Notice.updated_at)).limit(20)
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
