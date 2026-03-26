"""
TaxShield — Auth Routes
Register, login, and current user endpoints.
"""
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logger import logger
from app.models.user import User
from app.auth.deps import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter()


def serialize_user(user: User) -> dict:
    """Single source of truth for user serialization."""
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
    }


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ═══════════════════════════════════════════
# POST /api/auth/register
# ═══════════════════════════════════════════

@router.post("/auth/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Create a new user account."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        return JSONResponse(status_code=409, content={"detail": "Email already registered"})

    if len(body.password) < 6:
        return JSONResponse(status_code=400, content={"detail": "Password must be at least 6 characters"})

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        created_at=datetime.utcnow(),
    )
    # Issue 7A: Distinct variable names — no shadowing
    verification_token = secrets.token_urlsafe(32)
    user.email_verification_token = verification_token
    user.email_token_expires = datetime.utcnow() + timedelta(hours=24)
    
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(user.id, user.email)

    logger.info(f"New user registered: {user.email} (id={user.id})")

    # Issue 5A: Use serialize_user helper
    return {"token": access_token, "user": serialize_user(user)}


# ═══════════════════════════════════════════
# POST /api/auth/login
# ═══════════════════════════════════════════

@router.post("/auth/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate and return JWT token."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        return JSONResponse(status_code=401, content={"detail": "Invalid email or password"})

    access_token = create_access_token(user.id, user.email)

    logger.info(f"User logged in: {user.email}")

    # Issue 5A: Use serialize_user helper
    return {"token": access_token, "user": serialize_user(user)}


# ═══════════════════════════════════════════
# GET /api/auth/me
# ═══════════════════════════════════════════

@router.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    # Issue 5A: Use serialize_user helper
    return serialize_user(user)
