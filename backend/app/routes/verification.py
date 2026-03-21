"""
TaxShield — Email Verification Routes
Endpoints for email verification flow.
"""
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logger import logger
from app.models.user import User
from app.auth.deps import get_current_user
from app.config import settings

router = APIRouter()


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: str


def generate_verification_token() -> tuple[str, datetime]:
    """Generate a verification token valid for 24 hours."""
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=24)
    return token, expires


# ═══════════════════════════════════════════
# POST /api/auth/verify-email
# ═══════════════════════════════════════════

@router.post("/auth/verify-email")
async def verify_email(body: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    """Verify a user's email using the token sent via email."""
    result = await db.execute(
        select(User).where(User.email_verification_token == body.token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    if user.email_token_expires and user.email_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification token expired")

    user.email_verified = True
    user.email_verification_token = None
    user.email_token_expires = None
    await db.commit()

    logger.info(f"Email verified for user: {user.email}")
    return {"message": "Email verified successfully", "email": user.email}


# ═══════════════════════════════════════════
# POST /api/auth/resend-verification
# ═══════════════════════════════════════════

@router.post("/auth/resend-verification")
async def resend_verification(body: ResendVerificationRequest, db: AsyncSession = Depends(get_db)):
    """Resend the email verification token."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        # Don't reveal whether the email exists
        return {"message": "If the email exists, a verification link has been sent"}

    if user.email_verified:
        return {"message": "Email already verified"}

    token, expires = generate_verification_token()
    user.email_verification_token = token
    user.email_token_expires = expires
    await db.commit()

    # In production, this would send an email
    # For now, log the token (dev mode only)
    if settings.DEBUG:
        logger.info(f"[DEV] Verification token for {user.email}: {token}")

    return {"message": "If the email exists, a verification link has been sent"}


# ═══════════════════════════════════════════
# GET /api/auth/verification-status
# ═══════════════════════════════════════════

@router.get("/auth/verification-status")
async def verification_status(user: User = Depends(get_current_user)):
    """Check if the current user's email is verified."""
    return {
        "email": user.email,
        "verified": user.email_verified,
    }
