import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        # Test OPTIONS request (CORS Preflight)
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization"
        }
        res = await client.options("http://localhost:8000/api/notices", headers=headers)
        print("OPTIONS STATUS:", res.status_code)
        print("OPTIONS HEADERS:", dict(res.headers))

        # Test POST OPTIONS request 
        headers["Access-Control-Request-Method"] = "POST"
        res = await client.options("http://localhost:8000/api/notices/upload", headers=headers)
        print("OPTIONS UPLOAD STATUS:", res.status_code)
        print("OPTIONS UPLOAD HEADERS:", dict(res.headers))

asyncio.run(main())
