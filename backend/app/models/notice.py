"""
TaxShield — Notice Model
SQLAlchemy model for notices table.
Stores pipeline output from Agent 1 → 2 → 3 → 4.
"""
from sqlalchemy import Column, String, Text, DateTime, Float, Boolean, JSON
from app.database import Base
import uuid
from datetime import datetime


class Notice(Base):
    __tablename__ = "notices"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, unique=True, nullable=False)
    filename = Column(String, nullable=False)
    
    # Agent 1 output
    notice_text = Column(Text)  # PII-redacted OCR text
    entities = Column(JSON)  # Extracted entities (GSTIN, DIN, sections, etc.)
    notice_annotations = Column(JSON)  # Paragraph roles (HEADER, FACTS, DEMAND, etc.)
    processing_status = Column(String)  # "complete", "partial", "failed"
    
    # Agent 2 output
    risk_level = Column(String)  # LOW, MEDIUM, HIGH, UNKNOWN
    risk_score = Column(Float)
    risk_reasoning = Column(Text)
    is_time_barred = Column(Boolean, default=False)
    time_bar_detail = Column(JSON)
    
    # Derived fields (extracted from entities for easy querying)
    fy = Column(String)  # Financial year e.g. "2019-20"
    section = Column(String)  # Primary section e.g. "73"
    notice_type = Column(String)  # SCN, Demand, Scrutiny, etc.
    demand_amount = Column(Float, default=0.0)
    response_deadline = Column(String)
    
    # Agent 4 output
    draft_reply = Column(Text)
    draft_status = Column(String, default="pending")  # pending, draft_ready, approved, rejected
    
    # Metadata
    status = Column(String, default="processing")  # processing, processed, error
    error_message = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
