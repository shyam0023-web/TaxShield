"""
TaxShield — Draft Model
Purpose: SQLAlchemy model for drafts table
Status: PLACEHOLDER — to be implemented
"""
from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from app.database import Base
import uuid


class Draft(Base):
    __tablename__ = "drafts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notice_id = Column(UUID(as_uuid=True), nullable=False)
    draft_content = Column(Text, nullable=False)
    defense_strategy = Column(Text)
    supporting_documents = Column(ARRAY(String))
    procedural_compliance = Column(Boolean, default=False)
    approved = Column(Boolean, default=False)
    feedback = Column(Text)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
