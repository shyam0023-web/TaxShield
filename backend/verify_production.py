import requests
import time
import json

URL = "http://localhost:8000/health"
print(f"Testing rate limiting on {URL}...")

try:
    # 1. Successful request
    resp = requests.get(URL)
    print(f"[1] Status: {resp.status_code} | Request-ID: {resp.headers.get('X-Request-ID')}")
    
    # 2. Spam requests to trigger rate limit
    for i in range(25):
        resp = requests.get(URL)
        if resp.status_code == 429:
            print(f"[{i+2}] 🛑 Rate Limit Triggered! {resp.status_code}")
            print(f"Response: {resp.json()}")
            break
        print(f"[{i+2}] Status: {resp.status_code}")
        
except Exception as e:
    print(f"Error: {e}")
    print("Make sure the backend is running on port 8000!")
