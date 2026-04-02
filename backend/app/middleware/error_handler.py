"""
TaxShield — Error Handler Middleware
Purpose: Global error handling for FastAPI application
Status: IMPLEMENTED
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Awaitable
from app.logger import logger


class GlobalErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            from fastapi import HTTPException
            if isinstance(exc, HTTPException):
                raise exc
            import traceback
            tb = traceback.format_exc()
            logger.error(f"Global exception handler caught error: {exc}\n{tb}")
            
            # Issue 13: Never leak internal details in production
            from app.config import settings
            detail = str(exc) if settings.DEBUG else "An unexpected error occurred. Please try again."
            
            return JSONResponse(
                status_code=500,
                content={"error": "Internal Server Error", "detail": detail},
            )


def setup_error_handlers(app):
    """Setup error handlers for the FastAPI application"""
    app.add_middleware(GlobalErrorHandlerMiddleware)
