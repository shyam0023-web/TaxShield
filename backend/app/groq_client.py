import os
from typing import Optional, List, Dict, Any
from groq import Groq
from app.config import settings
from app.logger import logger


class GroqClient:
    """Client for Groq API interactions"""
    
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        if not self.api_key:
            logger.warning("GROQ_API_KEY not found in environment variables")
        
        self.client = Groq(api_key=self.api_key)
        self.default_model = "llama-3.1-70b-versatile"
    
    async def generate(self, prompt: str, model: Optional[str] = None, 
                       temperature: float = 0, json_mode: bool = False) -> str:
        """Generate response with unified interface"""
        try:
            messages = [{"role": "user", "content": prompt}]
            
            completion_params = {
                "model": model or self.default_model,
                "messages": messages,
                "temperature": temperature,
            }
            
            if json_mode:
                completion_params["response_format"] = {"type": "json_object"}
            
            response = self.client.chat.completions.create(**completion_params)
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating response from Groq: {e}")
            raise
    
    async def stream(self, prompt: str, model: Optional[str] = None):
        """Stream response token-by-token for live chat UI"""
        try:
            messages = [{"role": "user", "content": prompt}]
            
            completion_params = {
                "model": model or self.default_model,
                "messages": messages,
                "temperature": 0,
                "stream": True,
            }
            
            stream = self.client.chat.completions.create(**completion_params)
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Error streaming response from Groq: {e}")
            raise
    
    # Legacy methods for backward compatibility
    async def generate_response(
        self, 
        prompt: str, 
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        """Legacy method - use generate() instead"""
        messages = []
        
        if system_message:
            messages.append({
                "role": "system",
                "content": system_message
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        completion_params = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            completion_params["max_tokens"] = max_tokens
        
        response = self.client.chat.completions.create(**completion_params)
        
        return response.choices[0].message.content
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current client setup"""
        return {
            "default_model": self.default_model,
            "api_key_configured": bool(self.api_key),
            "client_initialized": self.client is not None
        }


# Singleton instance
groq = GroqClient()
