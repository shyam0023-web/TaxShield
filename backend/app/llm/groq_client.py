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
        self._llm_70b = None
        self._llm_8b = None
    
    def _get_llm(self, model: str) -> ChatGroq:
        """Lazy init — only create when first called."""
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set in .env")
        
        if model == "instant":
            if self._llm_8b is None:
                self._llm_8b = ChatGroq(
                    model="llama-3.1-8b-instant",
                    api_key=settings.GROQ_API_KEY,
                    temperature=0
                )
            return self._llm_8b
        else:
            if self._llm_70b is None:
                self._llm_70b = ChatGroq(
                    model="llama-3.3-70b-versatile",
                    api_key=settings.GROQ_API_KEY,
                    temperature=0
                )
            return self._llm_70b
    
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

    async def generate(self, prompt: str, json_mode: bool = False, model: str = "versatile") -> str:
        """Generate response using Groq."""
        try:
            llm = self._get_llm(model=model)
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            result = self._clean_response(response.content)
            logger.debug(f"Groq {model} response length: {len(result)} chars")
            return result
        except Exception as e:
            logger.error(f"Groq {model} generation failed: {e}")
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
