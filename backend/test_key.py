import asyncio
from app.llm.groq_client import groq_client

async def main():
    print("Testing 8B instant model...")
    result = await groq_client.generate("Say: Key is working", model="instant")
    print("8B:", result)
    
    print("\nTesting 70B versatile model...")
    result = await groq_client.generate("Say: Key is working", model="versatile")
    print("70B:", result)

asyncio.run(main())
