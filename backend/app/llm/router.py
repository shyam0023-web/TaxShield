"""
TaxShield — LLM Router (Groq-Only + Retry)
All LLM calls route through Groq Llama 3.3 70B.
Retry with exponential backoff for transient failures (429, 503).
"""
import asyncio
from app.llm.groq_client import groq_client
import logging

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
INITIAL_BACKOFF_S = 1.0


class LLMRouter:
    def __init__(self):
        self.groq = groq_client

    async def generate(self, prompt: str, risk_level: str = "LOW",
                       json_mode: bool = False) -> str:
        """
        Route to Groq with retry on transient failures.
        
        Retries up to MAX_RETRIES times with exponential backoff.
        Only retries on likely-transient errors (rate limit, server error).
        """
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                return await self.groq.generate(prompt, json_mode=json_mode)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                is_transient = any(kw in error_str for kw in [
                    "429", "rate limit", "503", "502", "timeout", "overloaded"
                ])
                
                if not is_transient or attempt == MAX_RETRIES:
                    logger.error(f"LLM generation failed (attempt {attempt + 1}/{MAX_RETRIES + 1}): {e}")
                    raise
                
                wait = INITIAL_BACKOFF_S * (2 ** attempt)
                logger.warning(
                    f"LLM transient error (attempt {attempt + 1}/{MAX_RETRIES + 1}), "
                    f"retrying in {wait}s: {e}"
                )
                await asyncio.sleep(wait)
        
        raise last_error  # Should never reach here

    async def generate_with_image(self, prompt: str, image_bytes: bytes,
                                   mime_type: str = "image/png") -> str:
        """Vision is not supported in Groq-only mode."""
        raise NotImplementedError(
            "Vision not available in Groq-only mode. "
            "Use Surya or Tesseract OCR for image processing."
        )

    async def stream(self, prompt: str, risk_level: str = "LOW"):
        """Stream via Groq."""
        try:
            async for chunk in self.groq.stream(prompt):
                yield chunk
        except Exception as e:
            logger.error(f"Groq streaming failed: {e}")
            raise


llm_router = LLMRouter()

