import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        # Login
        r = await client.post("http://localhost:8000/api/auth/login", json={"email":"test@test.com","password":"demo123"})
        data = r.json()
        token = data["token"]
        print(f"Token: {token[:50]}...")
        
        # Fetch notices
        r2 = await client.get("http://localhost:8000/api/notices?page_size=5", headers={"Authorization": f"Bearer {token}"})
        print(f"Status: {r2.status_code}")
        print(f"Response: {r2.text[:500]}")

asyncio.run(test())
