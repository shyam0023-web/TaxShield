"""
TaxShield — Case Model
Purpose: SQLAlchemy model for cases table
Status: PLACEHOLDER — to be implemented
"""
from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON
from app.database import Base
import uuid


class Case(Base):
    __tablename__ = "cases"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String, unique=True, nullable=False)
    client_name = Column(String)
    client_interview = Column(JSON)
    legal_analysis = Column(Text)
    relevant_circulars = Column(JSON)
    relevant_case_laws = Column(JSON)
    status = Column(String, default="active")
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
