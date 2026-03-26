"""
TaxShield — LLM Router (Groq-Only)
All LLM calls route through Groq Llama 3.3 70B.
No Gemini dependency — single vendor, simpler ops.

Note: Vision (OCR fallback) is disabled in Groq-only mode.
Agent 1 should use Surya/Tesseract OCR instead.
"""
from app.llm.groq_client import groq_client
import logging

logger = logging.getLogger(__name__)


class LLMRouter:
    def __init__(self):
        self.groq = groq_client

    async def generate(self, prompt: str, risk_level: str = "LOW",
                       json_mode: bool = False) -> str:
        """
        All risk levels route to Groq Llama 3.3 70B.
        risk_level param kept for API compatibility but has no routing effect.
        """
        try:
            return await self.groq.generate(prompt, json_mode=json_mode)
        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            raise

    async def generate_with_image(self, prompt: str, image_bytes: bytes,
                                   mime_type: str = "image/png") -> str:
        """Vision is not supported in Groq-only mode.
        Agent 1 should use Surya/Tesseract OCR instead."""
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
