"""
TaxShield — LLM Router
Fallback chain: Gemini Flash → Gemini Pro → Groq Llama 3.3
"""
from app.llm.gemini_client import gemini
from app.llm.groq_client import groq_client
import logging

logger = logging.getLogger(__name__)


class LLMRouter:
    def __init__(self):
        self.groq = groq_client
    
    async def generate(self, prompt: str, risk_level: str = "LOW",
                       json_mode: bool = False) -> str:
        """
        Route to appropriate LLM based on risk level:
        - LOW/MEDIUM: Gemini Flash (fast, cheap)
        - HIGH: Gemini Pro (better reasoning)
        - Fallback: Groq Llama 3.3
        """
        model = "pro" if risk_level == "HIGH" else "flash"
        
        try:
            return await gemini.generate(prompt, model=model, 
                                          json_mode=json_mode)
        except Exception as e:
            logger.warning(f"Gemini {model} failed: {e}, falling back to Groq")
            try:
                return await self.groq.generate(prompt, json_mode=json_mode)
            except Exception as e2:
                logger.error(f"All LLMs failed: {e2}")
                raise
    
    async def generate_with_image(self, prompt: str, image_bytes: bytes,
                                   mime_type: str = "image/png") -> str:
        """Vision — only Gemini supports this, no fallback."""
        return await gemini.generate_with_image(prompt, image_bytes, mime_type)
    
    async def stream(self, prompt: str, risk_level: str = "LOW"):
        """Stream with fallback chain."""
        model = "pro" if risk_level == "HIGH" else "flash"
        
        try:
            async for chunk in gemini.stream(prompt, model=model):
                yield chunk
        except Exception as e:
            logger.warning(f"Gemini streaming failed: {e}, falling back to Groq")
            try:
                async for chunk in self.groq.stream(prompt):
                    yield chunk
            except Exception as e2:
                logger.error(f"All LLM streaming failed: {e2}")
                raise


llm_router = LLMRouter()
