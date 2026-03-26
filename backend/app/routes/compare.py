"""
TaxShield — Notice Comparison Endpoint
Compare multiple notices side-by-side on key fields.
Inspired by Legora's Tabular Review feature.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.notice import Notice
from app.models.user import User
from app.auth.deps import get_current_user

router = APIRouter()


COMPARISON_FIELDS = [
    ("case_id", "Case ID"),
    ("notice_type", "Notice Type"),
    ("section", "Section"),
    ("fy", "Financial Year"),
    ("risk_level", "Risk Level"),
    ("risk_score", "Risk Score"),
    ("demand_amount", "Demand Amount"),
    ("response_deadline", "Response Deadline"),
    ("is_time_barred", "Time-Barred"),
    ("draft_status", "Draft Status"),
    ("status", "Processing Status"),
    ("verification_score", "Verification Score"),
]


@router.get("/notices/compare")
async def compare_notices(
    ids: List[str] = Query(..., description="Notice IDs to compare (2-5)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Compare 2-5 notices side-by-side.
    Returns a structured comparison with field labels and values per notice.
    """
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 notice IDs required for comparison")
    if len(ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 notices can be compared at once")

    # Fetch all requested notices
    result = await db.execute(select(Notice).where(Notice.id.in_(ids)))
    notices = result.scalars().all()

    if len(notices) < 2:
        raise HTTPException(status_code=404, detail=f"Found {len(notices)} notices, need at least 2")

    # Build comparison table
    notices_data = []
    for n in notices:
        notices_data.append({
            "id": n.id,
            "case_id": n.case_id or "",
            "filename": n.filename or "",
            "notice_type": n.notice_type or "Unknown",
            "section": n.section or "—",
            "fy": n.fy or "—",
            "risk_level": n.risk_level or "UNKNOWN",
            "risk_score": n.risk_score or 0,
            "demand_amount": n.demand_amount or 0,
            "response_deadline": n.response_deadline or "—",
            "is_time_barred": n.is_time_barred or False,
            "draft_status": n.draft_status or "pending",
            "status": n.status or "unknown",
            "verification_score": n.verification_score,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        })

    # Build row-based comparison for easy frontend rendering
    rows = []
    for field_key, field_label in COMPARISON_FIELDS:
        row = {
            "field": field_key,
            "label": field_label,
            "values": [nd.get(field_key) for nd in notices_data],
        }
        # Flag if all values differ (highlight differences)
        unique_values = set(str(v) for v in row["values"])
        row["all_same"] = len(unique_values) == 1
        rows.append(row)

    return {
        "notices": notices_data,
        "comparison": rows,
        "count": len(notices_data),
    }
