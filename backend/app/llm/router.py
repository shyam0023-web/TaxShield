"""
TaxShield — LLM Router (Groq-Only + Retry)
All LLM calls route through Groq Llama 3.3 70B.
Retry with exponential backoff for transient failures (429, 503).
"""
import asyncio
from app.llm.groq_client import groq_client
from app.llm.gemini_client import gemini
from app.config import settings
import logging

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
INITIAL_BACKOFF_S = 1.0


class LLMRouter:
    def __init__(self):
        self.groq = groq_client
        self.gemini = gemini

    async def generate(self, prompt: str, risk_level: str = "LOW",
                       json_mode: bool = False, model_type: str = "versatile") -> str:
        """
        Route to Groq with retry on transient failures.
        If Groq fully fails (rate limits exceeded, offline), fallback to Gemini.
        """
        last_error = None
        # Primary: Groq
        MAX_RETRIES = 5  # Allow more retries for slow refill
        for attempt in range(MAX_RETRIES + 1):
            try:
                return await self.groq.generate(prompt, json_mode=json_mode, model=model_type)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                is_transient = any(kw in error_str for kw in [
                    "429", "rate limit", "503", "502", "timeout", "overloaded"
                ])
                
                if not is_transient or attempt == MAX_RETRIES:
                    logger.error(f"Groq LLM generation failed permanently: {e}")
                    raise Exception(f"Groq generation failed permanently: {e}")
                
                wait = INITIAL_BACKOFF_S * (2 ** attempt)
                if "429" in error_str and "try again in" in error_str:
                    try:
                        import re
                        match = re.search(r'try again in (?:(\d+)m)?([\d\.]+)s', error_str)
                        if match:
                            m = int(match.group(1)) if match.group(1) else 0
                            s = float(match.group(2))
                            wait = m * 60 + s + 1.0  # Add 1s buffer
                    except Exception:
                        pass
                
                logger.warning(f"Groq transient error (attempt {attempt + 1}/{MAX_RETRIES + 1}), retrying in {wait}s: {e}")
                await asyncio.sleep(wait)
        
        # Fallback: Gemini
        if settings.GEMINI_API_KEY:
            logger.warning("Initiating LLM Fallback: Routing to Gemini 2.0 Flash")
            try:
                # Map Groq's high risk needs to Gemini Pro if needed, else Flash
                model = "pro" if risk_level == "HIGH" else "flash"
                return await self.gemini.generate(prompt, model=model, temperature=0, json_mode=json_mode)
            except Exception as gemini_err:
                logger.error(f"Gemini fallback also failed: {gemini_err}")
                raise Exception(f"All LLM providers failed. Primary: {last_error}, Fallback: {gemini_err}") from gemini_err
        
        # If no fallback configured, raise original error
        raise last_error

    async def generate_with_image(self, prompt: str, image_bytes: bytes,
                                   mime_type: str = "image/png") -> str:
        """Vision triggers Gemini Vision bypass."""
        if not settings.GEMINI_API_KEY:
            raise NotImplementedError("Vision requires GEMINI_API_KEY to be set.")
        return await self.gemini.generate_with_image(prompt, image_bytes, mime_type)

    async def stream(self, prompt: str, risk_level: str = "LOW"):
        """Stream via Groq, fallback to Gemini."""
        try:
            # Note: Groq streaming doesn't support elegant retry if it fails mid-stream
            # But we can try to initiate it, and if the init fails, fallback.
            async for chunk in self.groq.stream(prompt):
                yield chunk
        except Exception as e:
            logger.error(f"Groq streaming failed: {e}. Falling back to Gemini.")
            if settings.GEMINI_API_KEY:
                try:
                    model = "pro" if risk_level == "HIGH" else "flash"
                    async for chunk in self.gemini.stream(prompt, model=model):
                        yield chunk
                except Exception as gemini_err:
                    logger.error(f"Gemini streaming fallback failed: {gemini_err}")
                    raise
            else:
                raise


llm_router = LLMRouter()

