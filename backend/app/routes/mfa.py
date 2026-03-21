"""
TaxShield — TOTP Multi-Factor Authentication
Supports Google Authenticator / Authy for 2FA.
"""
import pyotp
import io
import base64
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.auth.deps import get_current_user

router = APIRouter()


class VerifyTOTPRequest(BaseModel):
    code: str


# ═══════════════════════════════════════════
# POST /api/auth/mfa/setup — Generate TOTP secret
# ═══════════════════════════════════════════

@router.post("/auth/mfa/setup")
async def setup_mfa(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a new TOTP secret for the user and return provisioning URI."""
    secret = pyotp.random_base32()

    # Store the secret (unverified until user confirms with a code)
    user.totp_secret = secret
    user.mfa_enabled = False  # Not active until verified
    await db.commit()

    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name="TaxShield"
    )

    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri,
        "message": "Scan the QR code in Google Authenticator, then verify with a code",
    }


# ═══════════════════════════════════════════
# POST /api/auth/mfa/verify — Verify TOTP and enable MFA
# ═══════════════════════════════════════════

@router.post("/auth/mfa/verify")
async def verify_mfa(
    body: VerifyTOTPRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Verify a TOTP code to enable MFA for the user."""
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="MFA not set up. Call /auth/mfa/setup first.")

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    user.mfa_enabled = True
    await db.commit()

    return {"message": "MFA enabled successfully", "mfa_enabled": True}


# ═══════════════════════════════════════════
# POST /api/auth/mfa/validate — Validate code during login
# ═══════════════════════════════════════════

@router.post("/auth/mfa/validate")
async def validate_mfa(
    body: VerifyTOTPRequest,
    user: User = Depends(get_current_user),
):
    """Validate a TOTP code (used as 2nd factor during login)."""
    if not user.mfa_enabled or not user.totp_secret:
        return {"valid": True, "message": "MFA not enabled — skipping"}

    totp = pyotp.TOTP(user.totp_secret)
    is_valid = totp.verify(body.code, valid_window=1)

    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid TOTP code")

    return {"valid": True, "message": "MFA validation successful"}


# ═══════════════════════════════════════════
# DELETE /api/auth/mfa — Disable MFA
# ═══════════════════════════════════════════

@router.delete("/auth/mfa")
async def disable_mfa(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Disable MFA for the current user."""
    user.mfa_enabled = False
    user.totp_secret = None
    await db.commit()

    return {"message": "MFA disabled", "mfa_enabled": False}


# ═══════════════════════════════════════════
# GET /api/auth/mfa/status
# ═══════════════════════════════════════════

@router.get("/auth/mfa/status")
async def mfa_status(user: User = Depends(get_current_user)):
    """Check if MFA is enabled for the current user."""
    return {
        "mfa_enabled": user.mfa_enabled or False,
        "email": user.email,
    }
