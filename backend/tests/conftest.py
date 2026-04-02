"""
Shared test configuration.
- Auto-clears rate limiter fallback state between tests
  (Redis won't be available in tests, so the in-memory fallback is used)
"""
import pytest


@pytest.fixture(autouse=True)
def clear_rate_limiter_state():
    """Clear in-memory fallback state on both limiters between tests."""
    from app.middleware.rate_limiter import ip_limiter, upload_limiter
    ip_limiter._fallback.clear()
    upload_limiter._fallback.clear()
    yield
    ip_limiter._fallback.clear()
    upload_limiter._fallback.clear()
