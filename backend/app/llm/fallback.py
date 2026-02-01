"""Fallback LLM Strategy - Groq -> OpenAI -> Ollama"""
def get_llm_with_fallback():
    # TODO: Try Groq first, then OpenAI, then local Ollama
    # Priority:
    # 1. Llama 3.3 70B (Groq) - Fast, free
    # 2. GPT-4o-mini (OpenAI) - If Groq fails
    # 3. Gemma 2 9B (Ollama) - Offline fallback
    pass
