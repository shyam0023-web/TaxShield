import asyncio
from app.llm.router import LLMRouter

async def main():
    router = LLMRouter()
    try:
        res = await router.generate("Extract entities. Notice text: Sample tax notice for ₹ 1000. Under section 73. Please output JSON with keys GSTIN, DIN, SECTIONS, notice_type", risk_level="LOW", json_mode=True)
        print("SUCCESS:", res)
    except Exception as e:
        print("ERROR:", e)

asyncio.run(main())
