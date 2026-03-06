"""
TaxShield — Deadline Table Model
Purpose: SQLAlchemy model for CBIC extension dates
Status: PLACEHOLDER — to be implemented
"""
from sqlalchemy import Column, String, DateTime
from app.database import Base


class DeadlineTable(Base):
    __tablename__ = "deadline_table"
    
    id = Column(String, primary_key=True)
    section = Column(String, nullable=False)
    fy = Column(String, nullable=False)
    original_deadline = Column(DateTime, nullable=False)
    extended_deadline = Column(DateTime, nullable=False)
    notification_no = Column(String)
    notification_date = Column(DateTime)
