"""
TaxShield — Drafts Routes
Purpose: Draft retrieval and approval endpoints
Status: PLACEHOLDER — to be implemented
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class DraftApproval(BaseModel):
    approved: bool
    feedback: Optional[str] = None


@router.get("/drafts/{id}")
def get_draft(id: str):
    """Get draft by ID"""
    # TODO: Implement draft retrieval from database
    return {"draft_id": id, "status": "PLACEHOLDER"}


@router.post("/drafts/{id}/approve")
async def approve_draft(id: str, approval: DraftApproval):
    """Approve or reject draft"""
    # TODO: Implement draft approval logic
    return {
        "draft_id": id,
        "approved": approval.approved,
        "feedback": approval.feedback,
        "status": "PLACEHOLDER"
    }
