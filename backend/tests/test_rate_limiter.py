"""
Unit tests for SlidingWindowLimiter — the unified rate limiter class.

All tests use the in-memory fallback path (no Redis required).
Redis → fallback transition is tested via mocking.
"""
import sys
import os
import time
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.middleware.rate_limiter import SlidingWindowLimiter, check_upload_rate


# ═══════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════

def make_limiter(max_requests: int = 3, window_seconds: int = 60) -> SlidingWindowLimiter:
    """Create a limiter with Redis disabled so tests use the in-memory fallback."""
    limiter = SlidingWindowLimiter(max_requests=max_requests, window_seconds=window_seconds)
    limiter._redis_available = False  # force fallback; no Redis in test env
    return limiter


# ═══════════════════════════════════════════
# In-memory fallback: core enforcement
# ═══════════════════════════════════════════

class TestSlidingWindowEnforcement:

    @pytest.mark.anyio
    async def test_allows_requests_under_limit(self):
        limiter = make_limiter(max_requests=3)
        assert await limiter.is_allowed("key1") is True
        assert await limiter.is_allowed("key1") is True
        assert await limiter.is_allowed("key1") is True

    @pytest.mark.anyio
    async def test_blocks_request_at_limit(self):
        limiter = make_limiter(max_requests=3)
        await limiter.is_allowed("key1")
        await limiter.is_allowed("key1")
        await limiter.is_allowed("key1")
        # 4th request should be blocked
        assert await limiter.is_allowed("key1") is False

    @pytest.mark.anyio
    async def test_different_keys_are_independent(self):
        limiter = make_limiter(max_requests=1)
        assert await limiter.is_allowed("user-a") is True
        assert await limiter.is_allowed("user-a") is False
        # user-b has its own counter
        assert await limiter.is_allowed("user-b") is True

    @pytest.mark.anyio
    async def test_counter_increments_on_each_allowed_request(self):
        limiter = make_limiter(max_requests=5)
        for _ in range(5):
            assert await limiter.is_allowed("key1") is True
        assert await limiter.is_allowed("key1") is False

    @pytest.mark.anyio
    async def test_blocked_request_does_not_increment_counter(self):
        """Blocking a request should not push the window further — idempotent."""
        limiter = make_limiter(max_requests=2)
        await limiter.is_allowed("key1")
        await limiter.is_allowed("key1")
        # key1 is now at limit
        assert await limiter.is_allowed("key1") is False
        assert await limiter.is_allowed("key1") is False
        # Count should still be 2, not growing
        assert len(limiter._fallback["key1"]) == 2


# ═══════════════════════════════════════════
# Sliding window mechanics
# ═══════════════════════════════════════════

class TestSlidingWindow:

    @pytest.mark.anyio
    async def test_old_timestamps_expire_out_of_window(self):
        """Requests older than window_seconds should not count toward the limit."""
        limiter = make_limiter(max_requests=2, window_seconds=60)
        # Manually backdate 2 timestamps to >60s ago
        old_time = time.time() - 61
        limiter._fallback["key1"] = [old_time, old_time]

        # These are outside the window — 2 new requests should be allowed
        assert await limiter.is_allowed("key1") is True
        assert await limiter.is_allowed("key1") is True

    @pytest.mark.anyio
    async def test_recent_timestamps_still_count(self):
        """Requests within the window should count."""
        limiter = make_limiter(max_requests=2, window_seconds=60)
        recent = time.time() - 30  # 30s ago — still within 60s window
        limiter._fallback["key1"] = [recent, recent]

        assert await limiter.is_allowed("key1") is False

    @pytest.mark.anyio
    async def test_mixed_old_and_new_timestamps(self):
        """Only in-window timestamps count toward limit."""
        limiter = make_limiter(max_requests=2, window_seconds=60)
        old = time.time() - 65   # outside window
        recent = time.time() - 5  # inside window
        limiter._fallback["key1"] = [old, recent]

        # 1 recent + this new one = 2 total → allowed
        assert await limiter.is_allowed("key1") is True
        # Now 2 recent → blocked
        assert await limiter.is_allowed("key1") is False


# ═══════════════════════════════════════════
# OOM Safety valve
# ═══════════════════════════════════════════

