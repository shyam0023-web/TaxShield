import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

async def test():
    key = os.getenv("GROQ_API_KEY", "MISSING")
    print(f"Key: {key[:20]}...")
    
    from langchain_groq import ChatGroq
    from langchain_core.messages import HumanMessage
    
    llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=key, temperature=0)
    resp = await llm.ainvoke([HumanMessage(content="Say hello in one word")])
    print(f"RESULT: {resp.content}")

asyncio.run(test())
