"""
TaxShield — Notice Model
Purpose: SQLAlchemy model for notices table
Status: PLACEHOLDER — to be implemented
"""
from sqlalchemy import Column, String, Text, DateTime, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid


class Notice(Base):
    __tablename__ = "notices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(String, unique=True, nullable=False)
    notice_text = Column(Text, nullable=False)
    fy = Column(String, nullable=False)
    section = Column(String, nullable=False)
    risk_classification = Column(String)
    confidence_score = Column(Float)
    draft_reply = Column(Text)
    audit_passed = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
