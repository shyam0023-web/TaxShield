"""
TaxShield — User Model
SQLAlchemy model for users table.
"""
from sqlalchemy import Column, String, DateTime, Boolean
from app.database import Base
import uuid
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="ca")  # ca, admin
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String, nullable=True)
    email_token_expires = Column(DateTime, nullable=True)
    totp_secret = Column(String, nullable=True)
    mfa_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
