"""
TaxShield — Gemini LLM Client
Supports: Gemini 2.0 Flash (primary) and Gemini Pro (HIGH risk)
Features: Streaming, structured JSON output, temperature=0 for legal accuracy
"""
import google.generativeai as genai
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self):
        self._flash = None
        self._pro = None
        self._configured = False
    
    def _ensure_configured(self):
        """Lazy init — only configure when first called."""
        if not self._configured:
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY not set in .env")
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._flash = genai.GenerativeModel("gemini-2.0-flash")
            self._pro = genai.GenerativeModel("gemini-1.5-pro")
            self._configured = True
            logger.info("GeminiClient initialized with Flash and Pro models")
    
    @property
    def flash(self):
        self._ensure_configured()
        return self._flash
    
    @property
    def pro(self):
        self._ensure_configured()
        return self._pro
    
    async def generate(self, prompt: str, model: str = "flash", 
                       temperature: float = 0, json_mode: bool = False) -> str:
        """Generate response. temperature=0 for legal accuracy."""
        try:
            selected = self.flash if model == "flash" else self.pro
            
            config = genai.GenerationConfig(
                temperature=temperature,
                top_p=1,
            )
            if json_mode:
                config.response_mime_type = "application/json"
            
            response = await selected.generate_content_async(
                prompt,
                generation_config=config
            )
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini {model} failed: {e}")
            raise
    
    async def generate_with_image(self, prompt: str, image_bytes: bytes,
                                   mime_type: str = "image/png") -> str:
        """Gemini Vision — for OCR extraction from scanned notices."""
        try:
            response = await self.flash.generate_content_async([
                prompt,
                {"mime_type": mime_type, "data": image_bytes}
            ])
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini Vision failed: {e}")
            raise
    
    async def stream(self, prompt: str, model: str = "flash"):
        """Stream response token-by-token for live chat UI."""
        try:
            selected = self.flash if model == "flash" else self.pro
            response = await selected.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(temperature=0),
                stream=True
            )
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"Gemini streaming failed: {e}")
            raise


# Singleton — lazy init, won't crash on import
gemini = GeminiClient()
