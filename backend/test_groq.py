import asyncio
from app.llm.groq_client import groq_client
import sys

async def main():
    try:
        res = await groq_client.generate('{"message": "Say hello"}', json_mode=True)
        print("SUCCESS:")
        print(res)
    except Exception as e:
        print("ERROR:")
        print(e)
        sys.exit(1)

asyncio.run(main())
