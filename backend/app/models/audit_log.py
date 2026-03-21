"""
TaxShield — Audit Log Model
Compliance trail: tracks who did what, when.
"""
from sqlalchemy import Column, String, Text, DateTime, JSON, Index
from app.database import Base
import uuid
from datetime import datetime


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Who
    user_id = Column(String(36), nullable=True)   # null for system actions
    user_email = Column(String, nullable=True)
    user_role = Column(String, nullable=True)
    
    # What
    action = Column(String, nullable=False)        # upload, approve, reject, delete, login, register
    resource_type = Column(String, nullable=False)  # notice, draft, user
    resource_id = Column(String, nullable=True)     # ID of the affected resource
    
    # Details
    details = Column(JSON, nullable=True)          # additional context (filename, changes, etc.)
    ip_address = Column(String, nullable=True)
    
    # When
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )
