"""
TaxShield — Rate Limiter Middleware
Purpose: Token bucket rate limiting for API endpoints
Status: IMPLEMENTED
"""
import time
import collections
import json
from typing import Callable, Awaitable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.logger import logger

# Simple in-memory rate limiter (Token Bucket)
# Dictionary: IP -> [timestamp1, timestamp2, ...]
RATE_LIMIT_DATA = collections.defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 20  # requests per window


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        client_ip = request.client.host
        current_time = time.time()
        
        # Remove old timestamps
        RATE_LIMIT_DATA[client_ip] = [t for t in RATE_LIMIT_DATA[client_ip] if current_time - t < RATE_LIMIT_WINDOW]
        
        if len(RATE_LIMIT_DATA[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded. Try again later."},
            )
            
        RATE_LIMIT_DATA[client_ip].append(current_time)
        return await call_next(request)


def setup_rate_limiting(app):
    """Setup rate limiting for the FastAPI application"""
    app.add_middleware(RateLimitMiddleware)
