"""
TaxShield — Draft Model
Purpose: SQLAlchemy model for drafts table
Status: PLACEHOLDER — to be implemented
"""
from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON
from app.database import Base
import uuid


class Draft(Base):
    __tablename__ = "drafts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    notice_id = Column(String(36), nullable=False)
    draft_content = Column(Text, nullable=False)
    defense_strategy = Column(Text)
    supporting_documents = Column(JSON)
    procedural_compliance = Column(Boolean, default=False)
    approved = Column(Boolean, default=False)
    feedback = Column(Text)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
