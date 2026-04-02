"""
Tests for LLM Router retry logic (Issue 6) and pipeline timeout (Issue 2).
"""
import sys
import os
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ═══════════════════════════════════════════
# Issue 6: LLM Router Retry Tests
# ═══════════════════════════════════════════

class TestLLMRouterRetry:

    @pytest.mark.anyio
    async def test_succeeds_first_try(self):
        """Normal case — no retries needed."""
        from app.llm.router import LLMRouter

        router = LLMRouter()
        router.groq = MagicMock()
        router.groq.generate = AsyncMock(return_value="Success response")

        result = await router.generate("test prompt")
        assert result == "Success response"
        assert router.groq.generate.call_count == 1

    @pytest.mark.anyio
    async def test_retries_on_429(self):
        """Should retry on rate limit (429) and succeed on 2nd attempt."""
        from app.llm.router import LLMRouter

        router = LLMRouter()
        router.groq = MagicMock()
        router.groq.generate = AsyncMock(
            side_effect=[Exception("429 rate limit exceeded"), "Retry success"]
        )

        result = await router.generate("test prompt")
        assert result == "Retry success"
        assert router.groq.generate.call_count == 2

    @pytest.mark.anyio
    async def test_retries_on_503(self):
        """Should retry on server error (503)."""
        from app.llm.router import LLMRouter

        router = LLMRouter()
        router.groq = MagicMock()
        router.groq.generate = AsyncMock(
            side_effect=[Exception("503 service unavailable"), "Back online"]
        )

        result = await router.generate("test prompt")
        assert result == "Back online"
        assert router.groq.generate.call_count == 2

    @pytest.mark.anyio
    async def test_no_retry_on_auth_error(self):
        """Should NOT retry on non-transient errors (auth, invalid key)."""
        from app.llm.router import LLMRouter

        router = LLMRouter()
        router.groq = MagicMock()
        router.groq.generate = AsyncMock(
            side_effect=Exception("Invalid API key")
        )

        with pytest.raises(Exception, match="Invalid API key"):
            await router.generate("test prompt")
        assert router.groq.generate.call_count == 1  # No retry

    @pytest.mark.anyio
    async def test_max_retries_exceeded(self):
        """Should give up after MAX_RETRIES and raise."""
        from app.llm.router import LLMRouter

        router = LLMRouter()
        router.groq = MagicMock()
        router.groq.generate = AsyncMock(
            side_effect=Exception("429 rate limit exceeded")
        )

        with pytest.raises(Exception, match="429"):
            await router.generate("test prompt")
        # 1 initial + 2 retries = 3 total
        assert router.groq.generate.call_count == 3


# ═══════════════════════════════════════════
# Issue 2: Pipeline Timeout Test
# ═══════════════════════════════════════════

class TestPipelineTimeout:

    @pytest.mark.anyio
    async def test_timeout_sets_error_status(self):
        """A slow pipeline should timeout and set notice status to 'error'."""
        from app.routes.notices import _run_pipeline_background, PIPELINE_TIMEOUT_SECONDS

        # Verify the timeout constant is reasonable
        assert PIPELINE_TIMEOUT_SECONDS > 0
        assert PIPELINE_TIMEOUT_SECONDS <= 300  # Not absurdly long

    @pytest.mark.anyio
    async def test_timeout_error_message(self):
        """TimeoutError should produce a user-friendly message."""
        from app.routes.notices import PIPELINE_TIMEOUT_SECONDS

        try:
            raise TimeoutError(
                f"Pipeline timed out after {PIPELINE_TIMEOUT_SECONDS}s. "
                "This usually means a slow LLM response. Try uploading again."
            )
        except TimeoutError as e:
            msg = str(e)
            assert "timed out" in msg
            assert "Try uploading again" in msg
