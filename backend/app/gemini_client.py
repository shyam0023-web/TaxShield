import os
from typing import Optional, List, Dict, Any
import google.generativeai as genai
from .config import settings
from .logger import logger


class GeminiClient:
    """Client for Google Gemini API interactions"""
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=self.api_key)
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self, model_name: str = "gemini-1.5-flash"):
        """Initialize the Gemini model"""
        try:
            self.model = genai.GenerativeModel(model_name)
            logger.info(f"Gemini model '{model_name}' initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            raise
    
    async def generate_response(
        self, 
        prompt: str, 
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate a response from Gemini"""
        try:
            if not self.model:
                raise ValueError("Model not initialized")
            
            generation_config = {
                "temperature": temperature,
            }
            
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens
            
            if system_instruction:
                self.model._system_instruction = system_instruction
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating response from Gemini: {e}")
            raise
    
    async def generate_structured_response(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_instruction: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a structured response following a specific schema"""
        try:
            # Add schema instruction to prompt
            schema_instruction = f"""
            Please respond with a JSON object that follows this schema:
            {schema}
            
            Your response must be valid JSON that matches this structure exactly.
            """
            
            full_prompt = f"{prompt}\n\n{schema_instruction}"
            
            response_text = await self.generate_response(
                full_prompt, 
                system_instruction=system_instruction,
                temperature=0.3  # Lower temperature for structured output
            )
            
            # Parse and validate the response
            import json
            try:
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response as JSON: {e}")
                logger.error(f"Raw response: {response_text}")
                raise ValueError("Invalid JSON response from Gemini")
                
        except Exception as e:
            logger.error(f"Error generating structured response from Gemini: {e}")
            raise
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Handle chat-style conversations with Gemini"""
        try:
            if not self.model:
                raise ValueError("Model not initialized")
            
            # Convert messages to Gemini's format
            chat_history = []
            for message in messages:
                role = message.get("role", "user")
                content = message.get("content", "")
                
                if role == "system":
                    # System messages in Gemini are handled differently
                    continue
                elif role == "assistant":
                    chat_history.append({"role": "model", "parts": [content]})
                else:  # user
                    chat_history.append({"role": "user", "parts": [content]})
            
            generation_config = {
                "temperature": temperature,
            }
            
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens
            
            # Start chat with history
            chat = self.model.start_chat(history=chat_history[:-1] if chat_history else [])
            
            # Send the last message
            if chat_history:
                response = chat.send_message(
                    chat_history[-1]["parts"][0],
                    generation_config=generation_config
                )
                return response.text
            else:
                raise ValueError("No messages provided")
                
        except Exception as e:
            logger.error(f"Error in chat completion with Gemini: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            "model_name": getattr(self.model, 'model_name', 'unknown'),
            "api_key_configured": bool(self.api_key),
            "model_initialized": self.model is not None
        }


# Global instance
gemini_client = GeminiClient()