class TestOOMSafetyValve:

    @pytest.mark.anyio
    async def test_clears_fallback_when_too_many_keys(self):
        """If fallback dict grows beyond MAX_FALLBACK_KEYS, it should be cleared."""
        limiter = make_limiter(max_requests=100)
        # Stuff the dict past the safety limit
        for i in range(limiter._MAX_FALLBACK_KEYS + 1):
            limiter._fallback[f"ip:{i}"] = [time.time()]

        assert len(limiter._fallback) > limiter._MAX_FALLBACK_KEYS
        # Next call should trigger the safety valve and clear
        result = await limiter.is_allowed("new-key")
        assert result is True
        # Dict was cleared and rebuilt with just the new key
        assert len(limiter._fallback) == 1


# ═══════════════════════════════════════════
# Cleanup
# ═══════════════════════════════════════════

class TestCleanupFallback:

    def test_removes_keys_with_no_timestamps(self):
        limiter = make_limiter()
        limiter._fallback["stale-key"] = []
        limiter.cleanup_fallback()
        assert "stale-key" not in limiter._fallback

    def test_removes_keys_with_only_old_timestamps(self):
        limiter = make_limiter(window_seconds=60)
        limiter._fallback["old-key"] = [time.time() - 61]
        limiter.cleanup_fallback()
        assert "old-key" not in limiter._fallback

    def test_keeps_keys_with_recent_timestamps(self):
        limiter = make_limiter(window_seconds=60)
        limiter._fallback["active-key"] = [time.time() - 10]
        limiter.cleanup_fallback()
        assert "active-key" in limiter._fallback

    def test_cleans_only_stale_keys(self):
        limiter = make_limiter(window_seconds=60)
        limiter._fallback["stale"] = [time.time() - 90]
        limiter._fallback["active"] = [time.time() - 5]
        limiter.cleanup_fallback()
        assert "stale" not in limiter._fallback
        assert "active" in limiter._fallback


# ═══════════════════════════════════════════
# Redis → fallback transition
# ═══════════════════════════════════════════

class TestRedisFallbackTransition:

    @pytest.mark.anyio
    async def test_falls_back_to_memory_when_redis_raises(self):
        """If Redis pipeline raises, limiter should switch to in-memory fallback."""
        limiter = SlidingWindowLimiter(max_requests=5, window_seconds=60)
        limiter._redis_available = True

        mock_redis = AsyncMock()
        mock_pipeline = AsyncMock()
        mock_pipeline.execute.side_effect = ConnectionError("Redis down")
        mock_redis.pipeline.return_value = mock_pipeline

        with patch("app.middleware.rate_limiter.SlidingWindowLimiter._get_redis", return_value=mock_redis):
            result = await limiter.is_allowed("key1")

        # Should have gracefully fallen back
        assert result is True
        assert limiter._redis_available is False
        assert len(limiter._fallback["key1"]) == 1  # recorded in-memory

    @pytest.mark.anyio
    async def test_once_failed_stays_on_memory_path(self):
        """After Redis is marked unavailable, calls use in-memory directly."""
        limiter = SlidingWindowLimiter(max_requests=2, window_seconds=60)
        limiter._redis_available = False  # already flipped — no Redis attempt

        result1 = await limiter.is_allowed("key1")
        result2 = await limiter.is_allowed("key1")
        result3 = await limiter.is_allowed("key1")  # should be blocked

        assert result1 is True
        assert result2 is True
        assert result3 is False  # limit enforced via in-memory
        # Confirm state was tracked in the fallback dict, confirming memory path was used
        assert len(limiter._fallback["key1"]) == 2


# ═══════════════════════════════════════════
# check_upload_rate helper
# ═══════════════════════════════════════════

class TestCheckUploadRate:

    @pytest.mark.anyio
    async def test_raises_429_when_limit_exceeded(self):
        """check_upload_rate should raise HTTP 429 after 5 uploads."""
        from fastapi import HTTPException
        from app.middleware.rate_limiter import upload_limiter

        upload_limiter._fallback.clear()
        upload_limiter._redis_available = False

        user_id = "test-user-rate-999"
        # Exhaust the limit
        for _ in range(5):
            await check_upload_rate(user_id)

        with pytest.raises(HTTPException) as exc_info:
            await check_upload_rate(user_id)

        assert exc_info.value.status_code == 429
        assert "5 uploads" in exc_info.value.detail

    @pytest.mark.anyio
    async def test_allows_within_limit(self):
        """Under the limit, no exception should be raised."""
        from app.middleware.rate_limiter import upload_limiter

        upload_limiter._fallback.clear()
        upload_limiter._redis_available = False

        user_id = "test-user-rate-888"
        # Should not raise for the first 5
        for _ in range(5):
            await check_upload_rate(user_id)  # no exception


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"
