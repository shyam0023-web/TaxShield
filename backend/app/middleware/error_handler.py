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
            logger.exception("Global exception handler caught error")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal Server Error", "detail": "An unexpected error occurred. Please contact support."},
            )


def setup_error_handlers(app):
    """Setup error handlers for the FastAPI application"""
    app.add_middleware(GlobalErrorHandlerMiddleware)
