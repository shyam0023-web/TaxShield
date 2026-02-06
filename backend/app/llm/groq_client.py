"""Groq API Client - Primary LLM (Llama 3.3 70B)"""
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from app.config import GROQ_API_KEY, LLM_MODEL, LLM_TEMPERATURE

def get_llm():
    """Initialize and return Groq LLM client"""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set in .env file")
    
    return ChatGroq(
        model=LLM_MODEL,
        api_key=GROQ_API_KEY,
        temperature=LLM_TEMPERATURE
    )

def generate(prompt: str) -> str:
    """Generate response from LLM"""
    llm = get_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content

# Singleton instance for reuse
llm = None

def get_shared_llm():
    """Get or create shared LLM instance"""
    global llm
    if llm is None:
        llm = get_llm()
    return llm
