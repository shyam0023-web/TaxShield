"""
TaxShield — Health Routes
Purpose: Health check endpoints
Status: IMPLEMENTED
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "version": "1.0"}
