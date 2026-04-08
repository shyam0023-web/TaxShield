import requests
import time

BASE = "http://127.0.0.1:8000"

# Login
print("Logging in...")
res = requests.post(f"{BASE}/api/auth/login", json={"email": "test@test.com", "password": "demo123"})
token = res.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"✅ Logged in")

# Upload
print("\nUploading sample_notice.pdf...")
with open("sample_notice.pdf", "rb") as f:
    upload_res = requests.post(
        f"{BASE}/api/notices/upload",
        files={"file": ("sample_notice.pdf", f, "application/pdf")},
        data={"user_instructions": "Focus on ITC mismatch defense."},
        headers=headers
    )
upload_data = upload_res.json()
notice_id = upload_data["id"]
print(f"✅ Upload accepted. Notice ID: {notice_id}")
print(f"   Pipeline is now running in background...\n")

# Poll
start = time.time()
while True:
    elapsed = time.time() - start
    if elapsed > 180:
        print("⏱ Timed out after 3 minutes. Check backend logs.")
        break

    res = requests.get(f"{BASE}/api/notices/{notice_id}", headers=headers)
    data = res.json()
    status = data.get("status", "?")
    draft_status = data.get("draft_status", "?")
    draft = data.get("draft_reply", "") or ""

    print(f"  [{elapsed:.0f}s] status={status} | draft_status={draft_status}")

    if status == "processed" and draft.strip():
        print(f"\n{'='*60}")
        print(f"✅ SUCCESS in {elapsed:.0f} seconds!")
        print(f"{'='*60}")
        print(draft[:1000])
        print(f"{'='*60}")
        break
    elif status == "error":
        print(f"\n❌ Pipeline Error: {data.get('error_message', 'unknown')}")
        break

    time.sleep(5)
