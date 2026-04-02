"""Test PDF upload via backend API manually to see the raw error."""
import httpx
import asyncio
import os

async def test_upload():
    async with httpx.AsyncClient(timeout=30) as c:
        # 1. Login
        login_res = await c.post("http://localhost:8000/api/auth/login", json={
            "email": "scrapetest@test.com", "password": "scrapetest123"
        })
        if login_res.status_code != 200:
            print(f"Login failed: {login_res.text}")
            return
            
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Create a dummy PDF file
        dummy_pdf_path = "dummy_test.pdf"
        with open(dummy_pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\n%EOF\n")
            
        # 3. Upload PDF
        with open(dummy_pdf_path, "rb") as f:
            files = {"file": ("dummy_test.pdf", f, "application/pdf")}
            print("Sending upload request...")
            upload_res = await c.post("http://localhost:8000/api/notices/upload", headers=headers, files=files)
            
        print(f"Status: {upload_res.status_code}")
        print(f"Response: {upload_res.text}")
        
        if os.path.exists(dummy_pdf_path):
            os.remove(dummy_pdf_path)

asyncio.run(test_upload())
