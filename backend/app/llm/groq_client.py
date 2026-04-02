"""
TaxShield — Groq LLM Client (Fallback)
Uses Groq Llama 3.3 as fallback when Gemini is down.
"""
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from app.config import settings
import logging
import re

logger = logging.getLogger(__name__)


class GroqClient:
    def __init__(self):
        self._llm = None
    
    def _get_llm(self) -> ChatGroq:
        """Lazy init — only create when first called."""
        if self._llm is None:
            if not settings.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY not set in .env")
            self._llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                api_key=settings.GROQ_API_KEY,
                temperature=0
            )
            logger.info("GroqClient initialized with Llama 3.3")
        return self._llm
    
    @staticmethod
    def _clean_response(text) -> str:
        """Clean LLM response: handle None, lists, markdown fences."""
        # Handle None
        if text is None:
            return ""
        
        # Handle list content (newer LangChain versions)
        if isinstance(text, list):
            text = " ".join(str(item) for item in text)
        
        # Ensure string
        text = str(text).strip()
        
        # Remove markdown code fences: ```json ... ``` or ``` ... ```
        match = re.search(r'```(?:json|JSON)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return text

    async def generate(self, prompt: str, json_mode: bool = False) -> str:
        """Generate response using Groq."""
        try:
            llm = self._get_llm()
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            result = self._clean_response(response.content)
            logger.debug(f"Groq response length: {len(result)} chars")
            return result
        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            raise
    
    async def stream(self, prompt: str):
        """Stream response token-by-token."""
        try:
            llm = self._get_llm()
            async for chunk in llm.astream([HumanMessage(content=prompt)]):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"Groq streaming failed: {e}")
            raise


# Singleton
groq_client = GroqClient()
