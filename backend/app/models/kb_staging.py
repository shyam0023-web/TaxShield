"""
TaxShield — KB Staging Model
Stores scraped CBIC circulars/notifications awaiting CA review.
Status lifecycle: UNVERIFIED → APPROVED → promoted to curated KB
                  UNVERIFIED → REJECTED → archived
"""
from sqlalchemy import Column, String, Text, DateTime, JSON, Index
from app.database import Base
import uuid
from datetime import datetime


class KBStaging(Base):
    __tablename__ = "kb_staging"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Circular metadata
    circular_id = Column(String(100), nullable=False, unique=True)  # e.g. "CGST-CIR-239-2024"
    title = Column(String(500), nullable=False)                     # Subject line
    full_text = Column(Text, nullable=False)                        # Complete circular text
    sections = Column(JSON, nullable=True)                          # ["73", "74"]
    source_url = Column(String(500), nullable=True)                 # CBIC download URL
    issue_date = Column(DateTime, nullable=True)                    # Circular issue date

    # Scraping metadata
    scraped_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Review status
    status = Column(String(20), nullable=False, default="UNVERIFIED")  # UNVERIFIED/APPROVED/REJECTED
    reviewed_by = Column(String(36), nullable=True)                     # User ID of reviewer
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)                          # CA's notes

    # CA-authored content (filled on approval)
    key_ruling = Column(Text, nullable=True)            # CA writes the key ruling summary
    defense_points = Column(JSON, nullable=True)        # CA writes defense points as list
    keywords = Column(JSON, nullable=True)              # CA adds searchable keywords

    __table_args__ = (
        Index("ix_kb_staging_status", "status"),
        Index("ix_kb_staging_circular_id", "circular_id"),
    )
