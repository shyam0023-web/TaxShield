"""
TaxShield — Rate Limiter Middleware
In-memory sliding window rate limiting with periodic cleanup.
"""
import time
import asyncio
import collections
from typing import Callable, Awaitable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.logger import logger

# Simple in-memory rate limiter (Sliding Window)
# Dictionary: IP -> [timestamp1, timestamp2, ...]
RATE_LIMIT_DATA: dict[str, list[float]] = collections.defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 20  # requests per window
CLEANUP_INTERVAL = 300  # cleanup stale IPs every 5 minutes
_cleanup_task = None


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        client_ip = request.client.host
        current_time = time.time()
        
        # Remove old timestamps for this IP
        RATE_LIMIT_DATA[client_ip] = [
            t for t in RATE_LIMIT_DATA[client_ip]
            if current_time - t < RATE_LIMIT_WINDOW
        ]
        
        if len(RATE_LIMIT_DATA[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded. Try again later."},
            )
            
        RATE_LIMIT_DATA[client_ip].append(current_time)
        return await call_next(request)


async def _periodic_cleanup():
    """Background task to remove stale IPs from rate limit data."""
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL)
        current_time = time.time()
        stale_ips = [
            ip for ip, timestamps in RATE_LIMIT_DATA.items()
            if not timestamps or (current_time - max(timestamps)) > RATE_LIMIT_WINDOW
        ]
        for ip in stale_ips:
            del RATE_LIMIT_DATA[ip]
        if stale_ips:
            logger.debug(f"Rate limiter cleanup: removed {len(stale_ips)} stale IPs")


def setup_rate_limiting(app):
    """Setup rate limiting for the FastAPI application.
    
    Note: Cleanup task is started/stopped via the app lifespan in main.py.
    The middleware itself is attached here.
    """
    app.add_middleware(RateLimitMiddleware)
