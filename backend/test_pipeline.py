import asyncio
import time
import logging
from app.config import settings

print(f"LOADING KEY: {settings.GROQ_API_KEY[:10]}...")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
from app.agents.graph import graph

async def main():
    print("Loading test PDF...")
    try:
        with open("SCN.pdf", "rb") as f:
            pdf_bytes = f.read()
    except Exception as e:
        print("SCN.pdf not found.", e)
        return

    initial_state = {
        "pdf_bytes": pdf_bytes,
        "case_id": "TEST_CASE_123",
        "current_agent": "start",
        "user_instructions": "This is a test run from CLI",
    }
    
    print("Starting pipeline graph.ainvoke...")
    start = time.time()
    try:
        final_state = await graph.ainvoke(initial_state)
        print("SUCCESS! Took:", time.time() - start)
        print("Draft Status:", str(final_state.get("draft_reply", ""))[:200])
    except Exception as e:
        print("FAILED! Took:", time.time() - start)
        print("Error:", e)
        print(type(e))

asyncio.run(main())
