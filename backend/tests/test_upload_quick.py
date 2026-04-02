"""Test script to trigger the upload route and see the real error."""
import httpx
import asyncio
import os

async def test():
    file_path = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "synthetic_notice_73.json")
    with open(file_path, "rb") as f:
        content = f.read()

    async with httpx.AsyncClient() as c:
        r = await c.post(
            "http://localhost:8000/api/notices/upload",
            files={"file": ("test.pdf", content, "application/pdf")},
            headers={"Authorization": "Bearer test-token-we-dont-care"} # We expect 401, but maybe it crashes before auth or after auth. Wait, if it's 401 it returns JSON. 
        )
        print(f"Status: {r.status_code}")
        print(f"Body: {r.text}")

asyncio.run(test())
