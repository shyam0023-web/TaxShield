"""
TaxShield — Logging Middleware
Purpose: Request/response logging with unique request IDs
Status: IMPLEMENTED
"""
import time
import uuid
import json
from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.logger import logger

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


def setup_logging(app):
    """Setup request logging for the FastAPI application"""
    app.add_middleware(RequestLoggingMiddleware)


