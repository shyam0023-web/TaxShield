from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from app.config import GROQ_API_KEY, LLM_MODEL, LLM_TEMPERATURE

def get_llm():
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set in .env file")
    
    return ChatGroq(
        model=LLM_MODEL,
        api_key=GROQ_API_KEY,
        temperature=LLM_TEMPERATURE
    )

def generate(prompt: str) -> str:
    llm = get_shared_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content

llm = None

def get_shared_llm():
    global llm
    if llm is None:
        llm = get_llm()
    return llm
