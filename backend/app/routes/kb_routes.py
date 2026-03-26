"""
TaxShield — KB Review API Routes
Endpoints for CAs to review, approve, or reject staged CBIC circulars.
On approval: generates curated markdown file → reloads section KB.
"""
import os
import re
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.kb_staging import KBStaging
from app.routes.auth import get_current_user
from app.retrieval.section_kb import section_kb

logger = logging.getLogger(__name__)
router = APIRouter()

KB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "curated_kb")


# ═══════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════

class ApproveRequest(BaseModel):
    key_ruling: str                     # CA writes the key ruling summary
    defense_points: List[str]           # CA writes defense points
    sections: List[str]                 # Sections this circular covers
    keywords: Optional[List[str]] = []  # Optional search keywords

class RejectRequest(BaseModel):
    reason: str

class ManualEntryRequest(BaseModel):
    circular_id: str
    title: str
    full_text: str
    sections: List[str]
    source_url: Optional[str] = ""

class StagingResponse(BaseModel):
    id: str
    circular_id: str
    title: str
    status: str
    sections: Optional[list] = None
    scraped_at: Optional[str] = None
    source_url: Optional[str] = None

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════

@router.get("/kb/pending")
async def list_pending(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all UNVERIFIED circulars awaiting review."""
    result = await db.execute(
        select(KBStaging)
        .where(KBStaging.status == "UNVERIFIED")
        .order_by(KBStaging.scraped_at.desc())
    )
    entries = result.scalars().all()

    return [{
        "id": e.id,
        "circular_id": e.circular_id,
        "title": e.title,
        "sections": e.sections,
        "source_url": e.source_url,
        "scraped_at": str(e.scraped_at) if e.scraped_at else None,
        "status": e.status,
    } for e in entries]


@router.get("/kb/pending/{entry_id}")
async def get_pending_detail(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """View full detail of a staged circular."""
    result = await db.execute(
        select(KBStaging).where(KBStaging.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    return {
        "id": entry.id,
        "circular_id": entry.circular_id,
        "title": entry.title,
        "full_text": entry.full_text,
        "sections": entry.sections,
        "source_url": entry.source_url,
        "issue_date": str(entry.issue_date) if entry.issue_date else None,
        "scraped_at": str(entry.scraped_at) if entry.scraped_at else None,
        "status": entry.status,
        "review_notes": entry.review_notes,
        "key_ruling": entry.key_ruling,
        "defense_points": entry.defense_points,
    }


@router.post("/kb/pending/{entry_id}/approve")
async def approve_circular(
    entry_id: str,
    body: ApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Approve a circular: save CA content → generate markdown → reload KB."""
    result = await db.execute(
        select(KBStaging).where(KBStaging.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    if entry.status != "UNVERIFIED":
        raise HTTPException(status_code=400, detail=f"Entry already {entry.status}")

    # Update staging entry
    entry.status = "APPROVED"
    entry.reviewed_by = current_user.id if hasattr(current_user, "id") else "unknown"
    entry.reviewed_at = datetime.utcnow()
    entry.key_ruling = body.key_ruling
    entry.defense_points = body.defense_points
    entry.sections = body.sections
    entry.keywords = body.keywords

    # Generate curated markdown file
    md_filename = _generate_kb_markdown(entry, body)

    await db.commit()

    # Hot-reload the section KB
    section_kb.reload()

    logger.info(f"Circular {entry.circular_id} approved → {md_filename}")

    return {
        "status": "approved",
        "circular_id": entry.circular_id,
        "kb_file": md_filename,
        "message": f"Circular approved and added to curated KB as {md_filename}",
    }


@router.post("/kb/pending/{entry_id}/reject")
async def reject_circular(
    entry_id: str,
    body: RejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Reject a circular with reason."""
    result = await db.execute(
        select(KBStaging).where(KBStaging.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    if entry.status != "UNVERIFIED":
        raise HTTPException(status_code=400, detail=f"Entry already {entry.status}")

    entry.status = "REJECTED"
    entry.reviewed_by = current_user.id if hasattr(current_user, "id") else "unknown"
    entry.reviewed_at = datetime.utcnow()
    entry.review_notes = body.reason

    await db.commit()

    logger.info(f"Circular {entry.circular_id} rejected: {body.reason}")

    return {"status": "rejected", "circular_id": entry.circular_id}


@router.get("/kb/sections")
async def list_kb_sections(current_user=Depends(get_current_user)):
    """List all indexed KB sections."""
    return {"sections": section_kb.get_all_sections()}


@router.post("/kb/scrape")
async def trigger_scrape(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Trigger a manual CBIC scrape."""
    from app.tools.cbic_scraper import scrape_cbic_circulars
    new_count = await scrape_cbic_circulars(db)
    return {"new_circulars": new_count, "message": f"Scrape complete: {new_count} new entries staged"}


@router.post("/kb/manual")
async def add_manual_entry(
    body: ManualEntryRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Add a circular manually (bypasses scraper)."""
    from app.tools.cbic_scraper import add_manual_circular
    entry = await add_manual_circular(
        db, body.circular_id, body.title, body.full_text,
        body.sections, body.source_url,
    )
    return {"id": entry.id, "circular_id": entry.circular_id, "status": "UNVERIFIED"}


# ═══════════════════════════════════════════
# KB Promotion (markdown generation)
# ═══════════════════════════════════════════

def _generate_kb_markdown(entry: KBStaging, approval: ApproveRequest) -> str:
    """Generate a curated markdown file from an approved staging entry."""
    # Determine filename
    sections = approval.sections
    if sections:
        primary = sections[0]
        filename = f"circular_{_sanitize_filename(entry.circular_id)}.md"
    else:
        filename = f"circular_{_sanitize_filename(entry.circular_id)}.md"

    # Build markdown content
    lines = [
        f"# {entry.title}",
        "",
        f"**Circular:** {entry.circular_id}",
    ]
    if entry.issue_date:
        lines.append(f"**Date:** {entry.issue_date.strftime('%Y-%m-%d')}")
    if entry.source_url:
        lines.append(f"**Source:** [{entry.source_url}]({entry.source_url})")
    if sections:
        lines.append(f"**Sections:** {', '.join(['Section ' + s for s in sections])}")

    lines.extend([
        "",
        "## Key Ruling",
        approval.key_ruling,
        "",
        "## Key Defense Points",
    ])

    for i, point in enumerate(approval.defense_points, 1):
        lines.append(f"{i}. {point}")

    if entry.full_text:
        lines.extend([
            "",
            "## Full Circular Text",
            entry.full_text[:3000],
        ])

    # Write file
    kb_dir = os.path.normpath(KB_DIR)
    os.makedirs(kb_dir, exist_ok=True)
    filepath = os.path.join(kb_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Generated KB file: {filepath}")
    return filename


def _sanitize_filename(name: str) -> str:
    """Convert circular ID to safe filename."""
    return re.sub(r'[^\w\-]', '_', name).lower()
