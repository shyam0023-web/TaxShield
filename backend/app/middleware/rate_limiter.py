"""
TaxShield — Unified Rate Limiter
Redis-backed sliding window limiter with in-memory fallback.

Single class (SlidingWindowLimiter) handles all rate limiting:
  - Global IP limiting (middleware)
  - Per-user upload limiting (route)
  - Any future per-route limits

Redis key format: rl:{key}  (e.g. "rl:ip:127.0.0.1", "rl:upload:user-id-123")
Uses Redis sorted sets (ZADD/ZRANGEBYSCORE) — standard sliding window approach.
Falls back to in-memory if Redis is unavailable.
"""
import time
import asyncio
import collections
from typing import Callable, Awaitable

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.logger import logger
from app.config import settings

CLEANUP_INTERVAL = 300  # in-memory fallback cleanup every 5 minutes


# ═══════════════════════════════════════════
# Core: Unified Sliding Window Limiter
# ═══════════════════════════════════════════

class SlidingWindowLimiter:
    """
    Redis-backed sliding window rate limiter with automatic in-memory fallback.

    Usage:
        limiter = SlidingWindowLimiter(max_requests=60, window_seconds=60)
        allowed = await limiter.is_allowed("ip:127.0.0.1")
        if not allowed:
            raise HTTPException(429, ...)

    Key is any string — caller decides the namespace (e.g. "ip:x.x.x.x" or "upload:user-id").
    """
    _fallback: dict[str, list[float]] = collections.defaultdict(list)
    _MAX_FALLBACK_KEYS = 10_000  # OOM safety valve for in-memory fallback

    def __init__(self, max_requests: int, window_seconds: int, prefix: str = "rl"):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.prefix = prefix
        self._redis = None
        self._redis_available = True  # optimistic; will flip on first failure

    async def _get_redis(self):
        """Lazily get Redis client — returns None if unavailable."""
        if not self._redis_available:
            return None
        try:
            from app.redis_client import get_redis
            return await get_redis()
        except Exception:
            return None

    async def is_allowed(self, key: str) -> bool:
        """
        Returns True if the request is within limits, False if rate-limited.
        Increments the counter as a side effect (check-and-increment in one step).
        """
        redis = await self._get_redis()
        if redis is not None:
            return await self._redis_check(redis, key)
        return self._memory_check(key)

    async def _redis_check(self, redis, key: str) -> bool:
        """Sliding window via Redis sorted set — atomic and restart-safe."""
        full_key = f"{self.prefix}:{key}"
        now = time.time()
        window_start = now - self.window_seconds

        try:
            pipe = redis.pipeline()
            # Remove timestamps older than window
            pipe.zremrangebyscore(full_key, 0, window_start)
            # Count current window
            pipe.zcard(full_key)
            # Add current request timestamp (score=timestamp, member=timestamp string)
            pipe.zadd(full_key, {str(now): now})
            # Set TTL so Redis auto-cleans
            pipe.expire(full_key, self.window_seconds * 2)
            results = await pipe.execute()

            count_before_add = results[1]
            if count_before_add >= self.max_requests:
                # We added the timestamp above — remove it since we're blocking
                await redis.zrem(full_key, str(now))
                return False
            return True
        except Exception as e:
            logger.warning(f"Redis rate limiter error, falling back to memory: {e}")
            self._redis_available = False
            return self._memory_check(key)

    def _memory_check(self, key: str) -> bool:
        """In-memory fallback — not restart-safe, not multi-worker-safe."""
        # OOM safety valve
        if len(self._fallback) > self._MAX_FALLBACK_KEYS:
            logger.warning(f"Rate limiter fallback safety valve: clearing {len(self._fallback)} keys")
            self._fallback.clear()

        now = time.time()
        window_start = now - self.window_seconds
        timestamps = [t for t in self._fallback[key] if t > window_start]

        if len(timestamps) >= self.max_requests:
            self._fallback[key] = timestamps
            return False

        timestamps.append(now)
        self._fallback[key] = timestamps
        return True

    def cleanup_fallback(self):
        """Remove stale keys from in-memory fallback. Call periodically."""
        now = time.time()
        stale = [
            k for k, timestamps in self._fallback.items()
            if not timestamps or (now - max(timestamps)) > self.window_seconds
        ]
        for k in stale:
            del self._fallback[k]
        if stale:
            logger.debug(f"Rate limiter cleanup: removed {len(stale)} stale keys")


# ═══════════════════════════════════════════
# Singleton limiters — one per limit type
# ═══════════════════════════════════════════

# Global IP limiter: 60 requests/min per IP
ip_limiter = SlidingWindowLimiter(
    max_requests=settings.RATE_LIMIT_PER_MINUTE,
    window_seconds=60,
    prefix="rl:ip",
)

# Per-user upload limiter: 5 uploads/min per user
# Each upload triggers ~5 LLM calls — stricter limit prevents Groq API abuse
upload_limiter = SlidingWindowLimiter(
    max_requests=5,
    window_seconds=60,
    prefix="rl:upload",
)


# ═══════════════════════════════════════════
# FastAPI Middleware
# ═══════════════════════════════════════════

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        client_ip = getattr(request.client, "host", "unknown")
        allowed = await ip_limiter.is_allowed(f"ip:{client_ip}")
        if not allowed:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded. Try again later."},
            )
        return await call_next(request)


# ═══════════════════════════════════════════
# Background cleanup (in-memory fallback only)
# ═══════════════════════════════════════════

async def _periodic_cleanup():
    """Periodically clean up in-memory fallback state. No-op when Redis is healthy."""
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL)
        ip_limiter.cleanup_fallback()
        upload_limiter.cleanup_fallback()


def setup_rate_limiting(app):
    """Attach rate limiting middleware to the FastAPI app."""
    app.add_middleware(RateLimitMiddleware)


# ═══════════════════════════════════════════
# Route-level helper (used by notices.py)
# ═══════════════════════════════════════════

async def check_upload_rate(user_id: str):
    """
    Raise HTTP 429 if the user has exceeded the upload rate limit.
    Call this at the top of the upload route before any file processing.
    """
    allowed = await upload_limiter.is_allowed(user_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Upload rate limit exceeded. Maximum 5 uploads per minute.",
        )
