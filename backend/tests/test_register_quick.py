"""Test scraper via backend API — register fresh account then scrape."""
import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(timeout=60) as c:
        # Register fresh test account
        reg = await c.post("http://localhost:8000/api/auth/register", json={
            "email": "scrapetest@test.com", "password": "scrapetest123", "full_name": "Scrape Test"
        })
        print(f"Register: {reg.status_code}")
        if reg.status_code == 409:
            # Already exists, try login
            reg = await c.post("http://localhost:8000/api/auth/login", json={
                "email": "scrapetest@test.com", "password": "scrapetest123"
            })
            print(f"Login: {reg.status_code}")
        
        if reg.status_code != 200:
            print(f"Auth failed: {reg.text}")
            return
        
        token = reg.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Trigger scrape
        print("\nTriggering CBIC scrape...")
        r = await c.post("http://localhost:8000/api/kb/scrape", headers=headers)
        print(f"Scrape status: {r.status_code}")
        print(f"Scrape result: {r.text}")
        
        # List pending
        print("\nListing pending circulars...")
        p = await c.get("http://localhost:8000/api/kb/pending", headers=headers)
        print(f"Pending status: {p.status_code}")
        print(f"Pending result: {p.text[:500]}")

asyncio.run(test())
