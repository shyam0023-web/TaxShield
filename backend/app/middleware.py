import time
import uuid
import logging
from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.logger import logger
from fastapi.responses import JSONResponse
import collections

# Simple in-memory rate limiter (Token Bucket)
# Dictionary: IP -> [timestamp1, timestamp2, ...]
RATE_LIMIT_DATA = collections.defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 20  # requests per window

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Attach request_id to logger context (simplified here by adding to request scope)
        request.scope["request_id"] = request_id
        
        logger.info(json.dumps({
            "event": "request_in",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host,
        }))
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            logger.info(json.dumps({
                "event": "request_out",
                "request_id": request_id,
                "status_code": response.status_code,
                "process_time": f"{process_time:.4f}s",
            }))
            
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(json.dumps({
                "event": "request_error",
                "request_id": request_id,
                "error": str(e),
                "process_time": f"{process_time:.4f}s",
            }))
            raise  # Re-raise to let ErrorHandlingMiddleware catch it

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

import json
