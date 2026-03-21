"""
TaxShield — Draft Diff Endpoint
Returns a diff between the original AI draft and the current (human-edited) version.
"""
import difflib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.notice import Notice
from app.models.draft import Draft
from app.models.user import User
from app.auth.deps import get_current_user

router = APIRouter()


@router.get("/notices/{notice_id}/diff")
async def get_draft_diff(
    notice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns a unified diff between the original AI-generated draft
    and the latest human-edited version.
    """
    # Get the notice
    result = await db.execute(select(Notice).where(Notice.id == notice_id))
    notice = result.scalar_one_or_none()
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")

    # Get the original draft from the drafts table (first version)
    drafts_result = await db.execute(
        select(Draft)
        .where(Draft.notice_id == notice_id)
        .order_by(Draft.created_at.asc())
    )
    drafts = drafts_result.scalars().all()

    if not drafts:
        return {
            "has_diff": False,
            "message": "No drafts found for this notice",
            "original": notice.draft_reply or "",
            "current": notice.draft_reply or "",
            "diff_lines": [],
            "stats": {"additions": 0, "deletions": 0, "unchanged": 0},
        }

    original_text = drafts[0].draft_content or ""
    current_text = notice.draft_reply or ""

    # Generate unified diff
    original_lines = original_text.splitlines(keepends=True)
    current_lines = current_text.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        original_lines,
        current_lines,
        fromfile="Original AI Draft",
        tofile="Current Version",
        lineterm="",
    ))

    # Compute stats
    additions = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))

    return {
        "has_diff": len(diff) > 0,
        "original": original_text,
        "current": current_text,
        "diff_lines": diff,
        "stats": {
            "additions": additions,
            "deletions": deletions,
            "unchanged": len(original_lines) - deletions,
        },
        "total_drafts": len(drafts),
    }
