"""Redis client for TaxShield — used for caching, rate limiting, and queue broker."""
import redis.asyncio as aioredis
from app.config import REDIS_URL
from app.logger import logger


_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get or create the shared async Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        try:
            _redis_pool = aioredis.from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
            )
            # Test connection
            await _redis_pool.ping()
            logger.info("✅ Redis connected successfully")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            _redis_pool = None
            raise
    return _redis_pool


async def close_redis():
    """Close the Redis connection pool on shutdown."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None
        logger.info("Redis connection closed")
